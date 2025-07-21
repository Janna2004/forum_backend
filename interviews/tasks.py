from celery import shared_task
from django.conf import settings
import base64
from openai import OpenAI
from .models import InterviewAnswer
from .services import XunfeiASRService
import traceback
import os
import time

@shared_task(name='interviews.analyze_interview_answer')
def analyze_interview_answer(answer_id, av_path=None):
    """异步分析面试回答"""
    print(f"[调试] 开始处理面试回答分析任务 - answer_id: {answer_id}")
    try:
        # 获取面试答案记录
        answer = InterviewAnswer.objects.get(id=answer_id)
        print(f"[调试] 成功获取答案记录 - answer_id: {answer_id}")
        
        # 如果有音频文件，先进行转写
        if av_path and os.path.exists(av_path):
            print(f"[调试] 开始处理音频文件 - answer_id: {answer_id}")
            asr_service = XunfeiASRService(av_path)
            transcribed_text = asr_service.get_result()
            if transcribed_text:
                print(f"[调试] 音频转写成功 - answer_id: {answer_id}")
                answer.answer = transcribed_text
                answer.save()
            else:
                print(f"[调试] 音频转写失败 - answer_id: {answer_id}")
        
        # 使用原来的分析流程
        prompt = f"请根据以下面试问题和应答，判断应答者在回答时的信心和表达流畅度，并按如下标准打1-5分：\\n1分：极度缺乏信心，表达极不流畅，长时间停顿或语无伦次。\\n2分：信心不足，表达有明显卡顿或多次重复、犹豫。\\n3分：信心一般，表达基本流畅但偶有停顿或语气不坚定。\\n4分：信心较强，表达流畅，偶有小瑕疵。\\n5分：非常有信心，表达极其流畅，思路清晰、语气坚定。\\n请输出分析理由和分数。\\n\\n面试问题：{answer.question}\\n应答内容：{answer.answer}"
        
        print(f"[调试] 准备调用 AI API - answer_id: {answer_id}")
        client = OpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        
        # 构建消息内容
        content = [{"type": "text", "text": prompt}]
        
        print(f"[调试] 调用 AI API - answer_id: {answer_id}")
        completion = client.chat.completions.create(
            model="qwen2.5-omni-7b",
            messages=[{"role": "user", "content": content}],
            modalities=["text"],
            stream=True
        )
        
        # 处理流式响应
        full_response = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
        
        print(f"[调试] AI 分析完成 - answer_id: {answer_id}")
        print("[调试] qwen2.5-omni-7b分析结果：", full_response)
        
        # 从分析结果中提取分数
        try:
            # 尝试从文本中提取分数
            score_text = full_response.split('分：')[1].split('分')[0].strip()
            score = float(score_text)
            confidence_score = score
            fluency_score = score
            print(f"[调试] 提取到分数 - answer_id: {answer_id}, score: {score}")
        except Exception as e:
            print(f"[调试] 提取分数失败 - answer_id: {answer_id}, error: {str(e)}")
            confidence_score = 3.0
            fluency_score = 3.0
        
        # 更新答案记录
        print(f"[调试] 准备更新数据库 - answer_id: {answer_id}")
        answer.ai_analysis = full_response
        answer.confidence_score = confidence_score
        answer.fluency_score = fluency_score
        answer.save()
        
        print(f"[调试] 已更新数据库 - answer_id: {answer_id}, ai_analysis: {full_response}")
        return True
        
    except Exception as e:
        print(f"[调试] 分析面试回答出错 - answer_id: {answer_id}")
        print(f"错误信息: {str(e)}")
        print("详细错误信息:")
        print(traceback.format_exc())
        return False 