import json
import time
import hmac
import base64
import hashlib
import websocket
import threading
from datetime import datetime
from urllib.parse import urlencode
from typing import List, Dict, Any
from django.conf import settings
from django.db import models
from django.db.models import Q
from users.models import Resume
from .models import JobPosition, KnowledgeBaseEntry, InterviewQuestion

class XunfeiSparkService:
    """讯飞星火API服务"""
    
    def __init__(self):
        self.app_id = getattr(settings, 'XUNFEI_APP_ID', '')
        self.api_secret = getattr(settings, 'XUNFEI_API_SECRET', '')
        self.api_key = getattr(settings, 'XUNFEI_API_KEY', '')
        self.spark_url = "wss://spark-api.xf-yun.com/v3.1/chat"
        
    def _create_url(self):
        """生成鉴权url"""
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # 拼接字符串
        signature_origin = f"host: spark-api.xf-yun.com\ndate: {date}\nGET /v3.1/chat HTTP/1.1"
        
        # 使用hmac-sha256进行加密
        signature_sha = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        
        signature_sha_base64 = base64.b64encode(signature_sha).decode()
        authorization_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode()
        
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": "spark-api.xf-yun.com"
        }
        print(f"调试: appid={appid}, api_key={api_key}, ts={ts}, signa={signa}")
    
        # 拼接鉴权参数，生成url
        url = f"{self.spark_url}?{urlencode(v)}"
        
        return url
    
    def _send_message(self, message: str) -> str:
        """发送消息到星火API并获取回复"""
        url = self._create_url()
        
        # 构建请求数据
        data = {
            "header": {
                "app_id": self.app_id,
                "uid": "12345"
            },
            "parameter": {
                "chat": {
                    "domain": "general",
                    "temperature": 0.7,
                    "max_tokens": 2048
                }
            },
            "payload": {
                "message": {
                    "text": [
                        {"role": "user", "content": message}
                    ]
                }
            }
        }
        
        response_text = ""
        
        def on_message(ws, message):
            nonlocal response_text
            data = json.loads(message)
            code = data['header']['code']
            if code != 0:
                print(f'请求错误: {code}, {data}')
                ws.close()
            else:
                text = data['payload']['choices']['text'][0]['content']
                response_text += text
                if data['header']['status'] == 2:
                    ws.close()
        
        def on_error(ws, error):
            print(f"错误: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print("连接关闭")
        
        def on_open(ws):
            ws.send(json.dumps(data))
        
        # 创建WebSocket连接
        ws = websocket.WebSocketApp(
            url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # 在新线程中运行WebSocket
        wst = threading.Thread(target=ws.run_forever)
        wst.daemon = True
        wst.start()
        
        # 等待响应完成
        while ws.sock and ws.sock.connected:
            time.sleep(0.1)
        
        return response_text
    
    def generate_interview_questions(self, job_position: JobPosition, resume: Resume) -> List[str]:
        """根据岗位和简历生成面试问题"""
        
        # 构建简历信息
        resume_info = self._build_resume_info(resume)
        
        # 构建提示词
        prompt = f"""
你是一位资深的面试官，需要根据候选人的简历和岗位要求，生成5个有针对性的面试问题。

岗位信息：
- 岗位名称：{job_position.name}
- 公司名称：{job_position.company_name}
- 岗位描述：{job_position.description}
- 岗位要求：{job_position.requirements or '无具体要求'}

候选人简历信息：
{resume_info}

请根据以上信息，生成5个面试问题。问题应该：
1. 结合候选人的具体经历和技能
2. 针对岗位要求进行提问
3. 包含技术问题、项目问题、行为问题等不同类型
4. 问题要有深度，能够考察候选人的实际能力

请直接返回5个问题，每个问题一行，不要包含序号或其他格式。
"""
        
        try:
            response = self._send_message(prompt)
            # 解析响应，提取问题
            questions = [q.strip() for q in response.split('\n') if q.strip()]
            # 确保返回5个问题
            return questions[:5] if len(questions) >= 5 else questions
        except Exception as e:
            print(f"生成面试问题时出错: {e}")
            return []
    
    def _build_resume_info(self, resume: Resume) -> str:
        """构建简历信息字符串"""
        info_parts = []
        
        # 基本信息
        info_parts.append(f"姓名：{resume.name}")
        info_parts.append(f"年龄：{resume.age}")
        info_parts.append(f"学历：{resume.education_level}")
        info_parts.append(f"期望职位：{resume.expected_position}")
        
        # 工作经历
        if resume.work_experiences.exists():
            info_parts.append("\n工作经历：")
            for exp in resume.work_experiences.all():
                info_parts.append(f"- {exp.company_name} {exp.position} ({exp.start_date} - {exp.end_date or '至今'})")
                info_parts.append(f"  工作内容：{exp.work_content}")
        
        # 项目经历
        if resume.project_experiences.exists():
            info_parts.append("\n项目经历：")
            for proj in resume.project_experiences.all():
                info_parts.append(f"- {proj.project_name} 角色：{proj.project_role}")
                info_parts.append(f"  项目内容：{proj.project_content}")
        
        # 教育经历
        if resume.education_experiences.exists():
            info_parts.append("\n教育经历：")
            for edu in resume.education_experiences.all():
                info_parts.append(f"- {edu.school_name} {edu.major} {edu.education_level}")
        
        return "\n".join(info_parts)

class KnowledgeBaseService:
    """知识库检索服务"""
    
    def __init__(self):
        self.spark_service = XunfeiSparkService()
    
    def search_relevant_questions(self, job_position: JobPosition, resume: Resume, limit: int = 5) -> List[Dict[str, Any]]:
        """从知识库中检索相关问题"""
        
        # 从知识库中检索相关问题
        knowledge_questions = self._search_knowledge_base(job_position, resume, limit)
        
        # 使用星火API生成个性化问题
        generated_questions = self.spark_service.generate_interview_questions(job_position, resume)
        
        # 合并结果
        all_questions = []
        
        # 添加知识库问题
        for q in knowledge_questions:
            all_questions.append({
                'question': q.question,
                'source': 'knowledge_base',
                'category': q.category,
                'difficulty': q.difficulty_level,
                'tags': q.tags
            })
        
        # 添加生成的问题
        for q in generated_questions:
            all_questions.append({
                'question': q,
                'source': 'generated',
                'category': 'custom',
                'difficulty': 3,
                'tags': []
            })
        
        # 记录生成历史
        self._save_interview_questions(job_position, resume, all_questions)
        
        return all_questions[:limit]
    
    def _search_knowledge_base(self, job_position: JobPosition, resume: Resume, limit: int) -> List[KnowledgeBaseEntry]:
        """从知识库中检索相关问题，优先匹配岗位类型和公司名称"""
        # 基于岗位名称和描述进行关键词匹配
        keywords = self._extract_keywords(str(job_position.name) + " " + str(job_position.description))
        
        # 先查找岗位类型和公司名称都匹配的题目
        query = KnowledgeBaseEntry.objects.filter(
            position_type=job_position.position_type,
            company_name=job_position.company_name
        )
        for keyword in keywords:
            query = query.filter(
                Q(question__icontains=keyword) |
                Q(answer__icontains=keyword) |
                Q(tags__contains=[keyword])
            )
        results = list(query.order_by('difficulty_level', '-created_at')[:limit])
        
        # 如果不足limit，再补充岗位类型匹配但公司不限的题目
        if len(results) < limit:
            query2 = KnowledgeBaseEntry.objects.filter(
                position_type=job_position.position_type
            ).exclude(company_name=job_position.company_name)
            for keyword in keywords:
                query2 = query2.filter(
                    Q(question__icontains=keyword) |
                    Q(answer__icontains=keyword) |
                    Q(tags__contains=[keyword])
                )
            extra = list(query2.order_by('difficulty_level', '-created_at')[:(limit-len(results))])
            results.extend(extra)
        
        return results[:limit]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取，可以根据需要优化
        common_keywords = [
            'python', 'java', 'javascript', 'react', 'vue', 'angular', 'node.js',
            'django', 'flask', 'spring', 'mysql', 'postgresql', 'mongodb',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'git', 'linux',
            '算法', '数据结构', '设计模式', '微服务', '分布式', '高并发',
            '前端', '后端', '全栈', '移动端', 'ios', 'android', 'flutter'
        ]
        
        text_lower = text.lower()
        found_keywords = [kw for kw in common_keywords if kw in text_lower]
        
        # 如果没有找到关键词，返回一些通用词
        if not found_keywords:
            found_keywords = ['技术', '项目', '经验']
        
        return found_keywords
    
    def _save_interview_questions(self, job_position: JobPosition, resume: Resume, questions: List[Dict[str, Any]]):
        """保存面试问题记录"""
        generation_context = f"岗位：{job_position.name}，公司：{job_position.company_name}"
        
        InterviewQuestion.objects.create(
            job_position=job_position,
            resume=resume,
            questions=questions,
            generation_context=generation_context
        ) 