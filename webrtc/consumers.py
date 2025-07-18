import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import VideoStream, WebRTCConnection  # type: ignore
from .services import webrtc_service, XunfeiRTASRClient
import uuid
import base64
from knowledge_base.services import KnowledgeBaseService
from users.models import Resume
from knowledge_base.models import JobPosition
import threading

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
        self.rtasr_client = None  # 讯飞RTASR实例
        self.question_queue = []  # 面试问题队列
        self.phase = self.PHASE_INTRO
        self.silence_timer = None
        self.last_asr_text = ''
        self._ws_loop = None

    async def connect(self):
        print("[WebRTCConsumer] connect called")
        await self.accept()
        try:
            self.user = await self.get_user() if hasattr(self, 'get_user') else None
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
                'message': 'WebRTC连接已建立'
            }))
            # 主动推送面试官开场白
            await self.send(text_data=json.dumps({
                'type': 'interview_message',
                'phase': self.PHASE_INTRO,
                'message': '请开始自我介绍吧'
            }))
            self.phase = self.PHASE_INTRO
            self.start_silence_timer()
        except Exception as e:
            print(f"[WebRTCConsumer] connect error: {e}")
            await self.send(text_data=json.dumps({'type': 'error', 'message': f'初始化失败: {e}'}))

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
        print(f"[WebRTCConsumer] receive called, text_data={text_data}")
        """接收WebSocket消息"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            print(f"[WebRTCConsumer] receive message_type={message_type}")
            
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
                    'message': f'未知的消息类型: {message_type}'
                }))
                
        except json.JSONDecodeError:
            print("[WebRTCConsumer] receive JSON decode error")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': '无效的JSON格式'
            }))
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}")
            print(f"[WebRTCConsumer] receive error: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'处理消息时出错: {str(e)}'
            }))
    
    async def handle_create_stream(self, data):
        """处理创建视频流请求"""
        try:
            title = data.get('title', '未命名流')
            description = data.get('description', '')
            
            # 创建视频流
            self.video_stream = await self.create_video_stream(title, description)
            
            # 创建WebRTC连接记录
            self.connection = await self.create_connection()
            
            await self.send(text_data=json.dumps({
                'type': 'stream_created',
                'stream_id': str(self.video_stream.id),
                'title': self.video_stream.title,
                'message': '视频流创建成功'
            }))
            
        except Exception as e:
            logger.error(f"创建视频流失败: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'创建视频流失败: {str(e)}'
            }))
    
    async def handle_join_stream(self, data):
        """处理加入视频流请求"""
        try:
            stream_id = data.get('stream_id')
            if not stream_id:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': '缺少流ID'
                }))
                return
            
            # 获取视频流
            self.video_stream = await self.get_video_stream(stream_id)
            if not self.video_stream:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': '视频流不存在'
                }))
                return
            
            # 创建连接记录
            self.connection = await self.create_connection()
            
            await self.send(text_data=json.dumps({
                'type': 'stream_joined',
                'stream_id': str(self.video_stream.id),
                'title': self.video_stream.title,
                'message': '成功加入视频流'
            }))
            
        except Exception as e:
            logger.error(f"加入视频流失败: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'加入视频流失败: {str(e)}'
            }))
    
    async def handle_offer(self, data):
        """处理WebRTC offer"""
        try:
            offer = data.get('offer')
            if not offer:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': '缺少offer数据'
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
                'message': f'处理offer失败: {str(e)}'
            }))
    
    async def handle_answer(self, data):
        """处理WebRTC answer"""
        try:
            answer = data.get('answer')
            target_peer = data.get('target_peer')
            
            if not answer or not target_peer:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': '缺少answer或target_peer数据'
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
                'message': f'处理answer失败: {str(e)}'
            }))
    
    async def handle_ice_candidate(self, data):
        """处理ICE候选"""
        try:
            candidate = data.get('candidate')
            target_peer = data.get('target_peer')
            
            if not candidate or not target_peer:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': '缺少candidate或target_peer数据'
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
                'message': f'处理ICE候选失败: {str(e)}'
            }))
    
    async def handle_video_frame(self, data):
        """处理视频帧数据"""
        try:
            frame_data = data.get('frame_data')
            frame_type = data.get('frame_type', 'keyframe')
            
            if not frame_data:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': '缺少帧数据'
                }))
                return
            
            # 保存视频帧
            await self.save_video_frame(frame_data, frame_type)
            
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
            
        except Exception as e:
            logger.error(f"处理视频帧失败: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'处理视频帧失败: {str(e)}'
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
                    'message': '缺少音频数据'
                }))
                return
            audio_bytes = base64.b64decode(audio_data)
            if self.rtasr_client and self.rtasr_client.connected and not self.rtasr_client.closed:
                self.rtasr_client.send_audio(audio_bytes)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'RTASR未连接'
                }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'音频帧处理出错: {str(e)}'
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
    
    def start_silence_timer(self, timeout=15):
        if self.silence_timer:
            self.silence_timer.cancel()
        loop = self._ws_loop or asyncio.get_event_loop()
        self.silence_timer = loop.call_later(timeout, lambda: asyncio.run_coroutine_threadsafe(self.handle_silence(), loop))

    def reset_silence_timer(self, timeout=15):
        self.start_silence_timer(timeout)

    async def handle_silence(self):
        # 15s无语音，自动切换阶段
        if self.phase == self.PHASE_INTRO:
            await self.finish_intro()
        elif self.phase == self.PHASE_QUESTION:
            await self.next_question()
        # 代码题阶段暂不处理

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
        self.last_asr_text = asr_text
        # 重置静默计时
        self.reset_silence_timer()
        # 推送asr_result消息
        await self.send(text_data=json.dumps({
            'type': 'asr_result',
            'text': asr_text
        }))
        # 检查“说完了”
        if '说完了' in asr_text:
            if self.phase == self.PHASE_INTRO:
                await self.finish_intro()
            elif self.phase == self.PHASE_QUESTION:
                await self.next_question()

    async def finish_intro(self):
        self.phase = self.PHASE_QUESTION
        if self.silence_timer:
            self.silence_timer.cancel()
        await self.send(text_data=json.dumps({
            'type': 'interview_message',
            'phase': self.PHASE_QUESTION,
            'message': '自我介绍结束，下面开始问问题。'
        }))
        await asyncio.sleep(1)
        await self.next_question()

    async def next_question(self):
        if self.silence_timer:
            self.silence_timer.cancel()
        if self.question_queue:
            question = self.question_queue.pop(0)
            await self.send(text_data=json.dumps({
                'type': 'interview_message',
                'phase': self.PHASE_QUESTION,
                'message': question
            }))
            self.phase = self.PHASE_QUESTION
            self.start_silence_timer()
        else:
            self.phase = self.PHASE_CODE
            await self.send(text_data=json.dumps({
                'type': 'interview_message',
                'phase': self.PHASE_CODE,
                'message': '问答环节结束，下面进入代码题环节。'
            }))
            # 代码题阶段暂不处理
    
    # 数据库操作方法
    @database_sync_to_async
    def get_user(self):
        """获取用户信息"""
        if hasattr(self.scope, 'user'):
            return self.scope['user']
        return None
    
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