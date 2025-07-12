# WebRTC WebSocket 前端对接指南

## 概述

本文档介绍前端如何通过WebSocket连接后端，实现实时面试视频传输功能。

## 连接信息

- **WebSocket地址**: `ws://localhost:8000/ws/webrtc/`
- **协议**: WebSocket
- **消息格式**: JSON

## 前端对接流程

### 1. 建立WebSocket连接

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/webrtc/');

ws.onopen = function() {
    console.log('WebSocket连接已建立');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('收到消息:', data);
};
```

### 2. 创建视频流会话

连接成功后，发送创建流消息：

```javascript
ws.send(JSON.stringify({
    type: 'create_stream',
    title: '面试视频流',
    description: '实时面试'
}));
```

### 3. 传输视频流

前端通过WebRTC获取摄像头和麦克风权限，将视频流数据发送到后端：

```javascript
// 获取媒体流（包含音频和视频）
navigator.mediaDevices.getUserMedia({
    video: true,
    audio: true
}).then(stream => {
    // 将视频流数据发送到后端
    // 这里需要将MediaStream转换为可传输的格式
});
```

### 4. 接收后端消息

后端可能会发送面试题目、代码题等：

```javascript
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.type === 'interview_question') {
        // 显示面试题目
        displayQuestion(data.question);
    } else if (data.type === 'code_challenge') {
        // 显示代码题
        displayCodeChallenge(data.challenge);
    }
};
```

### 5. 结束会话

前端可以主动结束视频流：

```javascript
ws.send(JSON.stringify({
    type: 'disconnect'
}));

ws.close();
```

## 消息类型说明

### 前端发送的消息
- `create_stream`: 创建视频流会话
- `video_frame`: 发送视频帧数据
- `audio_data`: 发送音频数据
- `disconnect`: 结束会话

### 后端发送的消息
- `stream_created`: 流创建成功确认
- `interview_question`: 面试题目
- `code_challenge`: 代码挑战题
- `connection_closed`: 连接关闭确认

## 注意事项

1. 确保浏览器支持WebRTC和WebSocket
2. 需要用户授权摄像头和麦克风权限
3. 视频流数据量较大，注意网络带宽
4. 建议实现断线重连机制
5. 生产环境使用HTTPS和WSS协议 