import base64
import hashlib
import hmac
import json
import threading
import time
from datetime import datetime
from urllib.parse import urlencode, quote
import websocket
from websocket import create_connection, WebSocketConnectionClosedException
from django.conf import settings

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
        self.api_key = getattr(settings, 'XUNFEI_ASR_API_KEY', '')
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
        print(f"调试: appid={appid}, api_key={api_key}, ts={ts}, signa={signa}")
        url = f"wss://rtasr.xfyun.cn/v1/ws?appid={appid}&ts={ts}&signa={signa}"
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
        work_experience_count = getattr(resume, 'work_experiences', [])
        project_count = getattr(resume, 'project_experiences', [])
        if hasattr(work_experience_count, 'count'):
            work_experience_count = work_experience_count.count()
        else:
            work_experience_count = len(work_experience_count) if work_experience_count else 0
        if hasattr(project_count, 'count'):
            project_count = project_count.count()
        else:
            project_count = len(project_count) if project_count else 0
        
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
        if resume and hasattr(resume, 'work_experiences'):
            for work_exp in resume.work_experiences.all():
                if work_exp.company_name and problem.companies:
                    if work_exp.company_name in problem.companies:
                        score += 20
        
        # 随机因子，增加多样性
        import random
        score += random.randint(0, 5)
        
        return score 