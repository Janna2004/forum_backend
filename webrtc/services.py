import asyncio
import logging
import cv2
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.media import MediaPlayer, MediaRecorder
from av import VideoFrame
import base64
import json
from typing import Dict, Optional, List
from .models import VideoStream, WebRTCConnection, VideoFrame as VideoFrameModel
from websocket import create_connection, WebSocketConnectionClosedException

import base64
import hashlib
import hmac
import json
import threading
import time
from datetime import datetime
from urllib.parse import urlencode
import websocket
from urllib.parse import quote

from django.conf import settings

logger = logging.getLogger(__name__)

class VideoStreamTrack(MediaStreamTrack):
    """自定义视频流轨道"""
    
    kind = "video"
    
    def __init__(self, track_id: str, video_stream: VideoStream):
        super().__init__()
        self.track_id = track_id
        self.video_stream = video_stream
        self.frame_count = 0
        
    async def recv(self):
        """接收视频帧"""
        # 这里可以处理接收到的视频帧
        # 例如：保存到数据库、转发给其他客户端等
        frame = await super().recv()
        
        # 将视频帧转换为OpenCV格式
        img = frame.to_ndarray(format="bgr24")
        
        # 保存关键帧到数据库
        if self.frame_count % 30 == 0:  # 每30帧保存一次关键帧
            await self.save_keyframe(img)
        
        self.frame_count += 1
        return frame
    
    async def save_keyframe(self, img):
        """保存关键帧到数据库"""
        try:
            # 将图像编码为JPEG格式
            _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_data = buffer.tobytes()
            
            # 保存到数据库
            await self.save_frame_to_db(frame_data, 'keyframe')
            
        except Exception as e:
            logger.error(f"保存关键帧失败: {str(e)}")
    
    async def save_frame_to_db(self, frame_data: bytes, frame_type: str):
        """保存帧数据到数据库"""
        try:
            # 使用数据库同步操作
            await self._save_frame_async(frame_data, frame_type)
        except Exception as e:
            logger.error(f"保存帧到数据库失败: {str(e)}")
    
    @staticmethod
    async def _save_frame_async(frame_data: bytes, frame_type: str):
        """异步保存帧数据"""
        from channels.db import database_sync_to_async
        
        @database_sync_to_async
        def save_frame():
            return VideoFrameModel.objects.create(
                video_stream=VideoStream.objects.get(id=1),  # 这里需要根据实际情况获取
                frame_data=frame_data,
                frame_type=frame_type
            )
        
        return await save_frame()

class WebRTCService:
    """WebRTC服务类"""
    
    def __init__(self):
        self.peer_connections: Dict[str, RTCPeerConnection] = {}
        self.video_streams: Dict[str, VideoStream] = {}
        self.connections: Dict[str, WebRTCConnection] = {}
    
    async def create_peer_connection(self, session_id: str, stream_id: str) -> RTCPeerConnection:
        """创建对等连接"""
        try:
            # 创建RTCPeerConnection
            pc = RTCPeerConnection()
            
            # 设置事件处理器
            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"连接状态改变: {pc.connectionState}")
                await self.update_connection_state(session_id, pc.connectionState)
            
            @pc.on("track")
            async def on_track(track):
                logger.info(f"接收到媒体轨道: {track.kind}")
                
                if track.kind == "video":
                    # 创建自定义视频流轨道
                    video_track = VideoStreamTrack(track.id, self.video_streams.get(stream_id))
                    
                    # 将轨道添加到连接中
                    pc.addTrack(video_track)
                    
                    # 处理视频帧
                    await self.handle_video_track(track, stream_id)
            
            # 存储连接
            self.peer_connections[session_id] = pc
            
            return pc
            
        except Exception as e:
            logger.error(f"创建对等连接失败: {str(e)}")
            raise
    
    async def handle_video_track(self, track: MediaStreamTrack, stream_id: str):
        """处理视频轨道"""
        try:
            while True:
                frame = await track.recv()
                
                # 将视频帧转换为OpenCV格式
                img = frame.to_ndarray(format="bgr24")
                
                # 处理视频帧（例如：保存、转发等）
                await self.process_video_frame(img, stream_id)
                
        except Exception as e:
            logger.error(f"处理视频轨道失败: {str(e)}")
    
    async def process_video_frame(self, img: np.ndarray, stream_id: str):
        """处理视频帧"""
        try:
            # 这里可以添加视频处理逻辑
            # 例如：人脸检测、对象识别、视频压缩等
            
            # 保存关键帧
            if hasattr(self, '_frame_counter'):
                self._frame_counter += 1
            else:
                self._frame_counter = 0
            
            if self._frame_counter % 30 == 0:  # 每30帧保存一次
                await self.save_video_frame(img, stream_id)
            
        except Exception as e:
            logger.error(f"处理视频帧失败: {str(e)}")
    
    async def save_video_frame(self, img: np.ndarray, stream_id: str):
        """保存视频帧"""
        try:
            # 将图像编码为JPEG格式
            _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_data = buffer.tobytes()
            
            # 保存到数据库
            await self._save_frame_to_db(frame_data, stream_id, 'keyframe')
            
        except Exception as e:
            logger.error(f"保存视频帧失败: {str(e)}")
    
    @staticmethod
    async def _save_frame_to_db(frame_data: bytes, stream_id: str, frame_type: str):
        """异步保存帧数据到数据库"""
        from channels.db import database_sync_to_async
        
        @database_sync_to_async
        def save_frame():
            try:
                video_stream = VideoStream.objects.get(id=stream_id)
                return VideoFrameModel.objects.create(
                    video_stream=video_stream,
                    frame_data=frame_data,
                    frame_type=frame_type
                )
            except VideoStream.DoesNotExist:
                logger.error(f"视频流不存在: {stream_id}")
                return None
        
        return await save_frame()
    
    async def create_offer(self, session_id: str, stream_id: str) -> RTCSessionDescription:
        """创建offer"""
        try:
            pc = await self.create_peer_connection(session_id, stream_id)
            
            # 创建offer
            offer = await pc.createOffer()
            await pc.setLocalDescription(offer)
            
            return offer
            
        except Exception as e:
            logger.error(f"创建offer失败: {str(e)}")
            raise
    
    async def create_answer(self, session_id: str, offer: RTCSessionDescription) -> RTCSessionDescription:
        """创建answer"""
        try:
            pc = await self.create_peer_connection(session_id, "")
            
            # 设置远程描述
            await pc.setRemoteDescription(offer)
            
            # 创建answer
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
            return answer
            
        except Exception as e:
            logger.error(f"创建answer失败: {str(e)}")
            raise
    
    async def add_ice_candidate(self, session_id: str, candidate: dict):
        """添加ICE候选"""
        try:
            if session_id in self.peer_connections:
                pc = self.peer_connections[session_id]
                await pc.addIceCandidate(candidate)
            else:
                logger.warning(f"连接不存在: {session_id}")
                
        except Exception as e:
            logger.error(f"添加ICE候选失败: {str(e)}")
    
    async def close_connection(self, session_id: str):
        """关闭连接"""
        try:
            if session_id in self.peer_connections:
                pc = self.peer_connections[session_id]
                await pc.close()
                del self.peer_connections[session_id]
                
                # 更新连接状态
                await self.update_connection_state(session_id, "closed")
                
        except Exception as e:
            logger.error(f"关闭连接失败: {str(e)}")
    
    async def update_connection_state(self, session_id: str, state: str):
        """更新连接状态"""
        try:
            from channels.db import database_sync_to_async
            
            @database_sync_to_async
            def update_state():
                try:
                    connection = WebRTCConnection.objects.get(session_id=session_id)
                    connection.connection_state = state
                    connection.save()
                except WebRTCConnection.DoesNotExist:
                    logger.warning(f"连接记录不存在: {session_id}")
            
            await update_state()
            
        except Exception as e:
            logger.error(f"更新连接状态失败: {str(e)}")
    
    async def get_connection_stats(self, session_id: str) -> dict:
        """获取连接统计信息"""
        try:
            if session_id in self.peer_connections:
                pc = self.peer_connections[session_id]
                stats = await pc.getStats()
                return stats
            else:
                return {}
                
        except Exception as e:
            logger.error(f"获取连接统计失败: {str(e)}")
            return {}
    
    def get_active_connections(self) -> List[str]:
        """获取活跃连接列表"""
        return list(self.peer_connections.keys())
    
    async def cleanup(self):
        """清理资源"""
        try:
            # 关闭所有连接
            for session_id in list(self.peer_connections.keys()):
                await self.close_connection(session_id)
                
        except Exception as e:
            logger.error(f"清理资源失败: {str(e)}")



# 全局WebRTC服务实例
webrtc_service = WebRTCService() 