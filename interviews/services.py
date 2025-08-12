import base64
import hashlib
import hmac
import json
import logging
import math
import os
import re
import requests
import threading
import time
import traceback
import urllib.parse
from datetime import datetime
from time import mktime
from urllib.parse import urlencode, quote, urlparse
from urllib3 import encode_multipart_formdata
from wsgiref.handlers import format_date_time
import websocket
from websocket import create_connection, WebSocketConnectionClosedException

from django.conf import settings
from django.db import models

from knowledge_base.services import XunfeiSparkService

logger = logging.getLogger(__name__)

class XunfeiRealtimeTranscribeClient:
    """
    讯飞实时语音转写WebSocket客户端（rtasr.xfyun.cn/v1/ws）
    用法：
        client = XunfeiRealtimeTranscribeClient(on_result=回调函数)
        client.connect()
        client.send_audio(audio_bytes)
        ...
        client.close()
    """
    def __init__(self, on_result=None):
        import hashlib, base64, time
        from django.conf import settings
        self.appid = getattr(settings, 'XUNFEI_APP_ID', '')
        self.api_key = getattr(settings, 'XUNFEI_RTASR_API_KEY', '')
        self.on_result = on_result
        self.ws = None
        self.thread = None
        self.connected = False
        self.closed = False
        self.url = self._create_url()

    def _create_url(self):
        import hashlib, base64, time
        appid = self.appid
        api_key = self.api_key
        ts = str(int(time.time()))
        md5 = hashlib.md5((appid + ts).encode('utf-8')).hexdigest()
        signa = base64.b64encode(hashlib.sha1((md5 + api_key).encode('utf-8')).digest()).decode('utf-8')
        lang = 'cn'
        print(f"调试: appid={appid}, api_key={api_key}, ts={ts}, signa={signa}")
        url = f"wss://rtasr.xfyun.cn/v1/ws?appid={appid}&ts={ts}&signa={signa}&lang={lang}"
        return url

    def connect(self):
        import websocket
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        import threading
        self.thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self.thread.start()
        # 等待连接建立
        for _ in range(30):
            if self.connected:
                break
            import time
            time.sleep(0.1)

    def _on_open(self, ws):
        self.connected = True
        # 实时转写无需发送握手参数，直接发送音频帧

    def send_audio(self, audio_bytes, is_last=False):
        if not self.connected or self.closed:
            return
        try:
            self.ws.send(audio_bytes, opcode=websocket.ABNF.OPCODE_BINARY)
            if is_last:
                self.ws.send("{" + '"end": true' + "}")
        except Exception:
            pass

    def _on_message(self, ws, message):
        try:
            print("ASR原始返回：", message)  # 新增调试
            import json
            data = json.loads(message)
            if data.get('code') == 0:
                if 'data' in data and self.on_result:
                    self.on_result(data['data'])
            else:
                if self.on_result:
                    # 返回原始错误内容，便于排查
                    self.on_result(f"[ASR错误] {data.get('message') or message}")
        except Exception as e:
            if self.on_result:
                self.on_result(f"[ASR解析异常] {str(e)}")

    def _on_error(self, ws, error):
        self.closed = True
        if self.on_result:
            self.on_result(f"[ASR连接错误] {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        self.closed = True
        self.connected = False
        if self.on_result:
            self.on_result(f"[ASR连接关闭] {close_status_code} {close_msg}")

    def close(self):
        self.closed = True
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass

class XunfeiRTASRClient:
    def __init__(self, app_id, api_key, on_result=None):
        self.app_id = app_id
        self.api_key = api_key
        self.on_result = on_result
        self.ws = None
        self.trecv = None
        self.connected = False
        self.closed = False

    def connect(self):
        base_url = "ws://rtasr.xfyun.cn/v1/ws"
        ts = str(int(time.time()))
        tt = (self.app_id + ts).encode('utf-8')
        md5 = hashlib.md5()
        md5.update(tt)
        baseString = md5.hexdigest()
        baseString = bytes(baseString, encoding='utf-8')
        apiKey = self.api_key.encode('utf-8')
        signa = hmac.new(apiKey, baseString, hashlib.sha1).digest()
        signa = base64.b64encode(signa)
        signa = str(signa, 'utf-8')
        url = base_url + "?appid=" + self.app_id + "&ts=" + ts + "&signa=" + quote(signa)
        self.ws = create_connection(url)
        self.connected = True
        self.trecv = threading.Thread(target=self.recv)
        self.trecv.start()

    def send_audio(self, audio_bytes, is_last=False):
        if self.connected and not self.closed:
            self.ws.send(audio_bytes, opcode=2)  # opcode=2 for binary
            if is_last:
                self.ws.send(b'{"end": true}')

    def recv(self):
        try:
            while self.ws.connected:
                result = str(self.ws.recv())
                if len(result) == 0:
                    break
                result_dict = json.loads(result)
                if result_dict["action"] == "result":
                    if self.on_result:
                        self.on_result(result_dict["data"])
                if result_dict["action"] == "error":
                    if self.on_result:
                        self.on_result("[RTASR错误] " + result)
                    self.ws.close()
                    self.closed = True
                    return
        except WebSocketConnectionClosedException:
            self.closed = True
        except Exception as e:
            self.closed = True
            if self.on_result:
                self.on_result(f"[RTASR异常] {str(e)}")

    def close(self):
        if self.ws:
            self.ws.close()
        self.connected = False
        self.closed = True 

class XunfeiTranscriptionService:
    def __init__(self):
        self.Host = "ost-api.xfyun.cn"
        self.RequestUriCreate = "/v2/ost/pro_create"
        self.RequestUriQuery = "/v2/ost/query"
        
        # 设置URL
        self.urlCreate = f"https://{self.Host}{self.RequestUriCreate}"
        self.urlQuery = f"https://{self.Host}{self.RequestUriQuery}"
        
        self.HttpMethod = "POST"
        self.APPID = settings.XUNFEI_APP_ID
        self.Algorithm = "hmac-sha256"
        self.HttpProto = "HTTP/1.1"
        self.UserName = settings.XUNFEI_ASR_API_KEY
        self.Secret = settings.XUNFEI_API_SECRET
        
        # 业务参数
        self.BusinessArgsCreate = {
            "language": "zh_cn",
            "accent": "mandarin",
            "domain": "pro_ost_ed",
        }

    def hashlib_256(self, data):
        m = hashlib.sha256(bytes(data.encode(encoding='utf-8'))).digest()
        result = "SHA-256=" + base64.b64encode(m).decode(encoding='utf-8')
        return result

    def httpdate(self, dt):
        weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
        month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                 "Oct", "Nov", "Dec"][dt.month - 1]
        return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekday, dt.day, month,
                                                        dt.year, dt.hour, dt.minute, dt.second)

    def generateSignature(self, digest, uri, date):
        signature_str = f"host: {self.Host}\n"
        signature_str += f"date: {date}\n"
        signature_str += f"{self.HttpMethod} {uri} {self.HttpProto}\n"
        signature_str += f"digest: {digest}"
        print(f"[调试] 签名字符串: {signature_str}")
        signature = hmac.new(bytes(self.Secret.encode('utf-8')),
                           bytes(signature_str.encode('utf-8')),
                           digestmod=hashlib.sha256).digest()
        return base64.b64encode(signature).decode(encoding='utf-8')

    def init_header(self, data, uri):
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        
        digest = self.hashlib_256(data)
        sign = self.generateSignature(digest, uri, date)
        auth_header = f'api_key="{self.UserName}",algorithm="{self.Algorithm}", ' \
                     f'headers="host date request-line digest", signature="{sign}"'
        
        print(f"[调试] 认证头: {auth_header}")
        
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Method": self.HttpMethod,
            "Host": self.Host,
            "Date": date,
            "Digest": digest,
            "Authorization": auth_header,
            "X-Date": date,  # 添加 X-Date 头
        }

    def call_api(self, url, body, headers):
        try:
            print(f"[调试] 请求URL: {url}")
            print(f"[调试] 请求头: {headers}")
            print(f"[调试] 请求体: {body}")
            response = requests.post(url, data=body, headers=headers, timeout=8)
            print(f"[调试] 响应状态码: {response.status_code}")
            print(f"[调试] 响应头: {response.headers}")
            print(f"[调试] 响应内容: {response.text}")
            if response.status_code != 200:
                print(f"[调试] 讯飞API调用失败: {response.content}")
                return None
            return response.json()
        except Exception as e:
            print(f"[调试] 讯飞API调用异常: {str(e)}")
            return None

    def create_task(self, audio_url):
        """创建转写任务"""
        # 确保URL是正确编码的
        if not audio_url.startswith('http'):
            audio_url = f"https://{audio_url}"
        audio_url = quote(audio_url, safe=':/?=')
        
        body = json.dumps({
            "common": {"app_id": self.APPID},
            "business": self.BusinessArgsCreate,
            "data": {
                "audio_src": "http",
                "audio_url": audio_url,
                "encoding": "raw"
            }
        })
        
        headers = self.init_header(body, self.RequestUriCreate)
        return self.call_api(self.urlCreate, body, headers)

    def query_task(self, task_id):
        """查询转写任务状态"""
        body = json.dumps({
            "common": {"app_id": self.APPID},
            "business": {
                "task_id": task_id,
            },
        })
        
        headers = self.init_header(body, self.RequestUriQuery)
        return self.call_api(self.urlQuery, body, headers)

    def get_create_body(self, audio_url):
        return json.dumps({
            "common": {"app_id": self.APPID},
            "business": self.BusinessArgsCreate,
            "data": {
                "audio_src": "http",
                "audio_url": audio_url,
                "encoding": "raw"
            }
        })

    def get_query_body(self, task_id):
        return json.dumps({
            "common": {"app_id": self.APPID},
            "business": {
                "task_id": task_id,
            },
        })

    async def transcribe_audio(self, audio_url):
        """转写音频文件"""
        print(f"[调试] 开始转写音频: {audio_url}")
        
        # 创建任务
        create_body = self.get_create_body(audio_url)
        create_headers = self.init_header(create_body, self.RequestUriCreate)
        create_response = self.call_api(self.urlCreate, create_body, create_headers)
        
        if not create_response or 'data' not in create_response:
            print("[调试] 创建转写任务失败")
            return None
            
        task_id = create_response['data']['task_id']
        print(f"[调试] 创建转写任务成功，task_id: {task_id}")
        
        # 轮询查询结果
        max_retries = 30  # 最多等待5分钟
        query_body = self.get_query_body(task_id)
        query_headers = self.init_header(query_body, self.RequestUriQuery)
        
        for _ in range(max_retries):
            query_response = self.call_api(self.urlQuery, query_body, query_headers)
            if not query_response or 'data' not in query_response:
                print("[调试] 查询转写结果失败")
                return None
                
            status = query_response['data']['task_status']
            if status == '9':  # 转写成功
                print("[调试] 转写成功")
                return query_response['data'].get('result', {}).get('text', '')
            elif status in ['3', '4']:  # 转写失败
                print(f"[调试] 转写失败: {query_response}")
                return None
                
            time.sleep(10)  # 等待10秒后重试
            
        print("[调试] 转写超时")
        return None

class XunfeiASRService:
    def __init__(self, file_path):
        self.lfasr_host = 'https://raasr.xfyun.cn/v2/api'
        self.api_upload = '/upload'
        self.api_get_result = '/getResult'
        self.appid = settings.XUNFEI_APP_ID
        self.secret_key = settings.XUNFEI_ASR_API_KEY
        self.file_path = file_path
        self.ts = str(int(time.time()))
        self.signa = self.get_signa()

    def get_signa(self):
        m2 = hashlib.md5()
        m2.update((self.appid + self.ts).encode('utf-8'))
        md5 = m2.hexdigest()
        md5 = bytes(md5, encoding='utf-8')
        signa = hmac.new(self.secret_key.encode('utf-8'), md5, hashlib.sha1).digest()
        signa = base64.b64encode(signa)
        return str(signa, 'utf-8')

    def upload(self):
        file_len = os.path.getsize(self.file_path)
        file_name = os.path.basename(self.file_path)
        param_dict = {
            'appId': self.appid,
            'signa': self.signa,
            'ts': self.ts,
            'fileSize': file_len,
            'fileName': file_name,
            'duration': "200"
        }
        with open(self.file_path, 'rb') as f:
            data = f.read(file_len)
        response = requests.post(
            url=self.lfasr_host + self.api_upload + "?" + urllib.parse.urlencode(param_dict),
            headers={"Content-type": "application/json"},
            data=data
        )
        result = json.loads(response.text)
        return result

    def get_result(self):
        uploadresp = self.upload()
        print(f"[调试] uploadresp: {uploadresp}")
        if not (uploadresp.get('ok') == 0 or uploadresp.get('code') == '000000'):
            print(f"[调试] 上传失败: {uploadresp}")
            return None
        orderId = None
        if 'content' in uploadresp and 'orderId' in uploadresp['content']:
            orderId = uploadresp['content']['orderId']
        elif 'orderId' in uploadresp:
            orderId = uploadresp['orderId']
        print(f"[调试] orderId: {orderId}")
        if not orderId:
            print(f"[调试] 未获取到orderId: {uploadresp}")
            return None
        param_dict = {
            'appId': self.appid,
            'signa': self.signa,
            'ts': self.ts,
            'orderId': orderId,
            'resultType': "transfer,predict"
        }
        status = 3
        result = None
        while status == 3:
            response = requests.post(
                url=self.lfasr_host + self.api_get_result + "?" + urllib.parse.urlencode(param_dict),
                headers={"Content-type": "application/json"}
            )
            result = json.loads(response.text)
            print(f"[调试] 查询result: {result}")
            status = result['content']['orderInfo']['status']
            if status == 4:
                break
            time.sleep(5)
        if result and (result.get('ok') == 0 or result.get('code') == '000000'):
            try:
                order_result = result['content']['orderResult']
                order_result_json = json.loads(order_result)
                sentences = []
                
                # 优先使用 lattice2（更新的格式）
                if isinstance(order_result_json, dict):
                    if 'lattice2' in order_result_json:
                        for item in order_result_json['lattice2']:
                            if 'json_1best' in item and isinstance(item['json_1best'], dict) and 'st' in item['json_1best']:
                                ws = item['json_1best']['st'].get('rt', [])
                                for seg in ws:
                                    for w in seg.get('ws', []):
                                        for cw in w.get('cw', []):
                                            word = cw.get('w', '')
                                            if word and word != '':  # 跳过空字符
                                                sentences.append(word)
                    # 如果没有 lattice2 才使用 lattice
                    elif 'lattice' in order_result_json:
                        for item in order_result_json['lattice']:
                            if 'json_1best' in item:
                                j1 = json.loads(item['json_1best'])
                                if 'st' in j1:
                                    ws = j1['st'].get('rt', [])
                                    for seg in ws:
                                        for w in seg.get('ws', []):
                                            for cw in w.get('cw', []):
                                                word = cw.get('w', '')
                                                if word and word != '':  # 跳过空字符
                                                    sentences.append(word)
                # 兼容老格式
                elif isinstance(order_result_json, list):
                    for item in order_result_json:
                        if 'onebest' in item:
                            sentences.append(item['onebest'])
                
                text = ''.join(sentences)
                print(f'[调试] 解析文本: {text}')
                return text
            except Exception as e:
                print(f"[调试] 解析结果异常: {str(e)}")
                print(traceback.format_exc())  # 添加详细错误信息
                return None
        print(f"[调试] 获取结果失败: {result}")
        return None

class FileUploadService:
    def __init__(self):
        self.lfasr_host = 'http://upload-ost-api.xfyun.cn/file'
        self.api_init = '/mpupload/init'
        self.api_upload = '/upload'
        self.api_cut = '/mpupload/upload'
        self.api_cut_complete = '/mpupload/complete'
        self.api_cut_cancel = '/mpupload/cancel'
        self.file_piece_size = 5242880  # 5MB
        
        self.app_id = settings.XUNFEI_APP_ID
        self.api_key = settings.XUNFEI_ASR_API_KEY
        self.api_secret = settings.XUNFEI_API_SECRET
        self.request_id = self.get_request_id()
        self.cloud_id = '0'

    def get_request_id(self):
        return time.strftime("%Y%m%d%H%M")

    def hashlib_256(self, data):
        m = hashlib.sha256(bytes(data.encode(encoding='utf-8'))).digest()
        digest = "SHA-256=" + base64.b64encode(m).decode(encoding='utf-8')
        return digest

    def assemble_auth_header(self, request_url, file_data_type, method="", body=""):
        u = urlparse(request_url)
        host = u.hostname
        path = u.path
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        digest = "SHA256=" + self.hashlib_256('')
        signature_origin = f"host: {host}\ndate: {date}\n{method} {path} HTTP/1.1\ndigest: {digest}"
        signature_sha = hmac.new(self.api_secret.encode('utf-8'), signature_origin.encode('utf-8'),
                               digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')
        authorization = f'api_key="{self.api_key}", algorithm="hmac-sha256", ' \
                       f'headers="host date request-line digest", signature="{signature_sha}"'
        
        return {
            "host": host,
            "date": date,
            "authorization": authorization,
            "digest": digest,
            'content-type': file_data_type,
        }

    def call_api(self, url, file_data, file_data_type):
        headers = self.assemble_auth_header(url, file_data_type, method="POST")
        try:
            print(f"[调试] 上传请求 - URL: {url}")
            print(f"[调试] 上传请求 - 头: {headers}")
            response = requests.post(url, data=file_data, headers=headers, timeout=8)
            print(f"[调试] 上传响应 - 状态: {response.status_code}, 内容: {response.text}")
            if response.status_code != 200:
                return None
            return response.json()
        except Exception as e:
            print(f"[调试] 上传异常: {str(e)}")
            return None

    def upload_file(self, file_path):
        """上传文件"""
        try:
            # 直接读取文件内容并进行base64编码
            with open(file_path, 'rb') as f:
                audio_data = f.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # 构建请求体
            body = {
                "common": {"app_id": self.app_id},
                "data": {
                    "audio": audio_base64
                }
            }
            
            # 发送请求
            url = self.lfasr_host + self.api_upload
            headers = {
                'Content-Type': 'application/json',
                'X-Appid': self.app_id,
                'X-CurTime': str(int(time.time())),
                'X-Param': base64.b64encode(json.dumps({}).encode('utf-8')).decode('utf-8')
            }
            
            # 计算签名
            x_checksum_str = self.api_key + headers['X-CurTime'] + headers['X-Param']
            headers['X-CheckSum'] = hashlib.md5(x_checksum_str.encode('utf-8')).hexdigest()
            
            print(f"[调试] 上传请求 - URL: {url}")
            print(f"[调试] 上传请求 - 头: {headers}")
            
            response = requests.post(url, json=body, headers=headers, timeout=30)
            print(f"[调试] 上传响应 - 状态: {response.status_code}, 内容: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    return result['data']['audio_url']
            
            print(f"[调试] 文件上传失败: {response.text}")
            return None
            
        except Exception as e:
            print(f"[调试] 文件上传异常: {str(e)}")
            return None

class CodingProblemService:
    """代码题选择服务"""
    
    def select_problems_for_interview(self, interview, resume, limit=3):
        """
        根据面试和简历信息选择合适的代码题
        
        Args:
            interview: Interview实例
            resume: Resume实例  
            limit: 最大题目数量，默认3道
            
        Returns:
            List[CodingProblem]: 选中的代码题列表
        """
        from .models import CodingProblem
        
        # 获取岗位类型
        position_type = interview.position_type if interview else 'backend'
        
        # 基础查询：根据岗位类型筛选
        queryset = CodingProblem.objects.filter(
            position_types__contains=[position_type]
        )
        
        # 如果没有指定岗位类型的题目，使用通用题目
        if not queryset.exists():
            queryset = CodingProblem.objects.all()
        
        # 根据简历信息调整难度和标签偏好
        difficulty_preference = self._get_difficulty_preference(resume)
        tag_preferences = self._get_tag_preferences(resume, position_type)
        
        # 按难度筛选
        if difficulty_preference:
            difficulty_queryset = queryset.filter(difficulty=difficulty_preference)
            if difficulty_queryset.exists():
                queryset = difficulty_queryset
        
        # 按标签偏好排序
        problems = list(queryset.order_by('?')[:limit * 2])  # 获取更多候选题目
        
        # 根据标签匹配度排序
        scored_problems = []
        for problem in problems:
            score = self._calculate_problem_score(problem, tag_preferences, resume)
            scored_problems.append((problem, score))
        
        # 按分数排序并取前limit个
        scored_problems.sort(key=lambda x: x[1], reverse=True)
        selected_problems = [problem for problem, score in scored_problems[:limit]]
        
        return selected_problems
    
    def _get_difficulty_preference(self, resume):
        """根据简历推断合适的题目难度"""
        if not resume:
            return 'medium'
        
        # 简单的经验值判断逻辑
        work_experience_count = 0
        project_count = 0
        
        if resume:
            try:
                work_experience_count = resume.work_experiences.count()
                project_count = resume.project_experiences.count()
            except Exception:
                work_experience_count = 0
                project_count = 0
        
        total_experience = work_experience_count + project_count
        
        if total_experience == 0:
            return 'easy'
        elif total_experience <= 2:
            return 'medium'
        else:
            return 'hard'
    
    def _get_tag_preferences(self, resume, position_type):
        """根据简历和岗位类型获取标签偏好"""
        preferences = []
        
        # 根据岗位类型添加基础标签
        position_tag_map = {
            'backend': ['数组', '字符串', '哈希表', '栈', '队列', '链表', '树', '数据库'],
            'frontend': ['数组', '字符串', '哈希表', '树', 'DOM', '算法'],
            'algo': ['动态规划', '贪心', '回溯', '分治', '图', '树', '数学'],
            'pm': ['逻辑', '数学', '概率'],
            'qa': ['逻辑', '边界条件', '测试']
        }
        
        preferences.extend(position_tag_map.get(position_type, ['数组', '字符串']))
        
        # 根据简历内容添加相关标签（简化逻辑）
        if resume:
            # 分析期望职位
            if resume.expected_position:
                expected_lower = resume.expected_position.lower()
                if 'java' in expected_lower:
                    preferences.extend(['面向对象', 'Java'])
                if 'python' in expected_lower:
                    preferences.extend(['Python', '脚本'])
                if 'react' in expected_lower or 'vue' in expected_lower:
                    preferences.extend(['前端', 'JavaScript'])
        
        return list(set(preferences))  # 去重
    
    def _calculate_problem_score(self, problem, tag_preferences, resume):
        """计算题目匹配分数"""
        score = 0
        
        # 标签匹配分数
        problem_tags = problem.tags or []
        tag_matches = len(set(problem_tags) & set(tag_preferences))
        score += tag_matches * 10
        
        # 公司匹配分数（如果简历中有相关工作经验）
        if resume:
            try:
                for work_exp in resume.work_experiences.all():
                    if work_exp.company_name and problem.companies:
                        if work_exp.company_name in problem.companies:
                            score += 20
            except Exception:
                pass
        
        # 随机因子，增加多样性
        import random
        score += random.randint(0, 5)
        
        return score 

from knowledge_base.services import XunfeiSparkService

class InterviewEvaluationService:
    """面试评估服务"""
    
    def __init__(self):
        self.spark_service = XunfeiSparkService()
    
    def get_evaluation_result(self, interview_id):
        """获取面试评估结果"""
        from .models import Interview, InterviewAnswer, InterviewResult
        
        try:
            # 获取面试记录及其所有答案
            interview = Interview.objects.get(id=interview_id)
            questions = interview.question_queue
            answers = InterviewAnswer.objects.filter(interview=interview)
            
            if not answers.exists():
                return None
            
            # 计算六个维度的平均分
            dimensions = [
                '专业知识水平', '技能匹配度', '语言表达能力',
                '逻辑思维能力', '创新能力', '应变抗压能力'
            ]
            
            scores = []
            for dimension in dimensions:
                field_name = {
                    '专业知识水平': 'professional_knowledge',
                    '技能匹配度': 'skill_matching',
                    '语言表达能力': 'communication_skills',
                    '逻辑思维能力': 'logical_thinking',
                    '创新能力': 'innovation_ability',
                    '应变抗压能力': 'stress_handling'
                }[dimension]
                
                avg_score = answers.aggregate(
                    avg_score=models.Avg(field_name)
                )['avg_score'] or 0
                scores.append(round(avg_score * 20, 1))  # 转换为百分制
            
            # 统计知识点分布
            knowledge_points = {}
            for answer in answers:
                if answer.knowledge_points:
                    for point in answer.knowledge_points:
                        knowledge_points[point] = knowledge_points.get(point, 0) + 1
            
            # 转换为饼图数据
            pie_points = [
                {'label': point, 'value': count}
                for point, count in knowledge_points.items()
            ]
            
            # 计算知识点掌握情况
            mastery_data = {}
            for answer in answers:
                if answer.knowledge_points and answer.correctness_score:
                    for point in answer.knowledge_points:
                        if point not in mastery_data:
                            mastery_data[point] = {'total': 0, 'count': 0}
                        mastery_data[point]['total'] += answer.correctness_score
                        mastery_data[point]['count'] += 1
            
            # 转换为柱状图数据
            bar_labels = []
            bar_accuracy = []
            for point, data in mastery_data.items():
                bar_labels.append(point)
                accuracy = data['total'] / (data['count'] * 5)  # 转换为0-1的比例
                bar_accuracy.append(round(accuracy, 2))
            
            # 生成所有评论（合并为一个AI调用）
            all_comments = self._generate_all_comments(dimensions, scores, pie_points, bar_labels, bar_accuracy)
            radar_comment = all_comments.get('radar', '')
            pie_comment = all_comments.get('pie', '')
            bar_comment = all_comments.get('bar', '')
            
            # 计算总分
            total_score = round(sum(scores) / len(scores), 1)
            
            # 获取上一次面试结果进行对比
            last_compare = self._get_last_compare_result(interview, dimensions, scores)
            
            # 生成总结
            summary = self._generate_summary(interview, questions, answers, scores, knowledge_points)
            
            # 存储评估结果到新表
            try:
                # 检查是否已存在评估结果，如果存在则更新，否则创建新的
                interview_result, created = InterviewResult.objects.get_or_create(
                    interview=interview,
                    user=interview.user,
                    defaults={
                        'radar_dimensions': dimensions,
                        'radar_scores': scores,
                        'radar_comment': radar_comment,
                        'pie_points': pie_points,
                        'pie_comment': pie_comment,
                        'bar_labels': bar_labels,
                        'bar_accuracy': bar_accuracy,
                        'bar_comment': bar_comment,
                        'total_score': total_score,
                        'last_compare': last_compare or {},
                        'star_summary': summary.get('starStructure', ''),
                        'technical_summary': summary.get('technicalSummary', '')
                    }
                )
                
                # 如果已存在，则更新数据
                if not created:
                    interview_result.radar_dimensions = dimensions
                    interview_result.radar_scores = scores
                    interview_result.radar_comment = radar_comment
                    interview_result.pie_points = pie_points
                    interview_result.pie_comment = pie_comment
                    interview_result.bar_labels = bar_labels
                    interview_result.bar_accuracy = bar_accuracy
                    interview_result.bar_comment = bar_comment
                    interview_result.total_score = total_score
                    interview_result.last_compare = last_compare or {}
                    interview_result.star_summary = summary.get('starStructure', '')
                    interview_result.technical_summary = summary.get('technicalSummary', '')
                    interview_result.save()
                
                print(f"[调试] 评估结果已{'创建' if created else '更新'}到InterviewResult表，ID: {interview_result.id}")
                
            except Exception as e:
                print(f"[调试] 存储评估结果到InterviewResult表失败: {e}")
                import traceback
                print(f"[调试] 错误详情: {traceback.format_exc()}")
            
            # 获取每个问题的AI分析详情
            question_analyses = []
            for answer in answers:
                question_analyses.append({
                    'question': answer.question,
                    'answer': answer.answer,
                    'ai_analysis': answer.ai_analysis,
                    'knowledge_points': answer.knowledge_points,
                    # 'scores': {
                    #     'professional_knowledge': answer.professional_knowledge,
                    #     'skill_matching': answer.skill_matching,
                    #     'communication_skills': answer.communication_skills,
                    #     'logical_thinking': answer.logical_thinking,
                    #     'innovation_ability': answer.innovation_ability,
                    #     'stress_handling': answer.stress_handling,
                    #     'correctness_score': answer.correctness_score
                    # },
                    # 'created_at': answer.created_at.isoformat() if answer.created_at else None
                })
            

            
            return {
                'radar': {
                    'data': {
                        'dimensions': dimensions,
                        'scores': scores
                    },
                    'comment': radar_comment
                },
                'pie': {
                    'data': {
                        'points': pie_points
                    },
                    'comment': pie_comment
                },
                'bar': {
                    'data': {
                        'labels': bar_labels,
                        'accuracy': bar_accuracy
                    },
                    'comment': bar_comment
                },
                'score': total_score,
                'lastCompare': last_compare,
                'summary': summary,
                'question_analyses': question_analyses
            }
            
        except Interview.DoesNotExist:
            return None
        except Exception as e:
            print(f"生成评估结果时出错: {e}")
            return None
    
    def _generate_all_comments(self, dimensions, scores, pie_points, bar_labels, bar_accuracy):
        """生成所有评论（合并为一个AI调用）"""
        try:
            # 找出最高和最低分的维度
            max_score_idx = scores.index(max(scores))
            min_score_idx = scores.index(min(scores))
            
            # 找出知识点分布最多和最少的
            sorted_pie = sorted(pie_points, key=lambda x: x['value'], reverse=True)
            pie_most = sorted_pie[0] if sorted_pie else {'label': '无', 'value': 0}
            pie_least = sorted_pie[-1] if sorted_pie else {'label': '无', 'value': 0}
            
            # 找出掌握最好和最差的知识点
            max_acc_idx = bar_accuracy.index(max(bar_accuracy)) if bar_accuracy else 0
            min_acc_idx = bar_accuracy.index(min(bar_accuracy)) if bar_accuracy else 0
            
            prompt = f"""请根据以下面试数据，生成三个简短的点评：

1. 能力维度评估：
{dimensions[max_score_idx]}: {scores[max_score_idx]}分（最高）
{dimensions[min_score_idx]}: {scores[min_score_idx]}分（最低）

2. 知识点分布：
{pie_most['label']}: {pie_most['value']}次（最多）
{pie_least['label']}: {pie_least['value']}次（最少）

3. 知识点掌握度：
{bar_labels[max_acc_idx] if bar_labels else '无'}: {bar_accuracy[max_acc_idx]*100:.0f}%（最高）
{bar_labels[min_acc_idx] if bar_labels else '无'}: {bar_accuracy[min_acc_idx]*100:.0f}%（最低）

请按以下格式返回：

雷达图评论：
[针对能力维度的点评，突出优势，指出改进方向，不超过30字]

知识点分布评论：
[评价分布是否均衡，给出针对性建议，不超过30字]

掌握度评论：
[肯定优势，指出提升空间，不超过30字]
"""
            
            response = self.spark_service._send_message(prompt)
            
            # 解析响应
            comments = {
                'radar': f"{dimensions[max_score_idx]}表现突出，{dimensions[min_score_idx]}方面需加强。",
                'pie': "题目分布较均衡，建议系统性复习。",
                'bar': f"{bar_labels[max_acc_idx] if bar_labels else '无'}掌握扎实，{bar_labels[min_acc_idx] if bar_labels else '无'}模块有待提高。"
            }
            
            if response:
                lines = response.split('\n')
                current_section = None
                
                for line in lines:
                    line = line.strip()
                    if '雷达图评论：' in line:
                        current_section = 'radar'
                    elif '知识点分布评论：' in line:
                        current_section = 'pie'
                    elif '掌握度评论：' in line:
                        current_section = 'bar'
                    elif line and current_section and line.startswith('[') and line.endswith(']'):
                        comment = line[1:-1]  # 移除方括号
                        if comment:
                            comments[current_section] = comment
            
            return comments
            
        except Exception as e:
            print(f"生成合并评论出错: {e}")
            return {
                'radar': f"{dimensions[max_score_idx]}表现突出，{dimensions[min_score_idx]}方面需加强。",
                'pie': "题目分布较均衡，建议系统性复习。",
                'bar': f"{bar_labels[max_acc_idx] if bar_labels else '无'}掌握扎实，{bar_labels[min_acc_idx] if bar_labels else '无'}模块有待提高。"
            }
    

    
    def _get_last_compare_result(self, interview, dimensions, scores):
        """获取与上一次面试的对比结果"""
        from .models import Interview, InterviewAnswer
        
        try:
            # 获取同一用户之前的面试记录
            last_interview = (
                Interview.objects
                .filter(
                    user=interview.user,
                    interview_time__lt=interview.interview_time,
                    position_type=interview.position_type
                )
                .order_by('-interview_time')
                .first()
            )
            
            if not last_interview:
                return None
                
            # 直接计算上一次面试的分数，避免递归调用
            last_answers = InterviewAnswer.objects.filter(interview=last_interview)
            if not last_answers.exists():
                return None
            
            # 计算上一次面试的六个维度平均分,
            # TODO:存储每次的面试结果，直接取上一次的分数
            last_scores = []
            for dimension in dimensions:
                field_name = {
                    '专业知识水平': 'professional_knowledge',
                    '技能匹配度': 'skill_matching',
                    '语言表达能力': 'communication_skills',
                    '逻辑思维能力': 'logical_thinking',
                    '创新能力': 'innovation_ability',
                    '应变抗压能力': 'stress_handling'
                }[dimension]
                
                avg_score = last_answers.aggregate(
                    avg_score=models.Avg(field_name)
                )['avg_score'] or 0
                last_scores.append(round(avg_score * 20, 1))  # 转换为百分制
            
            # 计算分数变化
            score_change = round(
                sum(scores) / len(scores) - sum(last_scores) / len(last_scores),
                1
            )
            
            # 计算各维度变化
            radar_delta = []
            for i in range(len(dimensions)):
                delta = round(scores[i] - last_scores[i], 1)
                radar_delta.append(delta)
            
            return {
                'scoreChange': score_change,
                'radarDelta': radar_delta
            }
            
        except Exception as e:
            print(f"获取对比结果出错: {e}")
            return None
    
    def _generate_summary(self, interview, questions, answers, scores, knowledge_points):
        """生成面试总结"""
        try:
            print(f"[调试] 开始生成面试总结，面试岗位: {interview.position_name}")
            print(f"[调试] 面试表现总分: {sum(scores)/len(scores):.1f}分")
            print(f"[调试] 面试问题: {questions}")
            print(f"[调试] 涉及知识点: {', '.join(knowledge_points.keys())}")
            
            # 获取本次面试所有问题的ai_analysis文本
            all_ai_analysis = []
            for answer in answers:
                if answer.ai_analysis and answer.ai_analysis.strip():
                    all_ai_analysis.append(answer.ai_analysis.strip())
            
            ai_analysis_text = '\n'.join(all_ai_analysis) if all_ai_analysis else '暂无AI分析结果'
            
            # 合并两个提示词，减少AI调用次数
            combined_prompt = f"""请根据以下面试信息，生成两个总结：

面试岗位：{interview.position_name}
面试表现：总分{sum(scores)/len(scores):.1f}分
所有问题：{', '.join(questions)}
面试者给出答案的AI分析结果：
{ai_analysis_text}

请按以下格式返回：

STAR分析：
[生成面试建议和总结，可结合STAR分析，结合每个问题的答案分析和所涉及知识点，总字数不超过100字]

技术总结：
[一句简短精炼的技术能力总结，不超过30个字，突出技术特点和进步，语气要积极专业]
"""
            print(f"[调试] 合并提示词: {combined_prompt[:200]}...")
            
            combined_response = self.spark_service._send_message(combined_prompt)
            print(f"[调试] 合并响应结果: {combined_response}")
            
            # 解析响应
            star_structure = None
            technical_summary = None
            
            if combined_response:
                lines = combined_response.split('\n')
                star_start = -1
                tech_start = -1
                
                for i, line in enumerate(lines):
                    if 'STAR分析：' in line or 'STAR:' in line:
                        star_start = i
                    elif '技术总结：' in line or '技术总结:' in line:
                        tech_start = i
                
                # 提取STAR分析
                if star_start >= 0:
                    star_lines = []
                    for i in range(star_start + 1, len(lines)):
                        if tech_start >= 0 and i >= tech_start:
                            break
                        if lines[i].strip():
                            star_lines.append(lines[i].strip())
                    star_structure = ' '.join(star_lines)
                
                # 提取技术总结
                if tech_start >= 0:
                    tech_lines = []
                    for i in range(tech_start + 1, len(lines)):
                        if lines[i].strip():
                            tech_lines.append(lines[i].strip())
                    technical_summary = ' '.join(tech_lines)
            
            # 检查返回结果
            if not star_structure or star_structure.strip() == "":
                print("[调试] STAR分析解析失败，使用默认值")
                star_structure = 'S: 遇到系统设计题；T: 需要高并发分析；A: 正确使用缓存和分布式锁；R: 得到面试官好评。'
            else:
                print(f"[调试] STAR分析成功，长度: {len(star_structure)}")
                
            if not technical_summary or technical_summary.strip() == "":
                print("[调试] 技术总结解析失败，使用默认值")
                technical_summary = '系统设计能力进步明显，表达清晰。'
            else:
                print(f"[调试] 技术总结成功，长度: {len(technical_summary)}")
            
            return {
                'starStructure': star_structure.strip(),
                'technicalSummary': technical_summary.strip()
            }
            
        except Exception as e:
            print(f"[调试] 生成面试总结出错: {e}")
            import traceback
            print(f"[调试] 错误详情: {traceback.format_exc()}")
            return {
                'starStructure': 'S: 遇到系统设计题；T: 需要高并发分析；A: 正确使用缓存和分布式锁；R: 得到面试官好评。',
                'technicalSummary': '系统设计能力进步明显，表达清晰。'
            } 

    def get_user_overall_evaluation(self, user):
        """获取用户总体能力评估"""
        from .models import Interview, InterviewAnswer, InterviewResult
        from django.db.models import Avg, Count
        from django.db.models.functions import TruncDate
        
        try:
            # 获取用户所有面试评估结果
            interview_results = InterviewResult.objects.filter(user=user).order_by('created_at')
            if not interview_results.exists():
                return None
            
            # 1. 计算六个维度的平均分（从InterviewResult中读取）
            all_dimensions = []
            all_scores = []
            
            for result in interview_results:
                if result.radar_dimensions and result.radar_scores:
                    all_dimensions.extend(result.radar_dimensions)
                    all_scores.extend(result.radar_scores)
            
            if not all_scores:
                return None
            
            # 计算平均分
            dimensions = [
                '专业知识水平', '技能匹配度', '语言表达能力',
                '逻辑思维能力', '创新能力', '应变抗压能力'
            ]
            
            # 按维度分组计算平均分
            dimension_scores = {dim: [] for dim in dimensions}
            for i, dim in enumerate(all_dimensions):
                if dim in dimension_scores and i < len(all_scores):
                    dimension_scores[dim].append(all_scores[i])
            
            scores = []
            for dimension in dimensions:
                avg_score = sum(dimension_scores[dimension]) / len(dimension_scores[dimension]) if dimension_scores[dimension] else 0
                scores.append(round(avg_score, 1))
            
            # 2. 计算知识点掌握进度（从InterviewResult中读取）
            all_bar_labels = []
            all_bar_accuracy = []
            
            for result in interview_results:
                if result.bar_labels and result.bar_accuracy:
                    all_bar_labels.extend(result.bar_labels)
                    all_bar_accuracy.extend(result.bar_accuracy)
            
            # 按知识点分组计算平均掌握度
            knowledge_mastery = {}
            for i, label in enumerate(all_bar_labels):
                if i < len(all_bar_accuracy):
                    if label not in knowledge_mastery:
                        knowledge_mastery[label] = []
                    knowledge_mastery[label].append(all_bar_accuracy[i])
            
            mastery_labels = []
            mastery_progress = []
            for label, accuracies in knowledge_mastery.items():
                mastery_labels.append(label)
                avg_accuracy = sum(accuracies) / len(accuracies)
                mastery_progress.append(round(avg_accuracy, 2))
            
            # 3. 计算总分趋势（从InterviewResult中读取）
            trends = interview_results.values('created_at').annotate(
                avg_score=Avg('total_score')
            ).order_by('created_at')
            
            trend_dates = []
            trend_scores = []
            for trend in trends:
                trend_dates.append(trend['created_at'].strftime('%Y-%m-%d'))
                trend_scores.append(round(trend['avg_score'], 1))
            
            # 4. 生成总体评价
            summary = self._generate_overall_summary(
                dimensions, scores,
                mastery_labels, mastery_progress,
                trend_scores
            )
            
            return {
                'radar': {
                    'dimensions': dimensions,
                    'scores': scores
                },
                'masteryProgress': {
                    'labels': mastery_labels,
                    'progress': mastery_progress
                },
                'trend': {
                    'dates': trend_dates,
                    'scores': trend_scores
                },
                'summary': summary
            }
            
        except Exception as e:
            print(f"生成总体评估结果失败: {e}")
            print(traceback.format_exc())
            return None
    
    def _generate_overall_summary(self, dimensions, scores, mastery_labels, mastery_progress, trend_scores):
        """生成总体评价"""
        try:
            # 找出最强和最弱维度
            max_score_idx = scores.index(max(scores))
            min_score_idx = scores.index(min(scores))
            
            # 找出掌握最好和最差的知识点
            max_progress_idx = mastery_progress.index(max(mastery_progress))
            min_progress_idx = mastery_progress.index(min(mastery_progress))
            
            # 计算分数趋势
            score_trend = "上升" if trend_scores[-1] > trend_scores[0] else "下降" if trend_scores[-1] < trend_scores[0] else "稳定"
            
            prompt = f"""请根据以下面试数据，生成一句简短的总体评价：

1. 能力维度：
- 最强：{dimensions[max_score_idx]} ({scores[max_score_idx]}分)
- 最弱：{dimensions[min_score_idx]} ({scores[min_score_idx]}分)

2. 知识点掌握：
- 最好：{mastery_labels[max_progress_idx]} ({mastery_progress[max_progress_idx]*100:.0f}%)
- 最差：{mastery_labels[min_progress_idx]} ({mastery_progress[min_progress_idx]*100:.0f}%)

3. 分数趋势：{score_trend}

要求：
1. 评价要简短精炼，不超过50个字
2. 突出进步和优势
3. 给出改进建议
4. 语气要积极专业
"""
            summary = self.spark_service._send_message(prompt)
            return summary.strip() if summary else f"你在{dimensions[max_score_idx]}表现突出，{mastery_labels[max_progress_idx]}掌握稳定，{dimensions[min_score_idx]}仍有提升空间。"
            
        except Exception as e:
            print(f"生成总体评价失败: {e}")
            return "你在技术面试中展现出良好的专业能力，建议继续保持并加强薄弱环节。" 