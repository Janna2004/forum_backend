import json
from channels.generic.websocket import AsyncWebsocketConsumer

class SimpleWebSocketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("[SimpleConsumer] 连接请求到达")
        await self.accept()
        print("[SimpleConsumer] 连接已接受")
        await self.send(text_data=json.dumps({
            'type': 'connection_success',
            'message': '简单WebSocket连接成功！'
        }))

    async def disconnect(self, close_code):
        print(f"[SimpleConsumer] 连接断开，代码: {close_code}")

    async def receive(self, text_data):
        print(f"[SimpleConsumer] 收到消息: {text_data}")
        await self.send(text_data=json.dumps({
            'type': 'echo',
            'message': f'收到: {text_data}'
        })) 