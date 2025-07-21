# WebRTC 面试流程 WebSocket 对接指南

## 概述

本指南详细说明前端如何通过 WebSocket 对接后端，实现面试全流程（自我介绍、问答、代码题）实时音视频与语音转写。

---

## 1. 面试流程

### 1.1 获取用户简历列表

在创建面试前，需要先获取用户的简历列表，让用户选择使用哪份简历进行面试：

```http
GET /users/resume/list/
Authorization: Bearer <token>
```

响应：
```json
{
    "success": true,
    "resumes": [
        {
            "resume_id": 1,
            "resume_name": "后端开发简历",
            "expected_position": "后端工程师",
            "updated_at": "2024-01-01T12:00:00Z",
            "completed": true
        },
        {
            "resume_id": 2,
            "resume_name": "全栈开发简历",
            "expected_position": "全栈工程师", 
            "updated_at": "2024-01-02T10:30:00Z",
            "completed": false
        }
    ],
    "total": 2
}
```

### 1.2 创建面试

在建立 WebSocket 连接前，需要先创建面试：

```http
POST /interviews/create/
Authorization: Bearer <token>
Content-Type: application/json

{
    "position_name": "后端开发工程师",
    "position_type": "backend",
    "company_name": "示例公司",  // 可选
    "position_description": "负责后端开发工作",
    "position_requirements": "熟悉Python/Django",  // 可选
    "interview_time": "2024-03-20T14:30:00Z"  // 可选，默认为当前时间
}
```

响应：
```json
{
    "id": "123",  // 面试ID
    "interview_time": "2024-03-20T14:30:00Z",
    "position_name": "后端开发工程师",
    "company_name": "示例公司",
    "position_type": "backend",
    "msg": "面试创建成功"
}
```

### 1.3 WebSocket 连接信息

- **地址**：`ws://<服务器地址>:8000/ws/webrtc/`
  - 本地开发示例：`ws://localhost:8000/ws/webrtc/`
- **认证**：URL参数传递token，例如：`ws://localhost:8000/ws/webrtc/?token=<your_token>`
- **协议**：WebSocket，消息体为 JSON

---

## 2. 消息类型与格式

### 2.1 前端发送消息

#### 1. 创建视频流会话

```json
{
  "type": "create_stream",
  "title": "面试视频流",
  "description": "实时面试",
  "interview_id": "123",  // 必填，从创建面试接口获得的ID
  "resume_id": "1"        // 必填，用户选择的简历ID
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

#### 4. 主动断开

```json
{
  "type": "disconnect"
}
```

---

### 2.2 后端发送消息

#### 1. 连接建立确认

```json
{
  "type": "connection_established",
  "session_id": "<会话ID>",
  "text": "WebRTC连接已建立"
}
```

#### 2. 流创建成功

```json
{
  "type": "stream_created",
  "stream_id": "<流ID>",
  "title": "测试流",
  "interview_id": "123",
  "text": "视频流创建成功"
}
```

#### 3. 面试流程控制消息

```json
{
  "type": "interview_message",
  "phase": "intro" | "question" | "code",
  "text": "<面试官语句或问题内容>"
}
```

- `phase`：当前面试阶段。`intro`=自我介绍，`question`=问答，`code`=代码题。
- `text`：面试官提示语或问题内容。前端应根据此内容切换UI、自动开启/关闭语音识别等。

#### 4. 语音转写结果

```json
{
  "type": "asr_result",
  "text": "<实时转写文本>"
}
```

- `text` 字段为后端实时识别到的中文文本，前端可实时显示。

#### 5. 作弊检测信号

```json
{
  "type": "cheat_detected",
  "text": "检测到多个人，疑似作弊！"
}
```

- 前端收到此消息后应高亮提示用户或自动上报。

#### 6. 错误/提示

```json
{
  "type": "error",
  "text": "<错误描述>"
}
```

---

## 3. 典型消息流程

1. 前端调用 `/users/resume/list/` 获取用户简历列表，让用户选择使用的简历。
2. 前端调用 `/interviews/create/` 创建面试，获取面试ID。
3. 前端连接 WebSocket，收到 `connection_established`。
4. 前端发送 `create_stream` 消息（带上面试ID和简历ID），收到 `stream_created` 响应。
5. 收到 `interview_message`（phase: intro, text: "请开始自我介绍吧"），前端自动开启语音识别。
6. 用户自我介绍，前端持续推送 `audio_frame` 和 `video_frame`，后端持续推送 `asr_result`。
7. 15秒无语音或识别到"说完了"，后端推送 `interview_message`（phase: question, text: "自我介绍结束，下面开始问问题。"），紧接着推送第一个问题。
8. 问题阶段循环，直到问题队列为空，后端推送 `interview_message`（phase: code, text: "问答环节结束，下面进入代码题环节。"）。
9. 代码题阶段（后端可继续推送相关消息，暂未实现）。

---

## 4. 前端对接建议

1. **获取简历列表**：
   - 调用 `/users/resume/list/` 接口获取用户的所有简历
   - 让用户选择使用哪份简历进行面试
2. **创建面试**：
   - 调用 `/interviews/create/` 接口创建面试
   - 保存返回的面试ID，后续WebSocket连接需要用到
3. **WebSocket连接**：
   - 连接时在URL中带上token参数
   - 连接成功后发送 `create_stream` 消息，必须带上面试ID和简历ID
4. **面试流程**：
   - 监听 `interview_message`，根据 `phase` 字段切换UI和控制语音识别
   - 实时显示 `asr_result` 中的转写内容
   - 每40ms推送一帧音频，每1秒推送一帧视频
5. **错误处理**：
   - 监听 `error` 和 `cheat_detected` 消息
   - 实现断线重连机制

---

## 5. 注意事项

1. 确保浏览器支持WebRTC和WebSocket。
2. 需要用户授权摄像头和麦克风权限。
3. 音频帧务必为16kHz单声道16位小端PCM，帧长1280字节，base64编码。
4. 视频帧建议为480x360或640x480 JPEG，base64编码。
5. 生产环境使用HTTPS和WSS协议。
6. 问题队列、面试阶段等由后端自动控制，前端只需根据ws消息切换UI和控制语音识别。
7. **多简历支持**：用户可以创建多份简历，面试时必须选择使用的简历ID传递给后端，后端会根据选择的简历生成个性化面试问题。
8. 创建面试时的position_type必须是以下之一：
   - backend：后端开发
   - frontend：前端开发
   - pm：产品经理
   - qa：测试
   - algo：算法

---

如需更多细节或前端代码示例，请查阅源码或联系后端开发。
