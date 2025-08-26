import json
import websocket
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from email.utils import formatdate
import hashlib
import base64
import hmac
from urllib.parse import urlencode
import logging
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from users.models import Resume
import redis


logger = logging.getLogger(__name__)


class ResumeOptimizeConsumer(AsyncWebsocketConsumer):
    """基于简历的优化建议（讯飞流式）"""

    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
            return
        await self.accept()
        self.user = self.scope["user"]
        logger.info(f"ResumeOptimize WS 已连接 - 用户: {self.user.username}")

    async def disconnect(self, close_code):
        logger.info(f"ResumeOptimize WS 断开: {close_code} - 用户: {self.user.username if hasattr(self, 'user') else 'Unknown'}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            resume_id = data.get('resume_id')
            if not resume_id:
                await self.send(text_data=json.dumps({'type': 'error', 'text': '缺少resume_id'}))
                return

            # 查询简历及其关联信息（放在线程中，避免在异步上下文调用同步ORM）
            resume = await self._get_resume_with_relations(resume_id)

            # 组装简历信息字符串（在线程中构建，避免潜在ORM访问）
            resume_info = await self._build_resume_text(resume)

            # 用户目标岗位信息（如有）
            target_lines = []
            if getattr(self.user, 'target_position_name', None):
                target_lines.append(f"目标岗位：{self.user.target_position_name}")
            if getattr(self.user, 'target_company_name', None):
                target_lines.append(f"目标公司：{self.user.target_company_name}")
            if getattr(self.user, 'target_salary_min', None) is not None and getattr(self.user, 'target_salary_max', None) is not None:
                target_lines.append(f"期望薪资：{self.user.target_salary_min}-{self.user.target_salary_max}k")
            target_info = ("\n" + "\n".join(target_lines)) if target_lines else ""

            # 第一阶段提示词：生成文字描述
            first_prompt = f"""
你是一名资深的中文简历优化顾问。请基于如下候选人简历内容，提出详细的优化建议和修改思路。

候选人简历：
{resume_info}
{target_info}

请以中文详细说明：
1. 当前简历的主要问题分析
2. 针对每个部分（基本信息、工作经历、项目经历、教育经历）的具体优化建议
3. 如何让描述更具体化、量化，突出成果和影响
4. 如何提高与目标岗位的匹配度
5. 整体的优化策略和思路

请用清晰的结构和具体的例子来说明，让用户能够理解为什么要这样修改。
""".strip()

            def create_url():
                date = formatdate(timeval=None, localtime=False, usegmt=True)
                signature_origin = f"host: spark-api.xf-yun.com\ndate: {date}\nGET /v3.1/chat HTTP/1.1"
                signature_sha = hmac.new(
                    settings.XUNFEI_API_SECRET.encode('utf-8'),
                    signature_origin.encode('utf-8'),
                    digestmod=hashlib.sha256
                ).digest()
                signature_sha_base64 = base64.b64encode(signature_sha).decode()
                authorization_origin = f"api_key=\"{settings.XUNFEI_API_KEY}\", algorithm=\"hmac-sha256\", headers=\"host date request-line\", signature=\"{signature_sha_base64}\""
                authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode()
                params = {
                    "authorization": authorization,
                    "date": date,
                    "host": "spark-api.xf-yun.com"
                }
                url = f"wss://spark-api.xf-yun.com/v3.1/chat?{urlencode(params)}"
                return url, date

            url, date = create_url()
            headers = [
                f"Host: spark-api.xf-yun.com",
                f"Date: {date}",
            ]
            ws = websocket.create_connection(url, header=headers, timeout=10)

            # 这个变量在第一阶段已经不需要了，删除

            # 第一阶段：生成文字描述
            await self.send(text_data=json.dumps({'type': 'start', 'stage': 'description'}))
            
            first_request_data = {
                "header": {
                    "app_id": settings.XUNFEI_APP_ID,
                    "uid": str(self.user.id)
                },
                "parameter": {
                    "chat": {
                        "domain": "generalv3",
                        "temperature": 0.5,
                        "max_tokens": 2048
                    }
                },
                "payload": {
                    "message": {
                        "text": [
                            {"role": "user", "content": first_prompt}
                        ]
                    }
                }
            }
            
            ws.send(json.dumps(first_request_data))
            
            try:
                text_description = ""
                
                # 第一阶段：接收文字描述
                while True:
                    response = ws.recv()
                    response_data = json.loads(response)
                    if response_data['header']['code'] != 0:
                        error_msg = response_data.get('payload', {}).get('text', '请求失败')
                        await self.send(text_data=json.dumps({'type': 'error', 'text': error_msg}))
                        return
                    if 'payload' in response_data and 'choices' in response_data['payload']:
                        text = response_data['payload']['choices']['text'][0]['content']
                        if text:
                            await self.send(text_data=json.dumps({'type': 'delta', 'text': text}))
                            text_description += text
                    if response_data['header']['status'] == 2:
                        break
                
                ws.close()
                
                # 第二阶段：生成结构化JSON
                await self.send(text_data=json.dumps({'type': 'stage_transition', 'text': '正在生成结构化建议...'}))
                
                # 第二阶段提示词
                second_prompt = f"""
基于以下优化建议文字描述，请生成对应的结构化JSON数据用于更新简历。

原始简历信息：
{resume_info}

优化建议描述：
{text_description}

请严格按照以下JSON格式返回，只返回JSON，不要其他内容：

{{
  "basic_info": {{
    "name": "优化后的姓名（如果需要改进）",
    "expected_position": "优化后的期望职位描述"
  }},
  "work_experiences": [
    {{
      "id": 工作经历ID,
      "company_name": "优化后的公司名称",
      "position": "优化后的职位名称", 
      "work_content": "优化后的工作内容描述，要具体、量化"
    }}
  ],
  "project_experiences": [
    {{
      "id": 项目经历ID,
      "project_name": "优化后的项目名称",
      "project_role": "优化后的项目角色",
      "project_content": "优化后的项目内容描述，要具体、量化"
    }}
  ],
  "education_experiences": [
    {{
      "id": 教育经历ID,
      "school_experience": "优化后的在校经历描述"
    }}
  ]
}}

要求：保持原有ID不变，只优化需要改进的字段。
"""
                
                # 创建第二个WebSocket连接
                url2, date2 = create_url()
                headers2 = [
                    f"Host: spark-api.xf-yun.com",
                    f"Date: {date2}",
                ]
                ws2 = websocket.create_connection(url2, header=headers2, timeout=10)
                
                second_request_data = {
                    "header": {
                        "app_id": settings.XUNFEI_APP_ID,
                        "uid": str(self.user.id)
                    },
                    "parameter": {
                        "chat": {
                            "domain": "generalv3",
                            "temperature": 0.3,  # 降低温度以获得更精确的JSON
                            "max_tokens": 2048
                        }
                    },
                    "payload": {
                        "message": {
                            "text": [
                                {"role": "user", "content": second_prompt}
                            ]
                        }
                    }
                }
                
                ws2.send(json.dumps(second_request_data))
                
                json_response = ""
                
                # 第二阶段：接收结构化JSON（不发送给前端）
                while True:
                    response = ws2.recv()
                    response_data = json.loads(response)
                    if response_data['header']['code'] != 0:
                        logger.error(f"第二阶段API请求失败: {response_data}")
                        break
                    if 'payload' in response_data and 'choices' in response_data['payload']:
                        text = response_data['payload']['choices']['text'][0]['content']
                        if text:
                            json_response += text
                    if response_data['header']['status'] == 2:
                        break
                
                ws2.close()
                
                # 只缓存结构化JSON数据
                try:
                    await self._cache_suggestion(str(self.user.id), str(resume.id), json_response)
                except Exception as e:
                    logger.error(f"缓存优化建议失败: {e}")
                
                await self.send(text_data=json.dumps({'type': 'end'}))
                
            except Exception as e:
                logger.error(f"处理阶段时出错: {e}")
                try:
                    if 'ws' in locals():
                        ws.close()
                    if 'ws2' in locals():
                        ws2.close()
                except Exception:
                    pass
                raise e

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'type': 'error', 'text': '无效的JSON格式'}))
        except Exception as e:
            logger.error(f"ResumeOptimize 处理出错: {str(e)}")
            await self.send(text_data=json.dumps({'type': 'error', 'text': f'处理出错: {str(e)}'}))

    @database_sync_to_async
    def _get_resume_with_relations(self, resume_id):
        # 只允许访问自己的简历
        resume = Resume.objects.select_related('user').prefetch_related(
            'work_experiences', 'project_experiences', 'education_experiences', 'custom_sections'
        ).get(id=resume_id, user=self.user)
        return resume

    @database_sync_to_async
    def _build_resume_text(self, resume):
        try:
            from knowledge_base.services import XunfeiSparkService
            kb_svc = XunfeiSparkService()
            return kb_svc._build_resume_info(resume)
        except Exception:
            parts = [
                f"姓名：{resume.name}",
                f"年龄：{resume.age}",
                f"学历：{resume.education_level}",
                f"期望职位：{resume.expected_position}",
            ]
            if resume.work_experiences.exists():
                parts.append("\n工作经历：")
                for exp in resume.work_experiences.all():
                    parts.append(f"- {exp.company_name} {exp.position} ({exp.start_date} - {exp.end_date or '至今'})")
                    parts.append(f"  工作内容：{exp.work_content}")
            if resume.project_experiences.exists():
                parts.append("\n项目经历：")
                for proj in resume.project_experiences.all():
                    parts.append(f"- {proj.project_name} 角色：{proj.project_role}")
                    parts.append(f"  项目内容：{proj.project_content}")
            if resume.education_experiences.exists():
                parts.append("\n教育经历：")
                for edu in resume.education_experiences.all():
                    parts.append(f"- {edu.school_name} {edu.major} {edu.education_level}")
            return "\n".join(parts)


    @sync_to_async
    def _cache_suggestion(self, user_id: str, resume_id: str, json_response: str, ttl_seconds: int = 86400):
        """将结构化JSON建议写入Redis"""
        try:
            client = redis.from_url(getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0'))
            
            # 尝试提取并存储结构化JSON
            structured_data = self._extract_json_from_text(json_response)
            if structured_data:
                json_key = f"resume:opt_suggestion:json:{user_id}:{resume_id}"
                client.setex(json_key, ttl_seconds, json.dumps(structured_data, ensure_ascii=False))
                
        except Exception as e:
            raise e
    
    def _extract_json_from_text(self, text: str):
        """从AI返回的文本中提取JSON结构"""
        try:
            import re
            # 查找JSON块（以{开始，以}结束）
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, text, re.DOTALL)
            
            for match in matches:
                try:
                    # 尝试解析JSON
                    parsed = json.loads(match)
                    # 验证是否包含预期的字段
                    if isinstance(parsed, dict) and any(key in parsed for key in ['basic_info', 'work_experiences', 'project_experiences']):
                        return parsed
                except json.JSONDecodeError:
                    continue
            
            return None
        except Exception as e:
            logger.error(f"提取JSON时出错: {e}")
            return None


