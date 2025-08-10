# ffmpeg 与 ASR 冲突问题解决方案

## 问题描述

在启用 ffmpeg 音视频合成功能后，讯飞 RTASR（实时语音识别）服务出现 `Client idle timeout` 错误，导致 ASR 连接中断。

## 问题原因

1. **阻塞操作**：ffmpeg 音视频合成是 CPU 密集型操作，需要 20-30 秒处理时间
2. **事件循环阻塞**：在主事件循环中执行 ffmpeg 操作，阻塞了 WebSocket 消息处理
3. **ASR 超时**：讯飞 RTASR 服务在客户端空闲超时后主动断开连接
4. **资源竞争**：ffmpeg 处理占用大量系统资源，影响 ASR 连接稳定性

## 解决方案

### 1. 异步处理架构

将音视频处理从主事件循环中分离，使用异步任务处理：

```python
# 修改前：同步处理，阻塞主线程
av_path = await self.save_av_clip_for_question()

# 修改后：异步处理，不阻塞主线程
asyncio.create_task(self._async_save_av_clip(answer.id))
```

### 2. 线程池处理

使用 `ThreadPoolExecutor` 在线程池中处理 CPU 密集型的 ffmpeg 操作：

```python
async def _async_save_av_clip(self, answer_id):
    # 使用线程池处理音视频合成，避免阻塞事件循环
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        av_path = await loop.run_in_executor(executor, self._sync_save_av_clip)
```

### 3. 分阶段处理

将答案保存和分析任务分为两个阶段：

1. **第一阶段**：立即保存答案记录，创建分析任务（不依赖音视频）
2. **第二阶段**：异步处理音视频，完成后重新触发分析任务

```python
# 第一阶段：立即保存答案
answer = await database_sync_to_async(InterviewAnswer.objects.create)(...)

# 第二阶段：异步处理音视频
asyncio.create_task(self._async_save_av_clip(answer.id))
```

### 4. 错误处理和容错

- 音视频处理失败不影响核心功能
- 提供多种降级方案（音频、图片、无媒体）
- 完善的异常捕获和日志记录

## 技术要点

### 1. 事件循环分离

```python
# 主事件循环：处理 WebSocket 消息和 ASR
async def save_current_answer(self):
    # 立即保存答案，不等待音视频处理
    answer = await database_sync_to_async(InterviewAnswer.objects.create)(...)
    
    # 异步处理音视频
    asyncio.create_task(self._async_save_av_clip(answer.id))

# 线程池：处理 CPU 密集型操作
def _sync_save_av_clip(self):
    # ffmpeg 音视频合成
    ffmpeg.output(...).run()
```

### 2. 资源管理

- 使用 `ThreadPoolExecutor` 管理线程资源
- 自动清理临时文件
- 内存缓冲区管理

### 3. 状态同步

- 答案记录立即保存到数据库
- 音视频路径后续更新
- 分析任务分两次触发（无媒体 + 有媒体）

## 效果

1. **ASR 连接稳定**：不再出现 idle timeout 错误
2. **响应速度提升**：答案保存立即完成，用户体验改善
3. **系统稳定性**：音视频处理失败不影响核心功能
4. **资源利用优化**：CPU 密集型操作在独立线程中执行

## 注意事项

1. **内存管理**：及时清理音视频缓冲区
2. **磁盘空间**：监控临时文件占用
3. **并发控制**：避免同时处理多个音视频任务
4. **错误恢复**：提供多种降级方案

## 相关文件

- `webrtc/consumers.py`：主要修改文件
- `interviews/models.py`：数据模型
- `interviews/tasks.py`：Celery 任务
- `ffmpeg_installation_guide.md`：ffmpeg 安装指南
