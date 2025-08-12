import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import VideoStream, WebRTCConnection  # type: ignore
from .services import webrtc_service
from interviews.services import XunfeiRTASRClient
from interviews.models import InterviewAnswer
import uuid
import base64
from knowledge_base.services import KnowledgeBaseService
from users.models import Resume
import threading
import cv2
import numpy as np
import torch
from torchvision import transforms
from PIL import Image
import sys
sys.path.append('./pytorch_model')
from ultralytics import YOLO
import requests
from django.conf import settings
import os
import datetime
import wave
import ffmpeg
import numpy as np
from requests_toolbelt.multipart.encoder import MultipartEncoder
from openai import OpenAI
import traceback
import re
from concurrent.futures import ThreadPoolExecutor
from django.conf import settings

User = get_user_model()
logger = logging.getLogger(__name__)

class WebRTCConsumer(AsyncWebsocketConsumer):
    """WebRTC WebSocket消费者"""
    PHASE_INTRO = 'intro'
    PHASE_QUESTION = 'question'
    PHASE_CODE = 'code'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.session_id = None
        self.peer_id = None
        self.video_stream = None
        self.connection = None
        self.interview_id = None  # 面试ID
        self.resume_id = None     # 简历ID
        self.rtasr_client = None  # 讯飞RTASR实例
        self.question_queue = []  # 面试问题队列
        self.phase = self.PHASE_INTRO
        self.last_asr_text = ''
        self._ws_loop = None
        self.current_question = None
        self.current_question_knowledge_points = []  # 当前问题的知识点
        self.current_answer_sentences = []
        self.current_answer_final = []
        self.current_answer_start_time = None
        self.current_question_idx = 0 # 新增：记录当前问题的序号
        self.audio_buffer = []
        self.video_frame_buffer = []
        self.coding_problems = []  # 代码题列表
        self.current_coding_problem = None  # 当前代码题
    
    async def connect(self):
        print("[WebRTCConsumer] connect called")
        await self.accept()
        print("[WebRTCConsumer] connect, self.scope['user']:", self.scope.get('user', None))
        self.user = await self.get_user() if hasattr(self, 'get_user') else None
        print("[WebRTCConsumer] connect, self.user:", self.user)
        try:
            self.session_id = str(uuid.uuid4())
            loop = asyncio.get_event_loop()
            self._ws_loop = loop
            def on_rtasr_result(text):
                # print('[RTASR回调]', text)
                asyncio.run_coroutine_threadsafe(self.handle_asr_result(text), loop)
            def start_rtasr():
                retry_count = 0
                max_retries = 3
                while retry_count < max_retries:
                    try:
                        print(f"[WebRTCConsumer] RTASR ws connecting... (尝试 {retry_count + 1}/{max_retries})")
                        self.rtasr_client = XunfeiRTASRClient(app_id=settings.XUNFEI_APP_ID, api_key=settings.XUNFEI_RTASR_API_KEY, on_result=on_rtasr_result)
                        self.rtasr_client.connect()
                        print("[WebRTCConsumer] RTASR ws connected")
                        # 连接成功，发送通知
                        asyncio.run_coroutine_threadsafe(
                            self.send(text_data=json.dumps({'type': 'asr_status', 'status': 'connected', 'message': '语音识别已启用'})), loop)
                        return
                    except Exception as e:
                        retry_count += 1
                        print(f"[WebRTCConsumer] RTASR ws connect error (尝试 {retry_count}): {e}")
                        if retry_count < max_retries:
                            import time
                            time.sleep(2)  # 等待2秒后重试
                        else:
                            # 所有重试都失败，发送友好的错误消息
                            error_msg = "语音识别服务暂不可用，但不影响面试进行。您可以继续面试，答案将通过其他方式记录。"
                            asyncio.run_coroutine_threadsafe(
                                self.send(text_data=json.dumps({'type': 'asr_status', 'status': 'failed', 'message': error_msg})), loop)
            threading.Thread(target=start_rtasr, daemon=True).start()
            
            # 注意：问题队列的初始化将在handle_create_stream中进行，因为此时还没有interview_id
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'session_id': self.session_id,
                'text': 'WebRTC连接已建立'
            }))
        except Exception as e:
            print(f"[WebRTCConsumer] connect error: {e}")
            await self.send(text_data=json.dumps({'type': 'error', 'text': f'初始化失败: {e}'}))
    
    async def disconnect(self, close_code):
        print(f"[WebRTCConsumer] disconnect called, code={close_code}")
        """断开WebSocket连接"""
        try:
            if self.rtasr_client:
                print("[WebRTCConsumer] closing RTASR ws...")
                try:
                    self.rtasr_client.close()
                    print("[WebRTCConsumer] RTASR ws closed")
                except Exception as e:
                    print(f"[WebRTCConsumer] RTASR ws close error: {e}")
            if self.connection:
                await self.update_connection_state('disconnected')
            if self.video_stream:
                await self.deactivate_video_stream()
            logger.info(f"WebRTC连接已断开: {self.user.username if self.user else 'Unknown'} - {close_code}")
        except Exception as e:
            logger.error(f"断开连接时出错: {str(e)}")
            print(f"[WebRTCConsumer] disconnect error: {e}")
    
    async def receive(self, text_data):
        """接收WebSocket消息"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'create_stream':
                await self.handle_create_stream(data)
            elif message_type == 'join_stream':
                await self.handle_join_stream(data)
            elif message_type == 'offer':
                await self.handle_offer(data)
            elif message_type == 'answer':
                await self.handle_answer(data)
            elif message_type == 'ice_candidate':
                await self.handle_ice_candidate(data)
            elif message_type == 'video_frame':
                await self.handle_video_frame(data)
            elif message_type == 'audio_frame':
                await self.handle_audio_frame(data)
            elif message_type == 'request_next_question':
                await self.handle_request_next_question()
            elif message_type == 'answer_completed':
                await self.handle_answer_completed(data)
            elif message_type == 'manual_answer_text':
                await self.handle_manual_answer_text(data)
            elif message_type == 'request_next_coding_problem':
                await self.handle_request_next_coding_problem()
            elif message_type == 'submit_coding_answer':
                await self.handle_submit_coding_answer(data)
            elif message_type == 'disconnect':
                await self.handle_disconnect(data)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'text': f'未知的消息类型: {message_type}'
                }))
                
        except json.JSONDecodeError:
            print("[WebRTCConsumer] receive JSON decode error")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': '无效的JSON格式'
            }))
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}")
            print(f"[WebRTCConsumer] receive error: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': f'处理消息时出错: {str(e)}'
            }))
    
    async def handle_create_stream(self, data):
        """处理创建视频流请求"""
        try:
            title = data.get('title', '未命名流')
            description = data.get('description', '')
            self.interview_id = data.get('interview_id')  # 获取面试ID
            
            if not self.interview_id:
                raise ValueError("缺少面试ID")
            
            # 通过面试ID获取简历ID
            interview = await self.get_interview_by_id(self.interview_id)
            if not interview:
                raise ValueError("面试记录不存在")
            if not interview.resume:
                raise ValueError("该面试没有关联简历")
            
            self.resume_id = interview.resume.id
            
            print("[调试] handle_create_stream - interview_id:", self.interview_id, "resume_id:", self.resume_id)
            
            # 创建视频流记录
            self.video_stream = await self.create_video_stream(title, description)
            if not self.video_stream:
                raise ValueError("创建视频流失败")
            
            # 创建连接记录
            self.connection = await self.create_connection()
            if not self.connection:
                raise ValueError("创建连接记录失败")
            
            # 加入视频流组
            await self.channel_layer.group_add(
                f"stream_{self.video_stream.id}",
                self.channel_name
            )
            
            # 初始化问题队列（现在有了interview_id和resume_id）
            self.question_queue = await self.init_question_queue()
            
            # 启动异步知识点生成任务
            if hasattr(self, '_pending_knowledge_points_data'):
                asyncio.create_task(self._async_generate_knowledge_points(
                    self._pending_knowledge_points_data['questions'],
                    self._pending_knowledge_points_data['position_type'],
                    self._pending_knowledge_points_data['kb_service']
                ))
                # 清理临时数据
                delattr(self, '_pending_knowledge_points_data')
            
            # 返回成功响应
            await self.send(text_data=json.dumps({
                'type': 'stream_created',
                'stream_id': str(self.video_stream.id),
                'peer_id': self.peer_id
            }))
            
            # 发送面试官开场白
            await self.send(text_data=json.dumps({
                'type': 'interview_message',
                'phase': self.PHASE_INTRO,
                'text': '请开始自我介绍吧'
            }))
            self.phase = self.PHASE_INTRO
            
        except Exception as e:
            print(f"创建视频流失败: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': f'创建视频流失败: {str(e)}'
            }))
            
    async def handle_join_stream(self, data):
        """处理加入视频流请求"""
        try:
            stream_id = data.get('stream_id')
            if not stream_id:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'text': '缺少流ID'
                }))
                return
            
            # 获取视频流
            self.video_stream = await self.get_video_stream(stream_id)
            if not self.video_stream:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'text': '视频流不存在'
                }))
                return
            
            # 创建连接记录
            self.connection = await self.create_connection()
            
            await self.send(text_data=json.dumps({
                'type': 'stream_joined',
                'stream_id': str(self.video_stream.id),
                'title': self.video_stream.title,
                'text': '成功加入视频流'
            }))
            
        except Exception as e:
            logger.error(f"加入视频流失败: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': f'加入视频流失败: {str(e)}'
            }))
    
    async def handle_offer(self, data):
        """处理WebRTC offer"""
        try:
            offer = data.get('offer')
            if not offer:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'text': '缺少offer数据'
                }))
                return
            
            # 更新连接状态
            await self.update_connection_state('connecting')
            
            # 广播offer给其他连接
            await self.channel_layer.group_send(
                f"stream_{self.video_stream.id}",
                {
                    'type': 'broadcast_offer',
                    'offer': offer,
                    'peer_id': self.peer_id,
                    'exclude': self.channel_name
                }
            )
            
        except Exception as e:
            logger.error(f"处理offer失败: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': f'处理offer失败: {str(e)}'
            }))
    
    async def handle_answer(self, data):
        """处理WebRTC answer"""
        try:
            answer = data.get('answer')
            target_peer = data.get('target_peer')
            
            if not answer or not target_peer:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'text': '缺少answer或target_peer数据'
                }))
                return
            
            # 发送answer给目标peer
            await self.channel_layer.send(
                target_peer,
                {
                    'type': 'send_answer',
                    'answer': answer,
                    'peer_id': self.peer_id
                }
            )
            
        except Exception as e:
            logger.error(f"处理answer失败: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': f'处理answer失败: {str(e)}'
            }))
    
    async def handle_ice_candidate(self, data):
        """处理ICE候选"""
        try:
            candidate = data.get('candidate')
            target_peer = data.get('target_peer')
            
            if not candidate or not target_peer:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'text': '缺少candidate或target_peer数据'
                }))
                return
            
            # 发送ICE候选给目标peer
            await self.channel_layer.send(
                target_peer,
                {
                    'type': 'send_ice_candidate',
                    'candidate': candidate,
                    'peer_id': self.peer_id
                }
            )
            
        except Exception as e:
            logger.error(f"处理ICE候选失败: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': f'处理ICE候选失败: {str(e)}'
            }))
    
    async def handle_video_frame(self, data):
        """处理视频帧数据，集成YOLOv11和原生PyTorch情绪识别"""
        # 检查video_stream是否已初始化
        if not hasattr(self, 'video_stream') or self.video_stream is None:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': '未初始化视频流，请先创建或加入视频流'
            }))
            return
        try:
            frame_data = data.get('frame_data')
            frame_type = data.get('frame_type', 'keyframe')
            
            # 调试信息
            #print(f"[调试] 收到视频帧 - frame_type: {frame_type}, frame_data长度: {len(frame_data) if frame_data else 0}")
            
            if not frame_data:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'text': '缺少帧数据'
                }))
                return
            # 处理data:image/jpeg;base64,前缀，确保为纯base64字符串
            if isinstance(frame_data, str):
                if frame_data.startswith('data:image'):
                    frame_data = frame_data.split(',', 1)[-1]
                img_bytes = base64.b64decode(frame_data)
            elif isinstance(frame_data, bytes):
                img_bytes = base64.b64decode(frame_data)
            else:
                raise ValueError("frame_data类型错误，必须为str或bytes")
            np_arr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'text': '无法解码图像数据'
                }))
                return
            # 1. YOLOv11检测人数（只加载一次模型）
            if not hasattr(self, 'yolo_model'):
                self.yolo_model = YOLO('yolo11n.pt')
            results = self.yolo_model(img)
            persons = [b for b in results[0].boxes.data.cpu().numpy() if int(b[5]) == 0]
            if len(persons) > 1:
                await self.send(text_data=json.dumps({
                    'type': 'cheat_detected',
                    'text': '检测到多个人，疑似作弊！'
                }))
                return
            elif len(persons) == 1:
                pass  # 目前不做任何处理
            # 2. 原生PyTorch情绪识别
            # self.load_fer_model() # 删除VGG/FER2013相关代码
            # x1, y1, x2, y2 = map(int, persons[0][:4])
            # face_img = img[y1:y2, x1:x2]
            # if face_img.size == 0:
            #     print('未检测到有效人脸区域')
            # else:
            #     emotion_idx, emotion_name = self.predict_emotion(face_img)
            #     print(f'情绪类别: {emotion_name}（索引: {emotion_idx}）')
            # 保存视频帧
            await self.save_video_frame(img_bytes, frame_type)
            # 广播给其他观看者
            await self.channel_layer.group_send(
                f"stream_{self.video_stream.id}",
                {
                    'type': 'broadcast_video_frame',
                    'frame_data': frame_data,
                    'frame_type': frame_type,
                    'peer_id': self.peer_id,
                    'exclude': self.channel_name
                }
            )
            if frame_data:
                self.video_frame_buffer.append(frame_data)
                #print(f"[调试] 视频帧已添加到buffer，当前buffer长度: {len(self.video_frame_buffer)}")
        except Exception as e:
            print(f"[调试] 处理视频帧失败: {str(e)}")
            logger.error(f"处理视频帧失败: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': f'处理视频帧失败: {str(e)}'
            }))
    
    async def handle_audio_frame(self, data):
        """处理音频帧数据，转发到讯飞ASR，推送转写结果"""

        try:
            audio_data = data.get('audio_data')  # base64字符串
            is_end = data.get('end', False)
            
            # 调试信息
            #print(f"[调试] 收到音频帧 - is_end: {is_end}, audio_data长度: {len(audio_data) if audio_data else 0}")
            
            if is_end:
                if self.rtasr_client and self.rtasr_client.connected and not self.rtasr_client.closed:
                    self.rtasr_client.send_audio(b'', is_last=True)
                return
            if not audio_data:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'text': '缺少音频数据'
                }))
                return
            audio_bytes = base64.b64decode(audio_data)
            if self.rtasr_client and self.rtasr_client.connected and not self.rtasr_client.closed:
                self.rtasr_client.send_audio(audio_bytes)
            else:
                # RTASR不可用时，仍然保存音频数据，但不进行实时转写
                # 这样音频可以用于后续的离线分析
                pass
            if audio_data:
                self.audio_buffer.append(audio_data)
                # print(f"[调试] 音频数据已添加到buffer，当前buffer长度: {len(self.audio_buffer)}")
        except Exception as e:
            print(f"[调试] 音频帧处理出错: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': f'音频帧处理出错: {str(e)}'
            }))
    
    async def handle_request_next_question(self):
        """处理前端请求下一个面试问题"""
        if self.question_queue:
            question_data = self.question_queue.pop(0)
            # 适配新的数据结构
            if isinstance(question_data, dict):
                question_text = question_data['question']
                self.current_question_knowledge_points = question_data['knowledge_points']
            else:
                question_text = question_data
                self.current_question_knowledge_points = ["通用技能", "专业能力"]
            
            await self.send(text_data=json.dumps({
                'type': 'next_question',
                'question': question_text
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'next_question',
                'question': '已无更多问题'
            }))
    
    async def handle_answer_completed(self, data):
        """处理用户手动确认答案完成"""
        print(f"[调试] handle_answer_completed called, phase: {self.phase}")
        
        if self.phase == self.PHASE_INTRO:
            # 自我介绍阶段结束
            await self.finish_intro()
        elif self.phase == self.PHASE_QUESTION:
            # 问答阶段，处理当前问题的答案
            # 如果有手动输入的答案文本，使用它；否则使用实时收集的文本
            manual_text = data.get('answer_text', '')
            if manual_text:
                self.current_answer_final = [manual_text]
            elif self.current_answer_sentences:
                self.current_answer_final = self.current_answer_sentences
            else:
                # 如果都没有，提供一个默认的答案记录
                self.current_answer_final = ["[用户已完成回答，但未收集到文本内容]"]
            
            # 保存答案并进入下一题
            await self.save_current_answer()
            await self.next_question()
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': f'当前阶段({self.phase})不支持此操作'
            }))
    
    async def handle_manual_answer_text(self, data):
        """处理用户手动输入的答案文本"""
        answer_text = data.get('text', '')
        if answer_text:
            print(f"[调试] 收到手动输入答案: {answer_text}")
            # 添加到当前答案句子列表中
            self.current_answer_sentences.append(answer_text)
            
            # 发送确认消息
            await self.send(text_data=json.dumps({
                'type': 'manual_answer_received',
                'text': '答案文本已收到'
            }))

    @database_sync_to_async
    def init_question_queue(self):
        """初始化面试问题队列 - 异步生成知识点版本"""
        import re  # 在方法内部重新导入re模块，避免装饰器作用域问题
        print(f"[调试] init_question_queue - interview_id: {self.interview_id} resume_id: {self.resume_id}")
        
        if not self.interview_id or not self.resume_id:
            print("[调试] init_question_queue - 缺少interview_id或resume_id")
            return self._get_default_questions_with_knowledge_points()
            
        try:
            from interviews.models import Interview
            from users.models import Resume
            from knowledge_base.models import JobPosition
            from knowledge_base.services import KnowledgeBaseService
            
            # 获取面试和简历信息
            interview = Interview.objects.select_related('resume').get(id=self.interview_id)
            resume = Resume.objects.get(id=self.resume_id)
            
            # 获取岗位信息
            position_type = interview.position_type
            position_name = interview.position_name
            
            # 使用知识库服务生成个性化问题
            kb_service = KnowledgeBaseService()
            
            # 获取教育背景
            education_info = "未提供"
            education_experiences = resume.education_experiences.all()
            if education_experiences.exists():
                education_list = []
                for edu in education_experiences:
                    edu_str = f"{edu.school_name}"
                    if edu.education_level:
                        edu_str += f"({edu.education_level})"
                    if edu.major:
                        edu_str += f"-{edu.major}"
                    education_list.append(edu_str)
                education_info = "；".join(education_list)
            
            # 获取工作经验
            work_info = "未提供"
            work_experiences = resume.work_experiences.all()
            if work_experiences.exists():
                work_list = []
                for work in work_experiences:
                    work_str = f"{work.company_name}"
                    if work.position:
                        work_str += f"-{work.position}"
                    work_list.append(work_str)
                work_info = "；".join(work_list)
            
            # 获取项目经验
            project_info = "未提供"
            project_experiences = resume.project_experiences.all()
            if project_experiences.exists():
                project_list = []
                for proj in project_experiences:
                    proj_str = f"{proj.project_name}"
                    if proj.project_role:
                        proj_str += f"({proj.project_role})"
                    project_list.append(proj_str)
                project_info = "；".join(project_list)
            
            # 获取技能特长（从期望职位和自定义部分中提取）
            skills_info = resume.expected_position if resume.expected_position else "未提供"
            custom_sections = resume.custom_sections.all()
            if custom_sections.exists():
                for section in custom_sections:
                    if "技能" in section.title or "能力" in section.title:
                        skills_info += f"；{section.content}"
            
            # 构建提示词
            prompt = f"""请根据以下信息生成一个技术面试问题列表：

1. 应聘岗位：{position_name}
2. 岗位类型：{position_type}
3. 应聘者教育背景：{education_info}
4. 技能特长：{skills_info}
5. 工作经验：{work_info}
6. 项目经验：{project_info}

要求：
1. 问题要针对该岗位的核心技能
2. 结合应聘者的背景设置合适的难度
3. 问题要由浅入深
4. 包含理论知识和实践经验的考察
5. 生成8-10个问题
6. 每个问题都要详细且专业

请按以下格式输出问题列表：
1. 问题1
2. 问题2
...
"""
            # 调用知识库服务生成问题
            try:
                questions = kb_service.generate_interview_questions(prompt)
                print(f"[调试] 知识库服务返回: {questions}")
            except Exception as kb_e:
                print(f"[调试] 调用知识库服务失败: {str(kb_e)}")
                questions = None
            
            if not questions:
                print("[调试] 生成问题失败，使用默认问题")
                return self._get_default_questions_with_knowledge_points()
                
            # 处理生成的问题，先使用默认知识点，然后异步生成
            processed_questions = []
            for q in questions.split('\n'):
                # 去除序号和空白
                q = re.sub(r'^\d+\.\s*', '', q.strip())
                if q:  # 忽略空行
                    # 先使用默认知识点，避免阻塞
                    default_knowledge_points = self._generate_rule_based_knowledge_points(q, position_type)
                    
                    processed_questions.append({
                        'question': q,
                        'knowledge_points': default_knowledge_points,
                        'knowledge_points_generated': False  # 标记知识点是否已生成
                    })
            
            print(f"[调试] 生成的问题列表（使用默认知识点）: {processed_questions}")
            
            # 保存岗位类型和知识库服务实例，供后续异步使用
            self._pending_knowledge_points_data = {
                'questions': processed_questions,
                'position_type': position_type,
                'kb_service': kb_service
            }
            
            return processed_questions
            
        except Exception as e:
            print(f"[调试] 初始化问题队列出错: {str(e)}")
            print(traceback.format_exc())
            try:
                return self._get_default_questions_with_knowledge_points()
            except Exception as default_e:
                print(f"[调试] 获取默认问题也失败: {str(default_e)}")
                # 返回最基础的问题列表
                return [
                    {
                        'question': "请简单介绍一下自己。",
                        'knowledge_points': ["自我介绍", "沟通能力"]
                    },
                    {
                        'question': "你有什么技术经验？",
                        'knowledge_points': ["技术能力", "工作经验"]
                    }
                ]

    async def _async_generate_knowledge_points(self, questions, position_type, kb_service):
        """异步生成知识点"""
        print(f"[调试] 开始异步生成知识点，共 {len(questions)} 个问题")
        
        for i, question_data in enumerate(questions):
            try:
                question = question_data['question']
                print(f"[调试] 异步生成知识点 {i+1}/{len(questions)}: {question[:50]}...")
                
                # 使用asyncio.to_thread包装同步的LLM调用
                knowledge_points = await asyncio.to_thread(
                    self._generate_knowledge_points_for_question, 
                    question, 
                    position_type, 
                    kb_service
                )
                
                if knowledge_points:
                    # 更新问题数据
                    question_data['knowledge_points'] = knowledge_points
                    question_data['knowledge_points_generated'] = True
                    print(f"[调试] 异步生成知识点成功: {knowledge_points}")
                else:
                    print(f"[调试] 异步生成知识点失败，保持默认知识点")
                    
            except Exception as e:
                print(f"[调试] 异步生成知识点出错: {str(e)}")
                # 保持默认知识点不变
        
        print(f"[调试] 异步知识点生成完成")

    def _get_default_questions(self):
        """获取默认问题列表"""
        return [
            "请简单介绍一下你的技术背景和主要技能。",
            "你在过去的项目中遇到过什么技术难题？是如何解决的？",
            "你对我们公司的技术栈了解多少？",
            "你认为自己的技术优势是什么？",
            "你平时是如何学习新技术的？",
            "你对未来的职业规划是什么？"
        ]
    
    def _get_default_questions_with_knowledge_points(self):
        """获取默认问题列表（包含知识点）"""
        return [
            {
                'question': "请简单介绍一下你的技术背景和主要技能。",
                'knowledge_points': ["自我表达能力", "技术栈掌握", "沟通能力", "职业素养"]
            },
            {
                'question': "你在过去的项目中遇到过什么技术难题？是如何解决的？",
                'knowledge_points': ["问题分析能力", "解决方案设计", "技术深度", "实践经验", "逻辑思维"]
            },
            {
                'question': "你对我们公司的技术栈了解多少？",
                'knowledge_points': ["技术栈理解", "学习能力", "行业认知", "技术前瞻性"]
            },
            {
                'question': "你认为自己的技术优势是什么？",
                'knowledge_points': ["自我认知", "技术特长", "专业能力", "核心竞争力"]
            },
            {
                'question': "你平时是如何学习新技术的？",
                'knowledge_points': ["学习方法", "自我提升", "技术热情", "持续学习"]
            },
            {
                'question': "你对未来的职业规划是什么？",
                'knowledge_points': ["职业规划", "目标设定", "自我发展", "战略思维"]
            }
        ]
    
    def _generate_knowledge_points_for_question(self, question, position_type, kb_service):
        """为问题生成知识点标注，优先使用LLM从知识点库选择"""
        try:
            # 首先尝试使用LLM从知识点库中选择
            knowledge_points = self._generate_llm_based_knowledge_points(question, position_type, kb_service)
            if knowledge_points:
                print(f"[调试] LLM生成知识点: {question[:50]}... -> {knowledge_points}")
                return knowledge_points
            
            # 如果LLM失败，使用规则生成
            knowledge_points = self._generate_rule_based_knowledge_points(question, position_type)
            print(f"[调试] 规则生成知识点: {question[:50]}... -> {knowledge_points}")
            return knowledge_points
            
        except Exception as e:
            print(f"[调试] 生成知识点失败: {str(e)}")
            # 返回默认知识点
            default_points_map = {
                'backend': ["后端开发", "系统设计", "数据库", "API设计"],
                'frontend': ["前端开发", "用户界面", "JavaScript", "框架应用"],
                'pm': ["产品设计", "用户需求", "项目管理", "数据分析"],
                'qa': ["测试方法", "质量保证", "自动化测试", "缺陷管理"],
                'algo': ["算法设计", "数据结构", "计算复杂度", "数学建模"],
                'data': ["数据分析", "机器学习", "数据挖掘", "统计学"]
            }
            return default_points_map.get(position_type, ["专业技能", "问题解决", "逻辑思维"])

    def _generate_rule_based_knowledge_points(self, question, position_type):
        """基于规则生成知识点，避免重复调用AI"""
        knowledge_points = []
        
        # 根据问题内容匹配知识点
        question_lower = question.lower()
        
        # 后端相关知识点
        if any(keyword in question_lower for keyword in ['数据库', 'mysql', 'redis', 'mongodb']):
            knowledge_points.extend(['数据库设计', 'SQL优化', '索引原理', '事务管理'])
        if any(keyword in question_lower for keyword in ['并发', '高并发', '多线程']):
            knowledge_points.extend(['并发编程', '线程安全', '锁机制', '性能优化'])
        if any(keyword in question_lower for keyword in ['微服务', '分布式', '架构']):
            knowledge_points.extend(['系统架构', '微服务设计', '分布式系统', '服务治理'])
        if any(keyword in question_lower for keyword in ['spring', 'java', '框架']):
            knowledge_points.extend(['Spring框架', 'Java核心', '设计模式', 'JVM调优'])
        
        # 前端相关知识点
        if any(keyword in question_lower for keyword in ['react', 'vue', '前端', 'javascript']):
            knowledge_points.extend(['前端框架', 'JavaScript', '组件化', '状态管理'])
        if any(keyword in question_lower for keyword in ['性能', '优化']):
            knowledge_points.extend(['性能优化', '代码质量', '最佳实践', '用户体验'])
        
        # 通用知识点
        if any(keyword in question_lower for keyword in ['项目', '经验', '实践']):
            knowledge_points.extend(['项目经验', '问题解决', '团队协作', '技术选型'])
        if any(keyword in question_lower for keyword in ['学习', '技术', '能力']):
            knowledge_points.extend(['学习能力', '技术栈', '自我提升', '专业素养'])
        
        # 去重并限制数量
        knowledge_points = list(set(knowledge_points))[:6]
        
        # 如果知识点不够，补充默认的
        if len(knowledge_points) < 3:
            default_points = {
                'backend': ['后端开发', '系统设计', '数据库'],
                'frontend': ['前端开发', '用户界面', 'JavaScript'],
                'algo': ['算法设计', '数据结构', '计算复杂度'],
                'pm': ['产品设计', '用户需求', '项目管理'],
                'qa': ['测试方法', '质量保证', '自动化测试'],
                'data': ['数据分析', '机器学习', '数据挖掘']
            }
            knowledge_points.extend(default_points.get(position_type, ['专业技能', '问题解决']))
            knowledge_points = list(set(knowledge_points))[:6]
        
        return knowledge_points

    def _generate_llm_based_knowledge_points(self, question, position_type, kb_service):
        """使用LLM从知识点库中选择知识点"""
        try:
            # 从数据库获取当前岗位类型的所有知识点
            from interviews.models import KnowledgePoint
            knowledge_points = KnowledgePoint.objects.filter(position_type=position_type).values_list('name', flat=True)
            knowledge_points_list = list(knowledge_points)
            
            if not knowledge_points_list:
                print(f"[调试] 未找到岗位类型 {position_type} 的知识点")
                return None
            
            # 构建提示词
            prompt = f"""请根据以下面试问题，从知识点库中选择1-3个最相关的知识点标签。

面试问题：{question}
岗位类型：{position_type}

可选的知识点标签：
{', '.join(knowledge_points_list)}

请严格按照以下格式返回，只返回知识点名称，用逗号分隔：
知识点1,知识点2,知识点3

注意：
1. 只能从上述知识点标签中选择
2. 选择1-3个最相关的知识点
3. 如果问题与任何知识点都不相关，返回"其他"
4. 严格按照格式返回，不要添加其他内容
"""
            
            # 调用LLM服务
            response = kb_service.spark_service._send_message(prompt)
            
            if not response:
                print(f"[调试] LLM调用失败，返回空响应")
                return None
            
            # 解析响应
            response = response.strip()
            if response == "其他" or not response:
                print(f"[调试] LLM返回'其他'或空响应")
                return None
            
            # 解析知识点
            selected_points = [point.strip() for point in response.split(',') if point.strip()]
            
            # 验证知识点是否在库中
            valid_points = []
            for point in selected_points:
                if point in knowledge_points_list:
                    valid_points.append(point)
                else:
                    print(f"[调试] 知识点 '{point}' 不在知识库中")
            
            if not valid_points:
                print(f"[调试] 没有有效的知识点被选择")
                return None
            
            print(f"[调试] LLM选择了知识点: {valid_points}")
            return valid_points[:3]  # 最多返回3个
            
        except Exception as e:
            print(f"[调试] LLM生成知识点失败: {str(e)}")
            return None

    async def handle_disconnect(self, data):
        """处理断开连接请求"""
        try:
            await self.update_connection_state('disconnected')
            await self.close(code=1000)
            
        except Exception as e:
            logger.error(f"断开连接失败: {str(e)}")
    
    @database_sync_to_async
    def get_resume_by_id(self, resume_id):
        """根据简历ID获取简历信息"""
        try:
            return Resume.objects.select_related('user').get(id=resume_id, user=self.user)
        except Resume.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_interview_by_id(self, interview_id):
        """获取面试记录"""
        from interviews.models import Interview
        try:
            return Interview.objects.select_related('user', 'resume').get(id=interview_id)
        except Interview.DoesNotExist:
            return None
    
    def sync_to_async(self, func):
        """将同步函数转换为异步函数"""
        import asyncio
        return asyncio.to_thread(func)


    async def handle_asr_result(self, text):
        """处理语音识别结果"""
        try:
            # 只处理中文文本
            if not text:
                return
            
            # 递归提取所有字符串中的中文
            def extract_chinese(obj):
                result = ''
                if isinstance(obj, str):
                    # 匹配所有中文
                    result += ''.join(char for char in obj if '\u4e00' <= char <= '\u9fff' or char in '，。！？、；：""''（）《》【】')
                elif isinstance(obj, list):
                    for item in obj:
                        result += extract_chinese(item)
                elif isinstance(obj, dict):
                    for key in obj:
                        result += extract_chinese(obj[key])
                return result
            
            # 如果text是JSON字符串，尝试提取所有中文
            try:
                obj = json.loads(text) if isinstance(text, str) else text
                text = extract_chinese(obj)
            except:
                pass
            
            # 更新当前回答
            if self.phase == self.PHASE_INTRO or self.phase == self.PHASE_QUESTION:
                if text:
                    # self.current_answer_sentences.append(text)
                    # 如果检测到说完了，保存答案
                    if "说完了" in text or "完毕" in text:
                        print("[调试] handle_asr_result 检测到说完了，准备保存答案")
                        await self.save_current_answer()
                        await self.next_question()
                    
            # 发送转写结果给前端
            await self.send(text_data=json.dumps({
                'type': 'asr_result',
                'text': text
            }))
            
        except Exception as e:
            print(f"[调试] handle_asr_result错误: {e}")

    async def finish_intro(self):
        # 如果还没有初始化问题队列，现在初始化
        if not self.question_queue:
            self.question_queue = await self.init_question_queue()
        
        self.phase = self.PHASE_QUESTION
        await self.send(text_data=json.dumps({
            'type': 'interview_message',
            'phase': self.PHASE_QUESTION,
            'text': '自我介绍结束，下面开始问问题。'
        }))
        await self.next_question()

    async def next_question(self):
        print(f"[DEBUG] next_question called, question_queue length: {len(self.question_queue) if self.question_queue else 0}")
        
        if self.question_queue:
            question_data = self.question_queue.pop(0)
            # 适配新的数据结构（可能是字典或字符串）
            if isinstance(question_data, dict):
                self.current_question = question_data['question']
                self.current_question_knowledge_points = question_data['knowledge_points']
            else:
                # 兼容旧格式
                self.current_question = question_data
                self.current_question_knowledge_points = ["通用技能", "专业能力"]
            
            self.current_answer_sentences = []
            self.current_answer_final = []
            from datetime import datetime
            self.current_answer_start_time = datetime.now()
            await self.send(text_data=json.dumps({
                'type': 'interview_message',
                'phase': self.PHASE_QUESTION,
                'text': self.current_question
            }))
            self.phase = self.PHASE_QUESTION
            # 注意：不再在这里清空buffer，而是在音视频处理完成后清空
            print(f"[调试] 新问题开始，当前音频buffer长度: {len(self.audio_buffer) if hasattr(self, 'audio_buffer') else 0}")
            print(f"[调试] 新问题开始，当前视频buffer长度: {len(self.video_frame_buffer) if hasattr(self, 'video_frame_buffer') else 0}")
        else:
            print(f"[DEBUG] 问题队列为空，准备进入代码题阶段")
            # 保存最后一道题答案
            await self.save_current_answer()
            self.phase = self.PHASE_CODE
            await self.send(text_data=json.dumps({
                'type': 'interview_message',
                'phase': self.PHASE_CODE,
                'text': '问答环节结束，下面进入代码题环节。'
            }))
            print(f"[DEBUG] 准备调用 start_coding_problems")
            # 开始代码题阶段
            await self.start_coding_problems()
            print(f"[DEBUG] start_coding_problems 调用完成")

    async def save_current_answer(self):
        """保存当前问题的答案"""
        print("[调试] save_current_answer called, current_question:", self.current_question)
        
        if not self.video_stream:
            print("[调试] save_current_answer异常: video_stream 未初始化")
            return
            
        if self.current_question:
            # 不依赖实时转写内容，答案文本将通过音频文件转写获得
            answer_text = "[答案内容将通过音频文件转写获得]"
            print("[调试] answer_text:", answer_text)
            
            try:
                from interviews.models import Interview, InterviewAnswer
                # 获取面试记录
                interview = await self.get_interview_by_id(self.interview_id)
                
                # 获取当前问题的知识点
                knowledge_points = getattr(self, 'current_question_knowledge_points', [])
                
                answer = await database_sync_to_async(InterviewAnswer.objects.create)(
                    interview=interview,
                    user=self.user,
                    question=self.current_question,
                    answer=answer_text,  # 临时占位，后续会被音频转写结果替换
                    knowledge_points=knowledge_points
                )
                
                print(f"[调试] 已保存答案记录，知识点: {knowledge_points}")
                
                # 异步处理音视频片段，避免阻塞 ASR
                # 注意：不在这里创建AI分析任务，等待音频转写完成后再创建
                try:
                    # 创建异步任务处理音视频
                    asyncio.create_task(self._async_save_av_clip(answer.id))
                    print(f"[调试] 已创建异步音视频处理任务 - answer_id: {answer.id}")
                except Exception as av_error:
                    print(f"[警告] 异步音视频任务创建失败: {av_error}")
                
                # 清空当前问题和答案（但不清空buffer，等音视频处理完成后再清空）
                self.current_question = None
                self.current_question_knowledge_points = []
                self.current_answer_final = []
                self.current_answer_sentences = []
                self.current_answer_start_time = None
                
            except Exception as e:
                print(f"[调试] save_current_answer错误: {e}")
                print(traceback.format_exc())

    async def _async_save_av_clip(self, answer_id):
        """异步保存音视频片段"""
        try:
            # 使用线程池处理音视频合成，避免阻塞事件循环
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(executor, self._sync_save_av_clip)
            
            print(f"[调试] 异步音视频保存成功: {result}")
            
            # 根据保存的文件类型决定分析策略
            if result['av_path']:
                try:
                    from interviews.tasks import analyze_interview_answer
                    
                    # 传递详细信息给分析任务
                    await database_sync_to_async(analyze_interview_answer.delay)(
                        str(answer_id), 
                        result['av_path'],
                        result['audio_path'],
                        result['has_audio'],
                        result['has_video']
                    )
                    print(f"[调试] 已创建分析任务 - id: {answer_id}, av_path: {result['av_path']}")
                except Exception as task_error:
                    print(f"[警告] 创建分析任务失败: {task_error}")
            else:
                print(f"[警告] 无音视频文件，跳过AI分析 - answer_id: {answer_id}")
            
            # 音视频处理完成后，清空buffer
            self.audio_buffer = []
            self.video_frame_buffer = []
            print(f"[调试] 音视频处理完成，已清空buffer")
                
        except Exception as e:
            print(f"[错误] 异步音视频处理失败: {e}")
            print(traceback.format_exc())
            # 即使处理失败，也要清空buffer
            self.audio_buffer = []
            self.video_frame_buffer = []
            print(f"[调试] 音视频处理失败，已清空buffer")

    def _sync_save_av_clip(self):
        """同步保存音视频片段（在线程池中运行）"""
        save_dir = './interview_clips'
        os.makedirs(save_dir, exist_ok=True)
        q_idx = getattr(self, 'current_question_idx', 0)
        session_id = getattr(self, 'session_id', 'unknown')
        audio_path = os.path.join(save_dir, f'{session_id}_q{q_idx+1}.wav')
        img_dir = os.path.join(save_dir, f'{session_id}_q{q_idx+1}_frames')
        os.makedirs(img_dir, exist_ok=True)
        video_path = os.path.join(save_dir, f'{session_id}_q{q_idx+1}_av.mp4')

        # 调试信息：检查buffer状态
        print(f"[调试] 音频buffer长度: {len(self.audio_buffer) if hasattr(self, 'audio_buffer') else 'None'}")
        print(f"[调试] 视频buffer长度: {len(self.video_frame_buffer) if hasattr(self, 'video_frame_buffer') else 'None'}")
        
        if hasattr(self, 'audio_buffer') and self.audio_buffer:
            print(f"[调试] 音频buffer第一个chunk长度: {len(self.audio_buffer[0]) if self.audio_buffer else 'N/A'}")
            print(f"[调试] 音频buffer第一个chunk前50字符: {self.audio_buffer[0][:50] if self.audio_buffer else 'N/A'}")

        # 保存音频
        if self.audio_buffer:
            pcm_bytes = b''.join([base64.b64decode(chunk) for chunk in self.audio_buffer])
            print(f"[调试] 解码后的音频数据长度: {len(pcm_bytes)} bytes")
            
            if len(pcm_bytes) > 0:
                with wave.open(audio_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(pcm_bytes)
                audio_saved = True
                print(f"[调试] 音频文件保存成功: {audio_path}")
            else:
                print(f"[调试] 警告：解码后的音频数据为空")
                audio_path = None
                audio_saved = False
        else:
            audio_path = None
            audio_saved = False
            print(f"[调试] 音频buffer为空")

        # 保存视频帧
        img_paths = []
        if self.video_frame_buffer:
            print(f"[调试] 开始保存视频帧，共{len(self.video_frame_buffer)}帧")
            for i, b64img in enumerate(self.video_frame_buffer):
                img_path = os.path.join(img_dir, f'frame_{i:04d}.jpg')
                with open(img_path, 'wb') as f:
                    f.write(base64.b64decode(b64img))
                img_paths.append(img_path)
            video_saved = True
            print(f"[调试] 视频帧保存成功，共{len(img_paths)}帧")
        else:
            video_saved = False
            print(f"[调试] 视频buffer为空")

        # 合成带声mp4
        try:
            # 检查ffmpeg是否可用
            import subprocess
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
                ffmpeg_available = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                ffmpeg_available = False
                print("[警告] ffmpeg未安装或不在PATH中，跳过音视频合成")
            
            if ffmpeg_available:
                if audio_path and img_paths:
                    print(f"[调试] 开始合成音视频文件")
                    video_stream = ffmpeg.input(os.path.join(img_dir, 'frame_%04d.jpg'), framerate=1)
                    audio_stream = ffmpeg.input(audio_path)
                    (
                        ffmpeg
                        .output(video_stream, audio_stream, video_path, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', shortest=None)
                        .run(overwrite_output=True)
                    )
                    av_path = video_path
                    has_audio = True
                    has_video = True
                    print(f"[调试] 音视频合成成功: {video_path}")
                elif audio_path:
                    av_path = audio_path
                    has_audio = True
                    has_video = False
                    print(f"[调试] 只有音频文件: {audio_path}")
                elif img_paths:
                    # 只合成无声视频
                    video_only_path = os.path.join(save_dir, f'{session_id}_q{q_idx+1}_video.mp4')
                    print(f"[调试] 开始合成无声视频")
                    (
                        ffmpeg
                        .input(os.path.join(img_dir, 'frame_%04d.jpg'), framerate=1)
                        .output(video_only_path, vcodec='libx264', pix_fmt='yuv420p')
                        .run(overwrite_output=True)
                    )
                    av_path = video_only_path
                    has_audio = False
                    has_video = True
                    print(f"[调试] 无声视频合成成功: {video_only_path}")
                else:
                    av_path = None
                    has_audio = False
                    has_video = False
                    print(f"[调试] 无音视频数据")
            else:
                # ffmpeg不可用时，只保存音频或图片
                if audio_path:
                    av_path = audio_path
                    has_audio = True
                    has_video = False
                    print(f"[调试] ffmpeg不可用，使用音频文件: {audio_path}")
                elif img_paths:
                    # 保存第一张图片作为代表
                    import shutil
                    first_img = os.path.join(img_dir, 'frame_0001.jpg')
                    if os.path.exists(first_img):
                        img_path = os.path.join(save_dir, f'{session_id}_q{q_idx+1}_image.jpg')
                        shutil.copy2(first_img, img_path)
                        av_path = img_path
                        has_audio = False
                        has_video = False
                        print(f"[调试] ffmpeg不可用，保存图片: {img_path}")
                    else:
                        av_path = None
                        has_audio = False
                        has_video = False
                        print(f"[调试] ffmpeg不可用，无图片可保存")
                else:
                    av_path = None
                    has_audio = False
                    has_video = False
                    print(f"[调试] ffmpeg不可用，无音视频数据")
                    
        except Exception as e:
            print(f"[错误] 音视频合成失败: {e}")
            # 出错时，尝试保存音频或图片
            if audio_path:
                av_path = audio_path
                has_audio = True
                has_video = False
                print(f"[调试] 合成失败，使用音频文件: {audio_path}")
            elif img_paths:
                # 保存第一张图片作为代表
                try:
                    import shutil
                    first_img = os.path.join(img_dir, 'frame_0001.jpg')
                    if os.path.exists(first_img):
                        img_path = os.path.join(save_dir, f'{session_id}_q{q_idx+1}_image.jpg')
                        shutil.copy2(first_img, img_path)
                        av_path = img_path
                    else:
                        av_path = None
                except Exception as img_error:
                    print(f"[错误] 保存图片失败: {img_error}")
                    av_path = None
                    has_audio = False
                    has_video = False
            else:
                av_path = None
                has_audio = False
                has_video = False
                print(f"[调试] 合成失败，无音视频数据")
        
        self.current_question_idx = q_idx + 1
        
        # 返回详细信息
        result = {
            'av_path': av_path,
            'audio_path': audio_path if has_audio else None,
            'has_audio': has_audio,
            'has_video': has_video
        }
        print(f"[调试] 返回结果: {result}")
        return result

    async def finish_interview(self):
        """结束面试"""
        try:
            # 发送面试结束消息
            await self.send(text_data=json.dumps({
                'type': 'interview_finished',
                'text': '面试已结束，感谢您的参与！我们会尽快给出面试评价。祝您求职顺利！'
            }))
            
            # 更新面试状态
            from interviews.models import Interview
            interview = await self.get_interview_by_id(self.interview_id)
            if interview:
                await database_sync_to_async(setattr)(interview, 'status', 'completed')
                await database_sync_to_async(interview.save)()
            
            # 关闭WebSocket连接
            await self.close()
            
        except Exception as e:
            print(f"[调试] finish_interview错误: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': f'结束面试时出错: {str(e)}'
            }))

    async def save_av_clip_for_question(self):
        """
        保存当前问题的音视频片段到本地文件，返回带声mp4路径。
        """
        save_dir = './interview_clips'
        os.makedirs(save_dir, exist_ok=True)
        q_idx = getattr(self, 'current_question_idx', 0)
        session_id = getattr(self, 'session_id', 'unknown')
        audio_path = os.path.join(save_dir, f'{session_id}_q{q_idx+1}.wav')
        img_dir = os.path.join(save_dir, f'{session_id}_q{q_idx+1}_frames')
        os.makedirs(img_dir, exist_ok=True)
        video_path = os.path.join(save_dir, f'{session_id}_q{q_idx+1}_av.mp4')

        # 保存音频
        if self.audio_buffer:
            pcm_bytes = b''.join([base64.b64decode(chunk) for chunk in self.audio_buffer])
            with wave.open(audio_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(pcm_bytes)
        else:
            audio_path = None

        # 保存视频帧
        img_paths = []
        if self.video_frame_buffer:
            for i, b64img in enumerate(self.video_frame_buffer):
                img_path = os.path.join(img_dir, f'frame_{i:04d}.jpg')
                with open(img_path, 'wb') as f:
                    f.write(base64.b64decode(b64img))
                img_paths.append(img_path)

        # 合成带声mp4
        try:
            # 检查ffmpeg是否可用
            import subprocess
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
                ffmpeg_available = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                ffmpeg_available = False
                print("[警告] ffmpeg未安装或不在PATH中，跳过音视频合成")
            
            if ffmpeg_available:
                if audio_path and img_paths:
                    video_stream = ffmpeg.input(os.path.join(img_dir, 'frame_%04d.jpg'), framerate=1)
                    audio_stream = ffmpeg.input(audio_path)
                    (
                        ffmpeg
                        .output(video_stream, audio_stream, video_path, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', shortest=None)
                        .run(overwrite_output=True)
                    )
                    av_path = video_path
                elif audio_path:
                    av_path = audio_path
                elif img_paths:
                    # 只合成无声视频
                    video_only_path = os.path.join(save_dir, f'{session_id}_q{q_idx+1}_video.mp4')
                    (
                        ffmpeg
                        .input(os.path.join(img_dir, 'frame_%04d.jpg'), framerate=1)
                        .output(video_only_path, vcodec='libx264', pix_fmt='yuv420p')
                        .run(overwrite_output=True)
                    )
                    av_path = video_only_path
                else:
                    av_path = None
            else:
                # ffmpeg不可用时，只保存音频或图片
                if audio_path:
                    av_path = audio_path
                elif img_paths:
                    # 保存第一张图片作为代表
                    import shutil
                    first_img = os.path.join(img_dir, 'frame_0001.jpg')
                    if os.path.exists(first_img):
                        img_path = os.path.join(save_dir, f'{session_id}_q{q_idx+1}_image.jpg')
                        shutil.copy2(first_img, img_path)
                        av_path = img_path
                    else:
                        av_path = None
                else:
                    av_path = None
                    
        except Exception as e:
            print(f"[错误] 音视频合成失败: {e}")
            # 出错时，尝试保存音频或图片
            if audio_path:
                av_path = audio_path
            elif img_paths:
                # 保存第一张图片作为代表
                try:
                    import shutil
                    first_img = os.path.join(img_dir, 'frame_0001.jpg')
                    if os.path.exists(first_img):
                        img_path = os.path.join(save_dir, f'{session_id}_q{q_idx+1}_image.jpg')
                        shutil.copy2(first_img, img_path)
                        av_path = img_path
                    else:
                        av_path = None
                except Exception as img_error:
                    print(f"[错误] 保存图片失败: {img_error}")
                    av_path = None
            else:
                av_path = None

        self.current_question_idx = q_idx + 1
        return av_path

    async def analyze_confidence_fluency(self, question, answer_text, av_path=None):
        prompt = f"请根据以下面试问题和应答，判断应答者在回答时的信心和表达流畅度，并按如下标准打1-5分：\\n1分：极度缺乏信心，表达极不流畅，长时间停顿或语无伦次。\\n2分：信心不足，表达有明显卡顿或多次重复、犹豫。\\n3分：信心一般，表达基本流畅但偶有停顿或语气不坚定。\\n4分：信心较强，表达流畅，偶有小瑕疵。\\n5分：非常有信心，表达极其流畅，思路清晰、语气坚定。\\n请输出分析理由和分数。\\n\\n面试问题：{question}\\n应答内容：{answer_text}"
        try:
            client = OpenAI(
                api_key=settings.QWEN_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            
            # 构建消息内容
            content = [{"type": "text", "text": prompt}]
            
            # 如果有视频文件，添加为base64编码的内容
            if av_path and av_path.endswith('.mp4'):
                with open(av_path, "rb") as f:
                    video_bytes = f.read()
                video_b64 = base64.b64encode(video_bytes).decode('utf-8')
                content.append({
                    "type": "video_url",
                    "video_url": {
                        "url": f"data:;base64,{video_b64}"
                    }
                })
            
            completion = client.chat.completions.create(
                model="qwen2.5-omni-7b",
                messages=[{"role": "user", "content": content}],
                modalities=["text"],
                stream=True
            )
            
            # 处理流式响应
            full_response = ""
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
            
            print("[调试] qwen2.5-omni-7b分析结果：", full_response)
        except Exception as e:
            print(f"qwen2.5-omni-7b API调用异常: {e}")
    
    # 数据库操作方法
    @database_sync_to_async
    def get_user(self):
        return self.scope.get('user', None)
    
    @database_sync_to_async
    def create_video_stream(self, title, description):
        """创建视频流"""
        return VideoStream.objects.create(  # type: ignore
            user=self.user,
            title=title,
            description=description,
            is_active=True
        )
    
    @database_sync_to_async
    def get_video_stream(self, stream_id):
        """获取视频流"""
        try:
            return VideoStream.objects.get(id=stream_id, is_active=True)  # type: ignore
        except VideoStream.DoesNotExist:  # type: ignore
            return None
    
    @database_sync_to_async
    def create_connection(self):
        """创建WebRTC连接记录"""
        return WebRTCConnection.objects.create(  # type: ignore
            video_stream=self.video_stream,
            session_id=self.session_id,
            peer_id=self.peer_id or str(uuid.uuid4()),
            connection_state='new'
        )
    
    @database_sync_to_async
    def update_connection_state(self, state):
        """更新连接状态"""
        if self.connection:
            self.connection.connection_state = state
            self.connection.save()
    
    @database_sync_to_async
    def deactivate_video_stream(self):
        """停用视频流"""
        if self.video_stream:
            self.video_stream.is_active = False
            self.video_stream.save()
    
    @database_sync_to_async
    def save_video_frame(self, frame_data, frame_type):
        """保存视频帧"""
        from .models import VideoFrame  # type: ignore
        # 确保frame_data是bytes格式，因为VideoFrame.frame_data是BinaryField
        if isinstance(frame_data, str):
            # 如果是base64字符串，先解码为bytes
            if frame_data.startswith('data:image'):
                frame_data = frame_data.split(',', 1)[-1]
            frame_data = base64.b64decode(frame_data)
        elif not isinstance(frame_data, bytes):
            frame_data = bytes(frame_data)
        return VideoFrame.objects.create(  # type: ignore
            video_stream=self.video_stream,
            frame_data=frame_data,
            frame_type=frame_type
        )
    
    # 广播方法
    async def broadcast_offer(self, event):
        """广播offer"""
        await self.send(text_data=json.dumps({
            'type': 'offer',
            'offer': event['offer'],
            'peer_id': event['peer_id']
        }))
    
    async def send_answer(self, event):
        """发送answer"""
        await self.send(text_data=json.dumps({
            'type': 'answer',
            'answer': event['answer'],
            'peer_id': event['peer_id']
        }))
    
    async def send_ice_candidate(self, event):
        """发送ICE候选"""
        await self.send(text_data=json.dumps({
            'type': 'ice_candidate',
            'candidate': event['candidate'],
            'peer_id': event['peer_id']
        }))
    
    async def broadcast_video_frame(self, event):
        """广播视频帧"""
        await self.send(text_data=json.dumps({
            'type': 'video_frame',
            'frame_data': event['frame_data'],
            'frame_type': event['frame_type'],
            'peer_id': event['peer_id']
        }))
    
    async def start_coding_problems(self):
        """开始代码题环节"""
        print(f"[DEBUG] start_coding_problems called")
        try:
            # 获取面试和简历信息
            interview = await self.get_interview_by_id(self.interview_id)
            resume = await self.get_resume_by_id(self.resume_id)
            
            print(f"[DEBUG] 获取到面试: {interview}, 简历: {resume}")
            
            if not interview or not resume:
                print("[DEBUG] 无法获取面试或简历信息")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'text': '无法获取面试或简历信息'
                }))
                return
            
            # 使用代码题选择服务选择合适的题目
            from interviews.services import CodingProblemService
            coding_service = CodingProblemService()
            print(f"[DEBUG] 初始化代码题服务: {coding_service}")
            self.coding_problems = await database_sync_to_async(
                coding_service.select_problems_for_interview
            )(interview, resume, limit=3)
            print(f"[DEBUG] 选择代码题: {self.coding_problems}")
            if not self.coding_problems:
                print("[DEBUG] 没有找到合适的代码题")
                await self.send(text_data=json.dumps({
                    'type': 'interview_message',
                    'phase': self.PHASE_CODE,
                    'text': '抱歉，没有找到合适的代码题。面试结束。'
                }))
                return
            
            print(f"[DEBUG] 准备开始第一道代码题")
            # 开始第一道代码题
            await self.start_next_coding_problem()
            print(f"[DEBUG] start_next_coding_problem 调用完成")
            
        except Exception as e:
            print(f"[DEBUG] start_coding_problems error: {e}")
            print(traceback.format_exc())
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': f'代码题加载失败: {str(e)}'
            }))
    
    async def start_next_coding_problem(self):
        """开始下一道代码题"""
        print(f"[DEBUG] start_next_coding_problem called, coding_problems: {self.coding_problems}")
        print(f"[DEBUG] WebSocket连接状态: {self.channel_name}")
        
        if not self.coding_problems:
            print("[DEBUG] 没有更多代码题，面试结束")
            # 面试全部结束
            # await self.send(text_data=json.dumps({
            #     'type': 'interview_message',
            #     'phase': self.PHASE_CODE,
            #     'text': '代码题环节结束。'
            # }))
            await self.finish_interview()
            return
        
        # 取出下一道题
        self.current_coding_problem = self.coding_problems.pop(0)
        print(f"[DEBUG] 当前代码题: {self.current_coding_problem}")
        print(f"[DEBUG] 代码题ID: {self.current_coding_problem.id}")
        print(f"[DEBUG] 代码题标题: {self.current_coding_problem.title}")
        
        try:
            # 获取第一个样例
            print(f"[DEBUG] 准备获取第一个样例")
            first_example = await database_sync_to_async(
                lambda: self.current_coding_problem.examples.first()
            )()
            print(f"[DEBUG] 第一个样例: {first_example}")
            
            # 构造代码题信息
            problem_data = {
                'type': 'coding_problem',
                'phase': self.PHASE_CODE,
                'problem': {
                    'id': self.current_coding_problem.id,
                    'number': self.current_coding_problem.number,
                    'title': self.current_coding_problem.title,
                    'description': self.current_coding_problem.description,
                    'difficulty': self.current_coding_problem.difficulty,
                    'tags': self.current_coding_problem.tags,
                    'example': {
                        'input': first_example.input_data if first_example else '',
                        'output': first_example.output_data if first_example else '',
                        'explanation': first_example.explanation if first_example else ''
                    } if first_example else None
                }
            }
            
            print(f"[DEBUG] 准备发送代码题数据: {problem_data}")
            await self.send(text_data=json.dumps(problem_data))
            print(f"[DEBUG] 代码题数据发送成功")
            
        except Exception as e:
            print(f"[DEBUG] start_next_coding_problem error: {e}")
            print(traceback.format_exc())
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': f'代码题加载失败: {str(e)}'
            }))
    
    async def handle_request_next_coding_problem(self):
        """处理请求下一道代码题"""
        if self.phase != self.PHASE_CODE:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': '当前不在代码题阶段'
            }))
            return
        
        await self.start_next_coding_problem()
    
    async def handle_submit_coding_answer(self, data):
        """处理代码题答案提交"""
        if self.phase != self.PHASE_CODE:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': '当前不在代码题阶段'
            }))
            return
        
        if not self.current_coding_problem:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': '没有当前代码题'
            }))
            return
        
        try:
            user_code = data.get('code', '')
            language = data.get('language', 'python')
            
            # 保存代码答案到数据库
            from interviews.models import Interview, InterviewCodingAnswer
            interview = await self.get_interview_by_id(self.interview_id)
            
            await database_sync_to_async(InterviewCodingAnswer.objects.create)(
                interview=interview,
                user=self.user,
                problem=self.current_coding_problem,
                code_answer=user_code,
                language=language
            )
            
            await self.send(text_data=json.dumps({
                'type': 'coding_answer_submitted',
                'text': '代码已提交成功'
            }))
            
        except Exception as e:
            print(f"[DEBUG] handle_submit_coding_answer error: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': f'提交代码失败: {str(e)}'
            }))