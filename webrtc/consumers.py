import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import VideoStream, WebRTCConnection
from .services import webrtc_service
import uuid

User = get_user_model()
logger = logging.getLogger(__name__)

class WebRTCConsumer(AsyncWebsocketConsumer):
    """WebRTC WebSocket消费者"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.session_id = None
        self.peer_id = None
        self.video_stream = None
        self.connection = None
    
    async def connect(self):
        """建立WebSocket连接"""
        try:
            # 允许匿名连接，不校验用户
            self.user = await self.get_user() if hasattr(self, 'get_user') else None
            self.session_id = str(uuid.uuid4())
            await self.accept()
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'session_id': self.session_id,
                'message': 'WebRTC连接已建立'
            }))
        except Exception as e:
            await self.close(code=4000)
    
    async def disconnect(self, close_code):
        """断开WebSocket连接"""
        try:
            if self.connection:
                await self.update_connection_state('disconnected')
            
            if self.video_stream:
                await self.deactivate_video_stream()
            
            logger.info(f"WebRTC连接已断开: {self.user.username if self.user else 'Unknown'} - {close_code}")
            
        except Exception as e:
            logger.error(f"断开连接时出错: {str(e)}")
    
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
            elif message_type == 'disconnect':
                await self.handle_disconnect(data)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'未知的消息类型: {message_type}'
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': '无效的JSON格式'
            }))
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}")
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
    
    async def handle_disconnect(self, data):
        """处理断开连接请求"""
        try:
            await self.update_connection_state('disconnected')
            await self.close(code=1000)
            
        except Exception as e:
            logger.error(f"断开连接失败: {str(e)}")
    
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
        return VideoStream.objects.create(
            user=self.user,
            title=title,
            description=description,
            is_active=True
        )
    
    @database_sync_to_async
    def get_video_stream(self, stream_id):
        """获取视频流"""
        try:
            return VideoStream.objects.get(id=stream_id, is_active=True)
        except VideoStream.DoesNotExist:
            return None
    
    @database_sync_to_async
    def create_connection(self):
        """创建WebRTC连接记录"""
        return WebRTCConnection.objects.create(
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
        from .models import VideoFrame
        return VideoFrame.objects.create(
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