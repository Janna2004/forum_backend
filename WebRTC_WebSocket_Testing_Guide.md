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

### 2.5 代码题环节相关消息（新增）

#### 1. 后端推送代码题

```json
{
  "type": "coding_problem",
  "phase": "code",
  "problem": {
    "id": 1,
    "number": "LC001",
    "title": "两数之和",
    "description": "给定一个整数数组...",
    "difficulty": "easy",
    "tags": ["数组", "哈希表"],
    "example": {
      "input": "nums = [2,7,11,15], target = 9",
      "output": "[0,1]",
      "explanation": "因为 nums[0] + nums[1] == 9 ，返回 [0, 1] 。"
    }
  }
}
```
- `phase` 固定为 `code`。
- `problem` 字段为当前代码题，包含题号、标题、描述、难度、标签、首个样例。

#### 2. 前端提交代码答案

```json
{
  "type": "submit_coding_answer",
  "code": "def twoSum(nums, target): ...",  // 用户代码
  "language": "python"  // 语言，可选：python/java/cpp/javascript
}
```

#### 3. 后端返回代码提交确认

```json
{
  "type": "coding_answer_submitted",
  "text": "代码已提交成功"
}
```

#### 4. 前端请求下一道代码题

```json
{
  "type": "request_next_coding_problem"
}
```

- 后端会推送下一道 `coding_problem`，若无更多题目则推送：

```json
{
  "type": "interview_message",
  "phase": "code",
  "text": "代码题环节结束。面试完毕！"
}
```

#### 7. 面试结束消息

```json
{
  "type": "interview_finished",
  "text": "面试已结束，感谢您的参与！我们会尽快给出面试评价。祝您求职顺利！"
}
```

- 当面试全部环节（自我介绍、问答、代码题）完成后，后端会发送此消息。
- 前端收到此消息后应显示结束提示，并关闭WebSocket连接。
- 面试评价（包括问题回答分析、语音语调分析等）会异步进行，不会阻塞面试流程。

---

## 3. 典型消息流程（含代码题）

1. 前端调用 `/users/resume/list/` 获取用户简历列表，让用户选择使用的简历。
2. 前端调用 `/interviews/create/` 创建面试，获取面试ID。
3. 前端连接 WebSocket，收到 `connection_established`。
4. 前端发送 `create_stream` 消息（带上面试ID和简历ID），收到 `stream_created` 响应。
5. 收到 `interview_message`（phase: intro, text: "请开始自我介绍吧"），前端自动开启语音识别。
6. 用户自我介绍，前端持续推送 `audio_frame` 和 `video_frame`，后端持续推送 `asr_result`。
7. 15秒无语音或识别到"说完了"，后端推送 `interview_message`（phase: question, text: "自我介绍结束，下面开始问问题。"），紧接着推送第一个问题。
8. 问题阶段循环，直到问题队列为空，后端推送 `interview_message`（phase: code, text: "问答环节结束，下面进入代码题环节。"）。
9. **代码题阶段**：
    - 后端推送 `coding_problem`，前端显示题目、样例、代码编辑区。
    - 前端填写代码，点击提交，发送 `submit_coding_answer`。
    - 后端返回 `coding_answer_submitted`。
    - 前端可点击"下一题"发送 `request_next_coding_problem`，后端继续推送下一道 `coding_problem`。
    - 所有题目完成后，后端推送 `interview_message`（phase: code, text: "代码题环节结束。"）。
10. **面试结束**：
    - 后端推送 `interview_finished` 消息。
    - 前端显示结束提示，关闭WebSocket连接。
    - 后端异步处理面试评价（问题分析、语音分析等）。

---

## 4. 前端对接建议（补充）

- 监听 `coding_problem` 消息，弹出代码题UI，显示题目、描述、样例。
- 用户填写代码后，点击“提交代码”按钮，发送 `submit_coding_answer`。
- 收到 `coding_answer_submitted` 后可提示“提交成功”，并允许用户点击“下一题”按钮。
- 点击“下一题”发送 `request_next_coding_problem`，收到新题后刷新UI。
- 若收到 `interview_message` 且 phase 为 `code` 且 text 包含“结束”，则隐藏代码题UI，显示面试结束提示。

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

## 5. 注意事项（补充）

- 代码题数量通常为1-3道，由后端根据岗位和简历智能分配。
- 每道题只推送首个样例，前端可显示“样例输入/输出/解释”。
- 支持多语言（python/java/cpp/javascript），前端可提供下拉选择。
- 代码答案和题目顺序会被后端记录。
- 代码题环节期间，`audio_frame`/`video_frame`消息可继续推送（如需同步音视频）。

---

如需更多细节或前端代码示例，请查阅源码或联系后端开发。
