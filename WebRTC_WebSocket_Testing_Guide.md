# WebRTC WebSocket API 测试指南

## 概述

本文档提供了测试WebRTC WebSocket接口的详细指南，包括使用Postman和其他工具进行测试的方法。

## WebSocket连接信息

- **连接地址**: `ws://localhost:8000/ws/webrtc/`
- **协议**: WebSocket
- **认证**: JWT令牌（在连接时通过Authorization头传递）
- **消息格式**: JSON

## 使用Postman测试WebSocket

### 1. 建立WebSocket连接

Postman支持WebSocket连接，但功能相对有限。以下是使用步骤：

#### 步骤1: 创建WebSocket请求
1. 打开Postman
2. 点击"New" → "WebSocket Request"
3. 输入URL: `ws://localhost:8000/ws/webrtc/`
4. 添加Headers:
   ```
   Authorization: Bearer your_jwt_token_here
   ```

#### 步骤2: 连接WebSocket
1. 点击"Connect"按钮建立连接
2. 连接成功后，状态会显示为"Connected"

#### 步骤3: 发送消息
在连接建立后，可以在消息框中发送JSON格式的消息：

```json
{
  "type": "create_stream",
  "title": "测试视频流",
  "description": "这是一个测试"
}
```

### 2. 测试消息类型

#### 创建视频流
```json
{
  "type": "create_stream",
  "title": "我的视频流",
  "description": "这是一个测试视频流"
}
```

**预期响应:**
```json
{
  "type": "stream_created",
  "stream_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "我的视频流",
  "message": "视频流创建成功"
}
```

#### 加入视频流
```json
{
  "type": "join_stream",
  "stream_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**预期响应:**
```json
{
  "type": "stream_joined",
  "stream_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "我的视频流",
  "message": "成功加入视频流"
}
```

#### 发送WebRTC Offer
```json
{
  "type": "offer",
  "offer": {
    "type": "offer",
    "sdp": "v=0\r\no=- 1234567890 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\na=group:BUNDLE 0\r\n..."
  }
}
```

#### 发送WebRTC Answer
```json
{
  "type": "answer",
  "answer": {
    "type": "answer",
    "sdp": "v=0\r\no=- 1234567890 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\na=group:BUNDLE 0\r\n..."
  },
  "target_peer": "peer_123"
}
```

#### 发送ICE候选
```json
{
  "type": "ice_candidate",
  "candidate": {
    "candidate": "candidate:1 1 UDP 2122252543 192.168.1.1 12345 typ host",
    "sdpMLineIndex": 0,
    "sdpMid": "0"
  },
  "target_peer": "peer_123"
}
```

#### 发送视频帧
```json
{
  "type": "video_frame",
  "frame_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
  "frame_type": "keyframe",
  "timestamp": 1640995200000
}
```

#### 断开连接
```json
{
  "type": "disconnect"
}
```

## 使用其他工具测试

### 1. 使用wscat命令行工具

#### 安装wscat
```bash
npm install -g wscat
```

#### 连接WebSocket
```bash
wscat -c "ws://localhost:8000/ws/webrtc/" -H "Authorization: Bearer your_jwt_token_here"
```

#### 发送消息
连接成功后，直接输入JSON消息：
```json
{"type": "create_stream", "title": "测试流", "description": "测试"}
```

### 2. 使用浏览器开发者工具

#### 在浏览器控制台中测试
```javascript
// 建立WebSocket连接
const ws = new WebSocket('ws://localhost:8000/ws/webrtc/');

// 添加认证头（需要在服务器端支持）
ws.onopen = function() {
    console.log('WebSocket连接已建立');
    
    // 发送创建流消息
    ws.send(JSON.stringify({
        type: 'create_stream',
        title: '测试视频流',
        description: '这是一个测试'
    }));
};

ws.onmessage = function(event) {
    console.log('收到消息:', JSON.parse(event.data));
};

ws.onerror = function(error) {
    console.error('WebSocket错误:', error);
};

ws.onclose = function() {
    console.log('WebSocket连接已关闭');
};
```

### 3. 使用Python测试脚本

```python
import websocket
import json
import threading
import time

class WebRTCTester:
    def __init__(self, token):
        self.token = token
        self.ws = None
        
    def on_message(self, ws, message):
        print(f"收到消息: {message}")
        
    def on_error(self, ws, error):
        print(f"错误: {error}")
        
    def on_close(self, ws, close_status_code, close_msg):
        print("连接已关闭")
        
    def on_open(self, ws):
        print("连接已建立")
        
        # 发送创建流消息
        create_stream_msg = {
            "type": "create_stream",
            "title": "Python测试流",
            "description": "使用Python脚本创建的测试流"
        }
        ws.send(json.dumps(create_stream_msg))
        
    def connect(self):
        # 添加认证头
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        
        self.ws = websocket.WebSocketApp(
            "ws://localhost:8000/ws/webrtc/",
            header=headers,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        self.ws.run_forever()
        
    def send_message(self, message):
        if self.ws:
            self.ws.send(json.dumps(message))

# 使用示例
if __name__ == "__main__":
    tester = WebRTCTester("your_jwt_token_here")
    
    # 在后台运行WebSocket连接
    ws_thread = threading.Thread(target=tester.connect)
    ws_thread.daemon = True
    ws_thread.start()
    
    # 等待连接建立
    time.sleep(2)
    
    # 发送测试消息
    test_messages = [
        {
            "type": "join_stream",
            "stream_id": "123e4567-e89b-12d3-a456-426614174000"
        },
        {
            "type": "disconnect"
        }
    ]
    
    for msg in test_messages:
        tester.send_message(msg)
        time.sleep(1)
```

## 测试场景

### 1. 基本连接测试
- 测试WebSocket连接建立
- 验证JWT认证
- 检查连接状态响应

### 2. 视频流管理测试
- 创建视频流
- 加入视频流
- 验证流ID生成
- 测试错误处理（无效流ID）

### 3. WebRTC信令测试
- 发送Offer/Answer
- 发送ICE候选
- 验证信令交换流程

### 4. 视频帧传输测试
- 发送视频帧数据
- 验证帧类型和时间戳
- 测试大数据量传输

### 5. 错误处理测试
- 无效的JSON格式
- 未知的消息类型
- 缺少必要参数
- 认证失败

### 6. 并发测试
- 多客户端同时连接
- 多用户加入同一流
- 连接断开和重连

## 常见问题

### 1. 连接被拒绝
- 检查JWT令牌是否有效
- 确认服务器是否运行
- 验证WebSocket端点是否正确

### 2. 消息发送失败
- 确保WebSocket连接已建立
- 检查JSON格式是否正确
- 验证消息类型是否支持

### 3. 认证失败
- 检查JWT令牌格式
- 确认令牌未过期
- 验证令牌权限

### 4. 响应延迟
- 检查网络连接
- 确认服务器性能
- 验证消息大小

## 性能测试

### 1. 连接数测试
- 测试最大并发连接数
- 监控内存和CPU使用率
- 验证连接稳定性

### 2. 消息吞吐量测试
- 测试每秒消息处理量
- 监控网络带宽使用
- 验证消息延迟

### 3. 视频流质量测试
- 测试不同分辨率的视频帧
- 监控帧率和延迟
- 验证视频质量

## 安全测试

### 1. 认证测试
- 测试无效令牌
- 测试过期令牌
- 测试无令牌连接

### 2. 输入验证测试
- 测试恶意JSON数据
- 测试超大数据包
- 测试特殊字符

### 3. 权限测试
- 测试跨用户访问
- 测试未授权操作
- 测试权限提升

## 总结

WebSocket接口的测试需要特殊的工具和方法。虽然Postman提供了基本的WebSocket支持，但对于复杂的实时通信测试，建议结合使用多种工具：

1. **Postman**: 用于基本连接和消息测试
2. **wscat**: 用于命令行快速测试
3. **浏览器开发者工具**: 用于前端集成测试
4. **Python脚本**: 用于自动化测试和性能测试

通过综合使用这些工具，可以全面测试WebRTC WebSocket接口的功能、性能和安全性。 