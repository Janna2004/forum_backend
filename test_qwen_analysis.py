#!/usr/bin/env python
"""
测试qwen-omni API的音视频分析功能
"""

import os
import sys
import django
import base64
from openai import OpenAI

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 设置Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 初始化Django
django.setup()

from django.conf import settings

def test_qwen_with_av():
    """测试qwen-omni API是否能正确处理音视频文件"""
    
    # 查找一个音视频文件进行测试，优先选择视频文件
    interview_clips_dir = './interview_clips'
    test_files = []
    
    if os.path.exists(interview_clips_dir):
        # 优先查找视频文件
        for file in os.listdir(interview_clips_dir):
            if file.endswith('.mp4') and os.path.isfile(os.path.join(interview_clips_dir, file)):
                test_files.append(os.path.join(interview_clips_dir, file))
        
        # 如果没有视频文件，查找音频文件
        if not test_files:
            for file in os.listdir(interview_clips_dir):
                if file.endswith('.wav') and os.path.isfile(os.path.join(interview_clips_dir, file)):
                    test_files.append(os.path.join(interview_clips_dir, file))
    
    if not test_files:
        print("未找到测试用的音视频文件")
        return
    
    test_file = test_files[0]  # 使用第一个找到的文件
    print(f"使用测试文件: {test_file}")
    
    # 如果是音频文件，说明qwen-omni不支持，跳过测试
    if test_file.endswith('.wav'):
        print("⚠️ 检测到音频文件(.wav)，qwen-omni API不支持音频文件的多模态分析")
        print("音频文件仅用于ASR转写，然后进行纯文本分析")
        return
    
    # 构建测试提示
    prompt = """请分析这个面试回答的音视频，评估回答者的信心和表达流畅度，按1-5分打分：

1分：极度缺乏信心，表达极不流畅，长时间停顿或语无伦次
2分：信心不足，表达有明显卡顿或多次重复、犹豫
3分：信心一般，表达基本流畅但偶有停顿或语气不坚定
4分：信心较强，表达流畅，偶有小瑕疵
5分：非常有信心，表达极其流畅，思路清晰、语气坚定

请输出分析理由和分数。"""
    
    try:
        client = OpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        
        # 构建消息内容
        content = [{"type": "text", "text": prompt}]
        
        # 添加视频文件
        print(f"正在读取视频文件: {test_file}")
        with open(test_file, "rb") as f:
            video_bytes = f.read()
        video_b64 = base64.b64encode(video_bytes).decode('utf-8')
        
        content.append({
            "type": "video_url",
            "video_url": {
                "url": f"data:video/mp4;base64,{video_b64}"
            }
        })
        
        print("正在调用qwen-omni API...")
        completion = client.chat.completions.create(
            model="qwen2.5-omni-7b",
            messages=[{"role": "user", "content": content}],
            stream=True
        )
        
        # 处理流式响应
        full_response = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
        
        print("qwen-omni API响应:")
        print(full_response)
        
        if full_response.strip():
            print("✅ qwen-omni API成功返回分析结果")
        else:
            print("❌ qwen-omni API返回空结果")
            
    except Exception as e:
        print(f"❌ 调用qwen-omni API失败: {e}")
        import traceback
        traceback.print_exc()

def test_qwen_text_only():
    """测试qwen-omni API的纯文本分析功能"""
    
    prompt = """请分析这个面试回答，评估回答者的专业知识水平，按1-5分打分：

面试问题：请介绍一下你的技术栈
应答内容：我主要使用Python和JavaScript进行开发，熟悉Django和React框架，有3年的开发经验。

请输出分析理由和分数。"""
    
    try:
        client = OpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        
        content = [{"type": "text", "text": prompt}]
        
        print("正在调用qwen-omni API（纯文本）...")
        completion = client.chat.completions.create(
            model="qwen2.5-omni-7b",
            messages=[{"role": "user", "content": content}],
            stream=True
        )
        
        # 处理流式响应
        full_response = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
        
        print("qwen-omni API响应（纯文本）:")
        print(full_response)
        
        if full_response.strip():
            print("✅ qwen-omni API纯文本分析成功")
        else:
            print("❌ qwen-omni API纯文本分析返回空结果")
            
    except Exception as e:
        print(f"❌ 调用qwen-omni API失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=== 测试qwen-omni API功能 ===")
    print()
    
    print("1. 测试纯文本分析...")
    test_qwen_text_only()
    print()
    
    print("2. 测试音视频分析...")
    test_qwen_with_av()
    print()
    
    print("=== 测试完成 ===")
