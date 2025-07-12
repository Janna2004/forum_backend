# 论坛后端系统

基于Django的论坛后端API，支持用户认证、帖子管理和AI对话功能。

## 功能特性

- 用户注册/登录（JWT认证）
- 帖子增删改查（分页）
- 讯飞大模型AI对话
- WebRTC视频流处理
- MySQL数据库支持

## 安装配置

### 1. 克隆项目

```bash
git clone <repository-url>
cd forum_backend
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置数据库和API密钥

复制配置示例文件：

```bash
cp config/local_settings_example.py config/local_settings.py
```

编辑 `config/local_settings.py`，填入你的配置：

- 数据库连接信息
- 讯飞API密钥
- Django SECRET_KEY

### 4. 数据库迁移

```bash
python manage.py migrate
```

### 5. 启动服务

```bash
python manage.py runserver
```

## API接口

### 用户认证

- `POST /users/register/` - 用户注册
- `POST /users/login/` - 用户登录

### 个人信息管理

- `GET /users/profile/` - 获取个人信息（需JWT）
- `POST /users/profile/update/` - 更新个人信息（需JWT）

### 简历管理

- `GET /users/resume/` - 获取简历详细信息（需JWT）
- `POST /users/resume/create/` - 创建或更新简历基本信息（需JWT）
- `POST /users/resume/work/` - 管理工作经历（需JWT）
- `POST /users/resume/project/` - 管理项目经历（需JWT）
- `POST /users/resume/education/` - 管理教育经历（需JWT）
- `POST /users/resume/custom/` - 管理自定义部分（需JWT）

### 帖子管理

- `POST /posts/create/` - 创建帖子（需JWT）
- `DELETE /posts/delete/{id}/` - 删除帖子（需JWT）
- `POST /posts/update/{id}/` - 更新帖子（需JWT）
- `GET /posts/list/` - 获取帖子列表（分页）
- `GET /posts/detail/{id}/` - 获取帖子详细信息（包含回复）

### 回复管理

- `POST /posts/reply/create/{post_id}/` - 创建回复（需JWT）
- `POST /posts/reply/update/{reply_id}/` - 更新回复（需JWT）
- `DELETE /posts/reply/delete/{reply_id}/` - 删除回复（需JWT）

### AI对话

- `POST /posts/chat/` - 讯飞AI对话（流式响应）

### WebRTC视频流

#### WebSocket连接
- `ws://localhost:8000/ws/webrtc/` - WebRTC WebSocket连接

#### 连接流程详解

**1. 建立WebSocket连接**
```javascript
// 前端建立WebSocket连接
const ws = new WebSocket('ws://localhost:8000/ws/webrtc/');

ws.onopen = function() {
    console.log('WebSocket连接已建立');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('收到消息:', data);
};
```

**2. 创建视频流**
```javascript
// 发送创建流请求
ws.send(JSON.stringify({
    type: 'create_stream',
    title: '我的视频流',
    description: '这是一个测试视频流'
}));

// 服务器响应
// {
//     type: 'stream_created',
//     stream_id: 'uuid',
//     title: '我的视频流',
//     message: '视频流创建成功'
// }
```

**3. 加入视频流**
```javascript
// 加入现有流
ws.send(JSON.stringify({
    type: 'join_stream',
    stream_id: 'stream_uuid'
}));

// 服务器响应
// {
//     type: 'stream_joined',
//     stream_id: 'uuid',
//     title: '我的视频流',
//     message: '成功加入视频流'
// }
```

**4. WebRTC信令交换**
```javascript
// 发送Offer
ws.send(JSON.stringify({
    type: 'offer',
    offer: {
        type: 'offer',
        sdp: '...' // WebRTC SDP offer
    }
}));

// 发送Answer
ws.send(JSON.stringify({
    type: 'answer',
    answer: {
        type: 'answer',
        sdp: '...' // WebRTC SDP answer
    },
    target_peer: 'peer_id'
}));

// 发送ICE候选
ws.send(JSON.stringify({
    type: 'ice_candidate',
    candidate: {
        candidate: '...',
        sdpMLineIndex: 0,
        sdpMid: '0'
    },
    target_peer: 'peer_id'
}));
```

**5. 视频帧传输**
```javascript
// 发送视频帧数据
ws.send(JSON.stringify({
    type: 'video_frame',
    frame_data: 'base64_encoded_frame',
    frame_type: 'keyframe', // 或 'deltaframe'
    timestamp: Date.now()
}));
```

**6. 断开连接**
```javascript
// 主动断开
ws.send(JSON.stringify({
    type: 'disconnect'
}));

// 关闭WebSocket
ws.close();
```

#### 前端完整示例

```javascript
class WebRTCClient {
    constructor() {
        this.ws = null;
        this.peerConnection = null;
        this.localStream = null;
        this.remoteStream = null;
    }

    async connect() {
        // 建立WebSocket连接
        this.ws = new WebSocket('ws://localhost:8000/ws/webrtc/');
        
        this.ws.onopen = () => {
            console.log('WebSocket连接已建立');
        };
        
        this.ws.onmessage = (event) => {
            this.handleMessage(JSON.parse(event.data));
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket连接已关闭');
        };
    }

    async createStream(title, description) {
        this.ws.send(JSON.stringify({
            type: 'create_stream',
            title: title,
            description: description
        }));
    }

    async joinStream(streamId) {
        this.ws.send(JSON.stringify({
            type: 'join_stream',
            stream_id: streamId
        }));
    }

    async startLocalStream() {
        try {
            this.localStream = await navigator.mediaDevices.getUserMedia({
                video: true,
                audio: true
            });
            
            // 创建RTCPeerConnection
            this.peerConnection = new RTCPeerConnection({
                iceServers: [
                    { urls: 'stun:stun.l.google.com:19302' }
                ]
            });
            
            // 添加本地流
            this.localStream.getTracks().forEach(track => {
                this.peerConnection.addTrack(track, this.localStream);
            });
            
            // 处理ICE候选
            this.peerConnection.onicecandidate = (event) => {
                if (event.candidate) {
                    this.ws.send(JSON.stringify({
                        type: 'ice_candidate',
                        candidate: event.candidate,
                        target_peer: 'broadcast' // 广播给所有peer
                    }));
                }
            };
            
            // 处理远程流
            this.peerConnection.ontrack = (event) => {
                this.remoteStream = event.streams[0];
                // 显示远程视频
                const videoElement = document.getElementById('remoteVideo');
                videoElement.srcObject = this.remoteStream;
            };
            
        } catch (error) {
            console.error('获取媒体流失败:', error);
        }
    }

    async createOffer() {
        try {
            const offer = await this.peerConnection.createOffer();
            await this.peerConnection.setLocalDescription(offer);
            
            this.ws.send(JSON.stringify({
                type: 'offer',
                offer: offer
            }));
        } catch (error) {
            console.error('创建Offer失败:', error);
        }
    }

    async handleMessage(data) {
        switch (data.type) {
            case 'connection_established':
                console.log('连接已建立:', data.session_id);
                break;
                
            case 'stream_created':
                console.log('流创建成功:', data.stream_id);
                break;
                
            case 'stream_joined':
                console.log('成功加入流:', data.stream_id);
                break;
                
            case 'offer':
                // 处理收到的Offer
                await this.peerConnection.setRemoteDescription(data.offer);
                const answer = await this.peerConnection.createAnswer();
                await this.peerConnection.setLocalDescription(answer);
                
                this.ws.send(JSON.stringify({
                    type: 'answer',
                    answer: answer,
                    target_peer: data.peer_id
                }));
                break;
                
            case 'answer':
                // 处理收到的Answer
                await this.peerConnection.setRemoteDescription(data.answer);
                break;
                
            case 'ice_candidate':
                // 处理收到的ICE候选
                await this.peerConnection.addIceCandidate(data.candidate);
                break;
                
            case 'error':
                console.error('服务器错误:', data.message);
                break;
        }
    }

    disconnect() {
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
        }
        if (this.peerConnection) {
            this.peerConnection.close();
        }
        if (this.ws) {
            this.ws.close();
        }
    }
}

// 使用示例
const client = new WebRTCClient();
await client.connect();
await client.startLocalStream();
await client.createStream('测试视频流', '这是一个测试');
await client.createOffer();
```

#### 技术架构说明

**后端架构：**
- **Django Channels**: 提供WebSocket支持，处理实时通信
- **WebRTC Consumer**: 管理WebSocket连接和消息路由
- **视频流模型**: 存储流信息和连接状态
- **信令服务器**: 处理WebRTC的Offer/Answer/ICE候选交换

**数据流向：**
1. 前端通过WebSocket连接到后端信令服务器
2. 创建或加入视频流，建立会话
3. 通过信令服务器交换WebRTC连接参数
4. 建立P2P连接后，视频数据直接在peer间传输
5. 后端记录连接状态和统计信息

**安全考虑：**
- WebSocket连接需要用户认证
- 视频流创建和加入需要权限验证
- 连接状态实时监控和异常处理

#### 注意事项

1. **浏览器兼容性**: 确保浏览器支持WebRTC API
2. **HTTPS要求**: 生产环境需要HTTPS才能使用getUserMedia
3. **STUN/TURN服务器**: 建议配置自己的STUN/TURN服务器以提高连接成功率
4. **带宽管理**: 视频质量需要根据网络状况动态调整
5. **错误处理**: 实现完善的错误处理和重连机制

## 环境要求

- Python 3.8+
- Django 5.2+
- MySQL 5.7+
- PyJWT
- websocket-client
- aiortc (WebRTC支持)
- opencv-python (视频处理)
- channels (WebSocket支持)

### 使用方法

1. **启动服务器**：

   ```bash
   python manage.py runserver
   ```
2. **WebSocket端点**：

   - `ws://localhost:8000/ws/webrtc/` - WebRTC WebSocket连接
3. **WebSocket消息格式**：

   ```json
   // 创建流
   {"type": "create_stream", "title": "标题", "description": "描述"}

   // 加入流
   {"type": "join_stream", "stream_id": "uuid"}

   // WebRTC Offer/Answer
   {"type": "offer", "offer": {...}}
   ```

## 安全说明

- 敏感配置信息存储在 `config/local_settings.py` 中
- 该文件已被 `.gitignore` 忽略，不会提交到版本控制
- 生产环境请使用强随机SECRET_KEY
- 定期更新API密钥和数据库密码
