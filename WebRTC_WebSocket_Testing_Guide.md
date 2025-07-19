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

#### 3. 视频帧（人脸/作弊检测）

```json
{
  "type": "video_frame",
  "frame_data": "<base64编码的JPEG图片>",
  "frame_type": "keyframe" // 可选，默认为keyframe
}
```

- 建议每隔1秒推送一帧视频（可用canvas截图），frame_data为base64字符串，frame_type一般为"keyframe"。
- 用于后端人脸检测、人数检测、作弊检测等。
- 示例JS：
```js
canvas.toBlob(blob => {
  const reader = new FileReader();
  reader.onloadend = function() {
    const base64data = reader.result.split(',')[1];
    ws.send(JSON.stringify({type: 'video_frame', frame_data: base64data, frame_type: 'keyframe'}));
  };
  reader.readAsDataURL(blob);
}, 'image/jpeg', 0.8);
```

#### 4. WebRTC 信令/视频帧（如需）

- `offer`、`answer`、`ice_candidate`、`video_frame` 等，详见下方“信令消息”小节。

#### 5. 主动断开

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
  "text": "<面试官语句或问题内容>"
}
```

- `phase`：当前面试阶段。`intro`=自我介绍，`question`=问答，`code`=代码题。
- `text`：面试官提示语或问题内容。前端应根据此内容切换UI、自动开启/关闭语音识别等。

#### 2. 语音转写结果

```json
{
  "type": "asr_result",
  "text": "<实时转写文本>"
}
```

- `text` 字段为后端实时识别到的中文文本，前端可实时显示。

#### 3. 视频流帧广播

```json
{
  "type": "video_frame",
  "frame_data": "<base64编码的JPEG图片>",
  "frame_type": "keyframe",
  "peer_id": "<发送者id>"
}
```

- 后端可将某用户推送的视频帧广播给其他观看者。

#### 4. 连接建立确认

```json
{
  "type": "connection_established",
  "session_id": "<会话ID>",
  "text": "WebRTC连接已建立"
}
```

#### 5. 错误/提示

```json
{
  "type": "error",
  "text": "<错误描述>"
}
```

#### 6. WebRTC 信令/视频帧

- `offer`、`answer`、`ice_candidate`、`video_frame`、`stream_created` 等，结构与前端发送类似。

#### 7. 作弊检测信号

```json
{
  "type": "cheat_detected",
  "text": "检测到多个人，疑似作弊！"
}
```

- 前端收到此消息后应高亮提示用户或自动上报。

---

## 3. 典型消息流程

1. 前端连接 ws，收到 `connection_established`。
2. 收到 `interview_message`（phase: intro, text: “请开始自我介绍吧”），前端自动开启语音识别。
3. 用户自我介绍，前端持续推送 `audio_frame`，后端持续推送 `asr_result`。
4. 15秒无语音或识别到“说完了”，后端推送 `interview_message`（phase: question, text: “自我介绍结束，下面开始问问题。”），紧接着推送第一个问题。
5. 问题阶段循环，直到问题队列为空，后端推送 `interview_message`（phase: code, text: “问答环节结束，下面进入代码题环节。”）。
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
4. **推送视频帧**：建议每1秒推送一帧，frame_data为base64编码JPEG，frame_type为keyframe。
5. **信令与视频帧**：WebRTC信令和视频帧消息需与前端WebRTC SDK配合。

---

## 6. 注意事项

1. 确保浏览器支持WebRTC和WebSocket。
2. 需要用户授权摄像头和麦克风权限。
3. 音频帧务必为16kHz单声道16位小端PCM，帧长1280字节，base64编码。
4. 视频帧建议为480x360或640x480 JPEG，base64编码。
5. 建议实现断线重连机制。
6. 生产环境使用HTTPS和WSS协议。
7. 问题队列、面试阶段等由后端自动控制，前端只需根据ws消息切换UI和控制语音识别。

---

如需更多细节或前端代码示例，请查阅源码或联系后端开发。
