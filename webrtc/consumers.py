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
from knowledge_base.models import JobPosition
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
from config.local_settings import QWEN_API_KEY
import os
import datetime
import wave
import ffmpeg
import numpy as np
from requests_toolbelt.multipart.encoder import MultipartEncoder
from openai import OpenAI

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
        self.rtasr_client = None  # 讯飞RTASR实例
        self.question_queue = []  # 面试问题队列
        self.phase = self.PHASE_INTRO
        self.last_asr_text = ''
        self._ws_loop = None
        self.current_question = None
        self.current_answer_sentences = []
        self.current_answer_final = []
        self.current_answer_start_time = None
        self.current_question_idx = 0 # 新增：记录当前问题的序号
        self.audio_buffer = []
        self.video_frame_buffer = []
    
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
                print('[RTASR回调]', text)
                asyncio.run_coroutine_threadsafe(self.handle_asr_result(text), loop)
            def start_rtasr():
                try:
                    print("[WebRTCConsumer] RTASR ws connecting...")
                    self.rtasr_client = XunfeiRTASRClient(app_id='08425c8a', api_key='c64481ae5aac8c1ad9993125c7a6fdbc', on_result=on_rtasr_result)
                    self.rtasr_client.connect()
                    print("[WebRTCConsumer] RTASR ws connected")
                except Exception as e:
                    print(f"[WebRTCConsumer] RTASR ws connect error: {e}")
                    asyncio.run_coroutine_threadsafe(
                        self.send(text_data=json.dumps({'type': 'asr_result', 'text': f'[RTASR连接失败] {e}'})), loop)
            threading.Thread(target=start_rtasr, daemon=True).start()
            self.question_queue = await self.init_question_queue()
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'session_id': self.session_id,
                'text': 'WebRTC连接已建立'
            }))
            # 主动推送面试官开场白
            await self.send(text_data=json.dumps({
                'type': 'interview_message',
                'phase': self.PHASE_INTRO,
                'text': '请开始自我介绍吧'
            }))
            self.phase = self.PHASE_INTRO
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
            
            # 创建视频流
            self.video_stream = await self.create_video_stream(title, description)
            
            # 创建WebRTC连接记录
            self.connection = await self.create_connection()
            
            await self.send(text_data=json.dumps({
                'type': 'stream_created',
                'stream_id': str(self.video_stream.id),
                'title': self.video_stream.title,
                'interview_id': self.interview_id,
                'text': '视频流创建成功'
            }))
            
        except Exception as e:
            logger.error(f"创建视频流失败: {str(e)}")
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
        except Exception as e:
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
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'text': 'RTASR未连接'
                }))
            if audio_data:
                self.audio_buffer.append(audio_data)
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': f'音频帧处理出错: {str(e)}'
            }))
    
    async def handle_request_next_question(self):
        """处理前端请求下一个面试问题"""
        if self.question_queue:
            question = self.question_queue.pop(0)
            await self.send(text_data=json.dumps({
                'type': 'next_question',
                'question': question
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'next_question',
                'question': '已无更多问题'
            }))

    async def init_question_queue(self):
        """初始化面试问题队列（实际应根据岗位/简历信息调用知识库服务）"""
        # TODO: 这里用测试数据，实际应从前端传岗位/简历id后调用KnowledgeBaseService
        # 示例：job_position = JobPosition.objects.get(id=xxx)
        #      resume = Resume.objects.get(id=xxx)
        #      questions = KnowledgeBaseService().search_relevant_questions(job_position, resume, limit=5)
        #      return [q['question'] for q in questions]
        return [
            '请简单自我介绍一下。',
            '你为什么选择我们公司？',
            '请介绍一下你最近的一个项目。',
            '你遇到过最大的技术难题是什么？',
            '你对未来的职业规划是什么？'
        ]
    
    async def handle_disconnect(self, data):
        """处理断开连接请求"""
        try:
            await self.update_connection_state('disconnected')
            await self.close(code=1000)
            
        except Exception as e:
            logger.error(f"断开连接失败: {str(e)}")
    


    async def handle_asr_result(self, text):
        # 只处理中文文本
        asr_text = ''
        try:
            obj = json.loads(text) if isinstance(text, str) else text
            def extract_chinese(obj):
                result = ''
                if isinstance(obj, str):
                    result += ''.join([c for c in obj if '\u4e00' <= c <= '\u9fa5'])
                elif isinstance(obj, list):
                    for item in obj:
                        result += extract_chinese(item)
                elif isinstance(obj, dict):
                    for v in obj.values():
                        result += extract_chinese(v)
                return result
            asr_text = extract_chinese(obj)
        except Exception:
            asr_text = str(text)
        print("[调试] handle_asr_result asr_text:", asr_text)
        print("[调试] handle_asr_result phase:", self.phase, "current_question:", self.current_question)
        self.last_asr_text = asr_text
        # 记录答案（自我介绍和问答阶段都记录）
        if self.current_question and asr_text.strip():
            print("[调试] handle_asr_result append to current_answer_final:", asr_text.strip())
            self.current_answer_final.append(asr_text.strip())
        print("[调试] handle_asr_result current_answer_final:", self.current_answer_final)
        # 检查“说完了”
        if '说完了' in asr_text:
            print("[调试] handle_asr_result 检测到说完了，准备保存答案")
            if self.phase == self.PHASE_INTRO:
                await self.finish_intro()
            elif self.phase == self.PHASE_QUESTION:
                await self.save_current_answer()
                await self.next_question()
        # 每次都推送转写内容给前端
        await self.send(text_data=json.dumps({
            'type': 'asr_result',
            'text': asr_text
        }))

    async def finish_intro(self):
        self.phase = self.PHASE_QUESTION
        await self.send(text_data=json.dumps({
            'type': 'interview_message',
            'phase': self.PHASE_QUESTION,
            'text': '自我介绍结束，下面开始问问题。'
        }))
        self.question_queue = await self.init_question_queue()
        await self.next_question()

    async def next_question(self):
        if self.question_queue:
            self.current_question = self.question_queue.pop(0)
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
            # 新问题开始时清空buffer
            self.audio_buffer = []
            self.video_frame_buffer = []
        else:
            # 保存最后一道题答案
            await self.save_current_answer()
            self.phase = self.PHASE_CODE
            await self.send(text_data=json.dumps({
                'type': 'interview_message',
                'phase': self.PHASE_CODE,
                'text': '问答环节结束，下面进入代码题环节。'
            }))
            # 代码题阶段暂不处理

    async def save_current_answer(self):
        print("[调试] save_current_answer called, current_question:", self.current_question)
        print("[调试] save_current_answer called, current_answer_final:", self.current_answer_final)
        if not self.video_stream:
            print("[调试] save_current_answer异常: video_stream 未初始化")
            return
        if self.current_question and self.current_answer_final:
            answer_text = '\n'.join(self.current_answer_final)
            print("[调试] answer_text:", answer_text)
            try:
                from interviews.models import Interview, InterviewAnswer
                # 获取面试记录
                interview = await database_sync_to_async(Interview.objects.get)(id=self.interview_id)
                await database_sync_to_async(InterviewAnswer.objects.create)(
                    interview=interview,
                    user=self.user,
                    question=self.current_question,
                    answer=answer_text
                )
                # 保存音视频片段
                av_path = await self.save_av_clip_for_question()
                print("[调试] 调用analyze_confidence_fluency，参数：", self.current_question, answer_text, av_path)
                await self.analyze_confidence_fluency(self.current_question, answer_text, av_path)
            except Exception as e:
                print("[调试] save_current_answer异常:", e)
        self.current_question = None
        self.current_answer_final = []
        self.current_answer_sentences = []
        self.current_answer_start_time = None

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

        self.current_question_idx = q_idx + 1
        return av_path

    async def analyze_confidence_fluency(self, question, answer_text, av_path=None):
        prompt = f"请根据以下面试问题和应答，判断应答者在回答时的信心和表达流畅度，并按如下标准打1-5分：\\n1分：极度缺乏信心，表达极不流畅，长时间停顿或语无伦次。\\n2分：信心不足，表达有明显卡顿或多次重复、犹豫。\\n3分：信心一般，表达基本流畅但偶有停顿或语气不坚定。\\n4分：信心较强，表达流畅，偶有小瑕疵。\\n5分：非常有信心，表达极其流畅，思路清晰、语气坚定。\\n请输出分析理由和分数。\\n\\n面试问题：{question}\\n应答内容：{answer_text}"
        try:
            client = OpenAI(
                api_key=QWEN_API_KEY,
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