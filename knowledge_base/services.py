import json
import time
import hmac
import base64
import hashlib
import websocket
import threading
import re
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
    
    def generate_interview_questions(self, prompt: str) -> str:
        """根据提示词生成面试问题"""
        try:
            # 从提示词中提取关键信息
            import re
            position_match = re.search(r'应聘岗位：(.*?)\n', prompt)
            position_type_match = re.search(r'岗位类型：(.*?)\n', prompt)
            skills_match = re.search(r'技能特长：(.*?)\n', prompt)
            projects_match = re.search(r'项目经验：(.*?)\n', prompt)
            
            position = position_match.group(1) if position_match else ''
            position_type = position_type_match.group(1) if position_type_match else ''
            skills = skills_match.group(1) if skills_match else ''
            projects = projects_match.group(1) if projects_match else ''
            
            print(f"[调试] 提取的信息 - 岗位: {position}, 类型: {position_type}, 技能: {skills}")
            
            # 先尝试使用基于规则的问题生成，避免API调用
            rule_based_questions = self._generate_rule_based_questions(
                position, position_type, skills, projects
            )
            
            if rule_based_questions:
                print(f"[调试] 使用基于规则的问题生成，共{len(rule_based_questions)}个问题")
                return '\n'.join([f"{i+1}. {q}" for i, q in enumerate(rule_based_questions)])
            
            # 如果规则生成失败，再尝试API调用（设置超时）
            print("[调试] 尝试调用AI服务生成问题")
            
            # 构建简化的提示词
            simple_prompt = f"""请为{position_type}岗位生成8个面试问题，要求简洁专业：

岗位：{position}
技能：{skills}

请直接列出问题，每行一个："""
            
            # 设置超时调用AI服务（使用线程超时）
            import threading
            result = {"response": None, "error": None}
            
            def call_ai_service():
                try:
                    result["response"] = self.spark_service._send_message(simple_prompt)
                except Exception as e:
                    result["error"] = str(e)
            
            thread = threading.Thread(target=call_ai_service)
            thread.start()
            thread.join(timeout=5)  # 5秒超时
            
            if thread.is_alive():
                print("[调试] AI服务调用超时")
                return ""
            elif result["error"]:
                print(f"[调试] AI服务调用失败: {result['error']}")
                return ""
            elif result["response"]:
                print(f"[调试] AI服务返回: {result['response'][:100]}...")
                return result["response"]
            else:
                print("[调试] AI服务返回空结果")
                return ""
            
        except Exception as e:
            print(f"[调试] 生成面试问题时出错: {e}")
            import traceback
            print(traceback.format_exc())
            return ""
    
    def _generate_rule_based_questions(self, position, position_type, skills, projects):
        """基于规则生成问题，不依赖API"""
        try:
            questions = []
            
            # 基础问题
            questions.append("请简单介绍一下你的技术背景和主要技能。")
            
            # 根据岗位类型生成专业问题
            if position_type == 'backend':
                questions.extend([
                    "你在后端开发中使用过哪些技术栈？请重点介绍你最熟悉的框架。",
                    "请描述一下你是如何设计和优化数据库的？",
                    "在处理高并发场景时，你有哪些经验和解决方案？",
                    "请介绍一下你对微服务架构的理解和实践。"
                ])
            elif position_type == 'frontend':
                questions.extend([
                    "你熟悉哪些前端框架？请介绍你最擅长的技术栈。",
                    "你是如何进行前端性能优化的？有哪些具体的方法？",
                    "请介绍你在响应式设计方面的经验。",
                    "你如何处理前端的状态管理和数据流？"
                ])
            elif position_type == 'algo':
                questions.extend([
                    "请介绍你最熟悉的机器学习算法和应用场景。",
                    "你在处理大规模数据时有哪些经验？",
                    "请描述一个你参与的算法优化项目。",
                    "你如何评估和选择合适的算法模型？"
                ])
            elif position_type == 'pm':
                questions.extend([
                    "请介绍你的产品管理经验和方法论。",
                    "你是如何进行用户需求分析和产品规划的？",
                    "请描述一个你主导的产品项目从0到1的过程。",
                    "你如何平衡技术实现和用户需求？"
                ])
            else:
                # 通用技术问题
                questions.extend([
                    "请介绍你最近参与的一个技术项目。",
                    "你在团队协作中通常担任什么角色？",
                    "遇到技术难题时，你的解决思路是什么？",
                    "你如何保持技术学习和自我提升？"
                ])
            
            # 根据技能信息添加针对性问题
            if skills and skills != "未提供":
                if any(skill in skills.lower() for skill in ['java', 'spring']):
                    questions.append("请介绍你在Java/Spring开发中的经验和遇到的挑战。")
                if any(skill in skills.lower() for skill in ['python', 'django']):
                    questions.append("请分享你在Python/Django开发中的实践经验。")
                if any(skill in skills.lower() for skill in ['react', 'vue', 'javascript']):
                    questions.append("请介绍你在前端框架开发中的经验和最佳实践。")
            
            # 根据项目经验添加问题
            if projects and projects != "未提供":
                questions.append("请详细介绍你参与过的最有挑战性的项目。")
                if "电商" in projects or "支付" in projects:
                    questions.append("在电商或支付项目中，你是如何保证系统的稳定性和安全性的？")
            
            # 结尾问题
            questions.extend([
                "你对我们公司和这个岗位有什么了解？",
                "你对未来的职业规划是什么？"
            ])
            
            # 返回前8个问题
            return questions[:8]
            
        except Exception as e:
            print(f"[调试] 基于规则生成问题失败: {e}")
            return []
    
    def _search_interview_posts(self, position: str, position_type: str, skills: str, limit: int = 10) -> list:
        """从帖子中搜索相关面经"""
        try:
            from posts.models import Post, Tag
            from django.db.models import Q
            
            # 构建标签查询条件
            tag_conditions = Q()
            
            # 添加岗位类型标签
            position_type_keywords = {
                'backend': ['后端', 'java', 'python', 'go', '服务端'],
                'frontend': ['前端', 'web', 'javascript', 'vue', 'react'],
                'algo': ['算法', '机器学习', '深度学习', 'AI'],
                'data': ['数据', '分析师', '数据挖掘'],
                'pm': ['产品经理', '产品', 'PM'],
                'qa': ['测试', 'QA', '质量']
            }
            
            if position_type in position_type_keywords:
                for keyword in position_type_keywords[position_type]:
                    tag_conditions |= Q(tags__name__icontains=keyword)
            
            # 添加职位标签
            if position:
                tag_conditions |= Q(tags__name__icontains=position)
            
            # 添加技能标签
            if skills:
                for skill in skills.split('，'):  # 处理中文逗号分隔的技能列表
                    skill = skill.strip()
                    if skill:
                        tag_conditions |= Q(tags__name__icontains=skill)
            
            # 搜索帖子
            posts = Post.objects.filter(
                tag_conditions,
                tags__tag_type__in=['company', 'position', 'skill']  # 只搜索公司、岗位、技能相关的标签
            ).distinct()
            
            # 构建内容搜索条件
            content_conditions = Q()
            
            # 添加面试相关关键词
            interview_keywords = ['面试', '面经', '八股文', '技术问题', '考察', '考点']
            for keyword in interview_keywords:
                content_conditions |= Q(title__icontains=keyword) | Q(content__icontains=keyword)
            
            posts = posts.filter(content_conditions)
            
            # 按相关度排序（标签匹配数量）并限制返回数量
            posts = posts.order_by('-likes_count', '-created_at')[:limit]
            
            # 处理结果
            results = []
            for post in posts:
                # 获取公司和岗位标签
                company_tags = [tag.name for tag in post.tags.filter(tag_type='company')]
                position_tags = [tag.name for tag in post.tags.filter(tag_type='position')]
                
                results.append({
                    'title': post.title,
                    'content': post.content,
                    'company': company_tags[0] if company_tags else '',
                    'position': position_tags[0] if position_tags else '',
                    'likes': post.likes_count
                })
            
            return results
            
        except Exception as e:
            print(f"搜索面经帖子时出错: {e}")
            return []
    
    def _format_interview_posts(self, posts: list) -> str:
        """格式化面经帖子内容"""
        if not posts:
            return "暂无相关面经"
            
        formatted = []
        for post in posts:
            # 提取标题和内容中的问题
            content = post['content']
            questions = self._extract_questions(content)
            
            # 添加帖子来源信息
            source = []
            if post['company']:
                source.append(post['company'])
            if post['position']:
                source.append(post['position'])
            source_str = f"【{'·'.join(source)}】" if source else ""
            
            # 格式化问题
            if questions:
                formatted.extend([f"{source_str}{q}" for q in questions])
            
        return "\n".join(formatted)
    
    def _extract_questions(self, text: str) -> list:
        """从文本中提取问题"""
        import re  # 在方法中导入re模块
        questions = []
        
        # 常见的问题标记模式
        patterns = [
            r'问：(.*?)(?=\n|$)',
            r'Q：(.*?)(?=\n|$)',
            r'Q:(.*?)(?=\n|$)',
            r'\d+[.、](.*?)(?=\n|$)',
            r'面试官：(.*?)(?=\n|$)',
            r'面试问题：(.*?)(?=\n|$)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.MULTILINE)
            for match in matches:
                question = match.group(1).strip()
                if question and len(question) > 5:  # 过滤太短的问题
                    questions.append(question)
        
        # 如果没有找到明确的问题格式，尝试按段落拆分并识别问题语句
        if not questions:
            paragraphs = text.split('\n')
            for p in paragraphs:
                p = p.strip()
                if p and ('?' in p or '？' in p) and len(p) > 10:
                    questions.append(p)
        
        return questions[:10]  # 限制返回的问题数量
    
    def search_relevant_questions(self, position_type, resume, limit=5):
        """
        根据岗位和简历信息搜索相关面试问题
        """
        try:
            # 如果没有简历，返回默认问题
            if not resume:
                return [
                    '请简单自我介绍一下。',
                    '你为什么选择我们公司？',
                    '请介绍一下你最近的一个项目。',
                    '你遇到过最大的技术难题是什么？',
                    '你对未来的职业规划是什么？'
                ]
            
            # 根据岗位类型获取相关问题
            questions = []
            if position_type == 'backend':
                questions.extend([
                    '请介绍一下你使用过的后端框架和技术栈。',
                    '你是如何处理高并发场景的？',
                    '请介绍一下你设计过的数据库结构。'
                ])
            elif position_type == 'frontend':
                questions.extend([
                    '请介绍一下你熟悉的前端框架。',
                    '你是如何优化前端性能的？',
                    '请介绍一下你做过的响应式设计。'
                ])
            elif position_type == 'algo':
                questions.extend([
                    '请介绍一下你最熟悉的算法。',
                    '你是如何处理大规模数据的？',
                    '请介绍一下你在机器学习方面的经验。'
                ])
            
            # 添加基于简历的个性化问题
            if hasattr(resume, 'work_experiences'):
                for exp in resume.work_experiences.all()[:2]:
                    questions.append(f'请详细介绍一下你在{exp.company_name}的工作经历。')
            
            if hasattr(resume, 'project_experiences'):
                for proj in resume.project_experiences.all()[:2]:
                    questions.append(f'请介绍一下{proj.project_name}项目的具体情况。')
            
            # 确保问题数量不超过限制
            questions = questions[:limit]
            
            # 如果问题不够，补充通用问题
            while len(questions) < limit:
                questions.append('你对未来的职业规划是什么？')
            
            return questions
            
        except Exception as e:
            print(f"搜索相关问题出错: {e}")
            return [
                '请简单自我介绍一下。',
                '你为什么选择我们公司？',
                '请介绍一下你最近的一个项目。',
                '你遇到过最大的技术难题是什么？',
                '你对未来的职业规划是什么？'
            ]
    
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