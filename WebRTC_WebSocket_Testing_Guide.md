# WebRTC 面试流程 WebSocket 对接指南

## 概述
本指南详细说明前端如何通过 WebSocket 对接后端，实现面试全流程（自我介绍、问答、代码题）实时音视频与语音转写。

---

## 1. WebSocket 连接信息
- **地址**：`ws://<服务器地址>:8000/ws/webrtc/`
  - 本地开发示例：`ws://localhost:8000/ws/webrtc/`
- **协议**：WebSocket，消息体为 JSON

---

## 2. 消息类型与格式

### 2.1 前端发送消息

#### 1. 创建视频流会话
```json
{
  "type": "create_stream",
  "title": "面试视频流",
  "description": "实时面试"
}
```

#### 2. 音频帧（语音识别）
```json
{
  "type": "audio_frame",
  "audio_data": "<base64编码的16kHz单声道16位小端PCM音频数据>",
  "end": false // 可选，结束时为true
}
```
- 每40ms推送1280字节（640采样点）音频帧，停止时发送一次 `{ "type": "audio_frame", "audio_data": "", "end": true }`

#### 3. WebRTC 信令/视频帧（如需）
- `offer`、`answer`、`ice_candidate`、`video_frame` 等，详见下方“信令消息”小节。

#### 4. 主动断开
```json
{
  "type": "disconnect"
}
```

---

### 2.2 后端发送消息

#### 1. 面试流程控制消息
```json
{
  "type": "interview_message",
  "phase": "intro" | "question" | "code",
  "message": "<面试官语句或问题内容>"
}
```
- `phase`：当前面试阶段。`intro`=自我介绍，`question`=问答，`code`=代码题。
- `message`：面试官提示语或问题内容。前端应根据此内容切换UI、自动开启/关闭语音识别等。

#### 2. 语音转写结果
```json
{
  "type": "asr_result",
  "text": "<实时转写文本>"
}
```
- `text` 字段为后端实时识别到的中文文本，前端可实时显示。

#### 3. 连接建立确认
```json
{
  "type": "connection_established",
  "session_id": "<会话ID>",
  "message": "WebRTC连接已建立"
}
```

#### 4. 错误/提示
```json
{
  "type": "error",
  "message": "<错误描述>"
}
```

#### 5. WebRTC 信令/视频帧
- `offer`、`answer`、`ice_candidate`、`video_frame`、`stream_created` 等，结构与前端发送类似。

---

## 3. 典型消息流程

1. 前端连接 ws，收到 `connection_established`。
2. 收到 `interview_message`（phase: intro, message: “请开始自我介绍吧”），前端自动开启语音识别。
3. 用户自我介绍，前端持续推送 `audio_frame`，后端持续推送 `asr_result`。
4. 15秒无语音或识别到“说完了”，后端推送 `interview_message`（phase: question, message: “自我介绍结束，下面开始问问题。”），紧接着推送第一个问题。
5. 问题阶段循环，直到问题队列为空，后端推送 `interview_message`（phase: code, message: “问答环节结束，下面进入代码题环节。”）。
6. 代码题阶段（后端可继续推送相关消息，暂未实现）。

---

## 4. 信令与视频帧消息（WebRTC相关）

- `offer`、`answer`、`ice_candidate`、`video_frame` 消息结构：
```json
{
  "type": "offer" | "answer" | "ice_candidate" | "video_frame",
  // 具体字段见webrtc/consumers.py
}
```
- 这些消息用于WebRTC信令交换和视频帧转发，通常由前端WebRTC SDK自动处理。

---

## 5. 前端对接建议

1. **连接建立后**，监听 `interview_message`，根据 `phase` 字段切换UI和控制语音识别：
   - `intro` 阶段：收到“请开始自我介绍吧”后自动开启语音识别，用户说完或15秒无语音自动进入下阶段。
   - `question` 阶段：每收到一个问题自动开启语音识别，用户说完或15秒无语音自动进入下一个问题。
   - `code` 阶段：收到“问答环节结束，下面进入代码题环节。”后可切换到代码题UI。
2. **实时显示转写内容**：监听 `asr_result`，将 `text` 实时显示在页面上。
3. **推送音频帧**：采集音频后每40ms推送一帧，停止时发送 `end: true`。
4. **信令与视频帧**：WebRTC信令和视频帧消息需与前端WebRTC SDK配合。

---

## 6. 注意事项

1. 确保浏览器支持WebRTC和WebSocket。
2. 需要用户授权摄像头和麦克风权限。
3. 音频帧务必为16kHz单声道16位小端PCM，帧长1280字节，base64编码。
4. 建议实现断线重连机制。
5. 生产环境使用HTTPS和WSS协议。
6. 问题队列、面试阶段等由后端自动控制，前端只需根据ws消息切换UI和控制语音识别。

---

如需更多细节或前端代码示例，请查阅源码或联系后端开发。 