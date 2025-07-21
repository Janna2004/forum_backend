import json
import asyncio
import websocket
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from datetime import datetime
import time
import hashlib
import base64
import hmac
from urllib.parse import urlencode
import logging
from channels.exceptions import DenyConnection
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from email.utils import formatdate

logger = logging.getLogger(__name__)
User = get_user_model()

class AIChatConsumer(AsyncWebsocketConsumer):
    """AI聊天WebSocket消费者"""
    
    async def connect(self):
        # 检查用户认证
        if self.scope["user"].is_anonymous:
            await self.close()
            return
        await self.accept()
        self.user = self.scope["user"]
        logger.info(f"AI聊天WebSocket连接已建立 - 用户: {self.user.username}")
    
    async def disconnect(self, close_code):
        logger.info(f"AI聊天WebSocket连接已断开: {close_code} - 用户: {self.user.username if hasattr(self, 'user') else 'Unknown'}")
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get('message', '')
            if not message:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'text': '消息不能为空'
                }))
                return
            
            def create_url():
                # 使用RFC1123 GMT格式
                date = formatdate(timeval=None, localtime=False, usegmt=True)
                signature_origin = f"host: spark-api.xf-yun.com\ndate: {date}\nGET /v3.1/chat HTTP/1.1"
                signature_sha = hmac.new(
                    settings.XUNFEI_API_SECRET.encode('utf-8'),
                    signature_origin.encode('utf-8'),
                    digestmod=hashlib.sha256
                ).digest()
                signature_sha_base64 = base64.b64encode(signature_sha).decode()
                authorization_origin = f'api_key="{settings.XUNFEI_API_KEY}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
                authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode()
                params = {
                    "authorization": authorization,
                    "date": date,
                    "host": "spark-api.xf-yun.com"
                }
                url = f"wss://spark-api.xf-yun.com/v3.1/chat?{urlencode(params)}"
                return url, date
            
            url, date = create_url()
            logger.info(f"正在连接讯飞API: {url}")
            # WebSocket header必须为列表
            headers = [
                f"Host: spark-api.xf-yun.com",
                f"Date: {date}",
            ]
            ws = websocket.create_connection(url, header=headers, timeout=10)
            logger.info("讯飞API WebSocket连接成功")
            request_data = {
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
                            {"role": "user", "content": message}
                        ]
                    }
                }
            }
            logger.info(f"发送请求数据: {json.dumps(request_data, ensure_ascii=False)}")
            ws.send(json.dumps(request_data))
            while True:
                response = ws.recv()
                logger.info(f"收到响应: {response}")
                response_data = json.loads(response)
                if response_data['header']['code'] != 0:
                    error_msg = response_data.get('payload', {}).get('text', '请求失败')
                    logger.error(f"API错误: {error_msg}")
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'text': error_msg
                    }))
                    break
                if 'payload' in response_data and 'choices' in response_data['payload']:
                    text = response_data['payload']['choices']['text'][0]['content']
                    logger.info(f"AI回复: {text}")
                    await self.send(text_data=json.dumps({
                        'type': 'message',
                        'text': text
                    }))
                else:
                    logger.error(f"响应格式异常: {response_data}")
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'text': '响应格式异常'
                    }))
                    break
                if response_data['header']['status'] == 2:
                    logger.info("对话结束")
                    break
            ws.close()
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': '无效的JSON格式'
            }))
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'text': f'处理消息时出错: {str(e)}'
            })) 