# FFmpeg 安装指南

## 问题描述

面试系统在保存答案时需要合成音视频文件，这需要FFmpeg工具。如果系统找不到FFmpeg，会出现以下错误：

```
FileNotFoundError: [WinError 2] 系统找不到指定的文件。
```

## 解决方案

### 方案1：安装FFmpeg（推荐）

#### Windows 安装方法：

1. **下载FFmpeg**
   - 访问 https://ffmpeg.org/download.html
   - 点击 "Windows Builds" 链接
   - 下载 "Windows builds from gyan.dev" 或 "Windows builds by BtbN"

2. **解压并配置环境变量**
   ```bash
   # 解压到 C:\ffmpeg
   # 将 C:\ffmpeg\bin 添加到系统PATH环境变量
   ```

3. **验证安装**
   ```bash
   ffmpeg -version
   ```

#### 使用包管理器安装：

**使用 Chocolatey:**
```bash
choco install ffmpeg
```

**使用 Scoop:**
```bash
scoop install ffmpeg
```

### 方案2：跳过音视频合成（临时方案）

如果暂时不想安装FFmpeg，系统会自动降级处理：

1. **只保存音频文件** (.wav格式)
2. **只保存图片文件** (第一帧作为代表)
3. **答案记录正常保存**到数据库

## 系统兼容性

修复后的系统具有以下特性：

- ✅ **自动检测FFmpeg可用性**
- ✅ **优雅降级处理**（无FFmpeg时保存音频/图片）
- ✅ **错误隔离**（音视频失败不影响答案保存）
- ✅ **详细日志输出**（便于调试）

## 验证修复

修复后，即使没有FFmpeg，您应该看到：

```
[警告] ffmpeg未安装或不在PATH中，跳过音视频合成
[调试] 音视频保存成功: ./interview_clips/xxx_q1.wav
[调试] 已创建答案记录并加入分析队列 - id: xxx, av_path: ./interview_clips/xxx_q1.wav
```

而不是之前的错误信息。

## 注意事项

1. **音视频合成是可选的**：不影响面试答案的保存和分析
2. **音频文件仍然可用**：用于语音识别和AI分析
3. **图片文件作为备选**：当只有视频帧时，保存第一帧作为代表
4. **性能影响**：无FFmpeg时性能更好，因为跳过了视频合成步骤
