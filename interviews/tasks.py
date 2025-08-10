from celery import shared_task
from django.conf import settings
import base64
from openai import OpenAI
from .models import InterviewAnswer
from .services import XunfeiASRService  # 添加这行导入
import traceback
import os
import time

@shared_task(name='interviews.analyze_interview_answer')
def analyze_interview_answer(answer_id, av_path=None, audio_path=None, has_audio=False, has_video=False):
    """异步分析面试回答"""
    print(f"[调试] 开始处理面试回答分析任务 - answer_id: {answer_id}")
    print(f"[调试] 文件信息 - av_path: {av_path}, audio_path: {audio_path}, has_audio: {has_audio}, has_video: {has_video}")
    
    try:
        # 获取面试答案记录
        answer = InterviewAnswer.objects.get(id=answer_id)
        print(f"[调试] 成功获取答案记录 - answer_id: {answer_id}")
        
        # 第一步：优先使用音频文件进行ASR转写并更新数据库
        if has_audio and audio_path and os.path.exists(audio_path):
            print(f"[调试] 使用音频文件进行ASR转写 - answer_id: {answer_id}, audio_path: {audio_path}")
            asr_service = XunfeiASRService(audio_path)
            transcribed_text = asr_service.get_result()
            if transcribed_text:
                print(f"[调试] 音频转写成功 - answer_id: {answer_id}")
                answer.answer = transcribed_text  # 用录音文件转写结果替换
                answer.save()
                print(f"[调试] 已更新数据库中的答案文本 - answer_id: {answer_id}")
            else:
                print(f"[调试] 音频转写失败 - answer_id: {answer_id}")
        elif has_video and av_path and os.path.exists(av_path):
            print(f"[调试] 只有视频文件，无法进行ASR转写 - answer_id: {answer_id}")
            # 视频文件无法进行ASR转写，保持占位文本
        else:
            print(f"[调试] 无音频文件，无法进行ASR转写 - answer_id: {answer_id}")
        
        # 第二步：获取问题知识点
        knowledge_points = answer.knowledge_points if hasattr(answer, 'knowledge_points') and answer.knowledge_points else []
        knowledge_points_str = "、".join(knowledge_points) if knowledge_points else "通用技能"
        
        # 第三步：构建分析提示（使用转写后的文本）
        prompt = f"""请根据以下面试问题和应答，从七个维度进行评分（1-5分）并给出分析理由：

1. 专业知识水平：对专业领域的理解深度和广度
2. 技能匹配度：技能与岗位要求的匹配程度
3. 语言表达能力：表达的清晰度、逻辑性和专业性
4. 逻辑思维能力：分析问题和解决问题的思路
5. 创新能力：思维的创新性和解决方案的独特性
6. 应变抗压能力：处理压力和突发情况的能力
7. 答案正确性：回答的准确性和完整性，针对问题涉及的知识点进行评估

评分标准：
1分：不及格，完全不符合要求
2分：基础水平，勉强达到基本要求
3分：中等水平，基本符合要求
4分：良好水平，超出基本要求
5分：优秀水平，远超预期要求

问题涉及的知识点：{knowledge_points_str}

请按以下格式输出：
专业知识水平：X分。理由：...
技能匹配度：X分。理由：...
语言表达能力：X分。理由：...
逻辑思维能力：X分。理由：...
创新能力：X分。理由：...
应变抗压能力：X分。理由：...
答案正确性：X分。理由：...

面试问题：{answer.question}
应答内容：{answer.answer}"""
        
        print(f"[调试] 准备调用 AI API - answer_id: {answer_id}")
        client = OpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        
        # 第四步：构建消息内容
        content = [{"type": "text", "text": prompt}]
        
        # 第五步：如果有视频文件，添加为base64编码的内容用于多模态分析
        if has_video and av_path and os.path.exists(av_path):
            print(f"[调试] 添加视频文件到多模态分析 - answer_id: {answer_id}")
            try:
                # 检查视频文件大小，如果太大则跳过
                file_size = os.path.getsize(av_path)
                if file_size > 50 * 1024 * 1024:  # 50MB限制
                    print(f"[警告] 视频文件过大({file_size/1024/1024:.1f}MB)，跳过多模态分析 - answer_id: {answer_id}")
                else:
                    with open(av_path, "rb") as f:
                        video_bytes = f.read()
                    video_b64 = base64.b64encode(video_bytes).decode('utf-8')
                    
                    content.append({
                        "type": "video_url",
                        "video_url": {
                            "url": f"data:video/mp4;base64,{video_b64}"
                        }
                    })
                    print(f"[调试] 视频文件已添加到多模态分析内容 - answer_id: {answer_id}")
            except Exception as e:
                print(f"[警告] 添加视频文件失败 - answer_id: {answer_id}, error: {e}")
        else:
            print(f"[调试] 无视频文件，仅进行文本分析 - answer_id: {answer_id}")
        
        # 第六步：调用qwen-omni API进行多模态分析
        print(f"[调试] 调用 AI API - answer_id: {answer_id}")
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
        
        print(f"[调试] AI 分析完成 - answer_id: {answer_id}")
        print("[调试] qwen2.5-omni-7b分析结果：", full_response)
        
        # 第七步：从分析结果中提取分数并更新数据库
        try:
            # 解析各个维度的分数
            scores = {
                'professional_knowledge': 0,
                'skill_matching': 0,
                'communication_skills': 0,
                'logical_thinking': 0,
                'innovation_ability': 0,
                'stress_handling': 0,
                'correctness_score': 0
            }
            
            # 使用简单的文本解析来提取分数
            for line in full_response.split('\n'):
                if '分。' in line:
                    score_text = line.split('：')[1].split('分。')[0].strip()
                    try:
                        score = float(score_text)
                        if '专业知识' in line:
                            scores['professional_knowledge'] = score
                        elif '技能匹配' in line:
                            scores['skill_matching'] = score
                        elif '语言表达' in line:
                            scores['communication_skills'] = score
                        elif '逻辑思维' in line:
                            scores['logical_thinking'] = score
                        elif '创新能力' in line:
                            scores['innovation_ability'] = score
                        elif '应变抗压' in line:
                            scores['stress_handling'] = score
                        elif '答案正确性' in line or '正确性' in line:
                            scores['correctness_score'] = score
                    except ValueError:
                        print(f"[调试] 解析分数失败: {score_text}")
                        continue
            
            print(f"[调试] 提取到分数 - answer_id: {answer_id}, scores: {scores}")
            
            # 更新答案记录
            answer.ai_analysis = full_response
            for field, score in scores.items():
                setattr(answer, field, score)
            answer.save()
            
            print(f"[调试] 已更新数据库 - answer_id: {answer_id}")
            return True
            
        except Exception as e:
            print(f"[调试] 提取分数失败 - answer_id: {answer_id}, error: {str(e)}")
            # 如果解析失败，设置默认分数
            answer.ai_analysis = full_response
            answer.professional_knowledge = 3.0
            answer.skill_matching = 3.0
            answer.communication_skills = 3.0
            answer.logical_thinking = 3.0
            answer.innovation_ability = 3.0
            answer.stress_handling = 3.0
            answer.correctness_score = 3.0
            answer.save()
            return False
            
    except Exception as e:
        print(f"[调试] 分析面试回答出错 - answer_id: {answer_id}")
        print(f"错误信息: {str(e)}")
        print("详细错误信息:")
        print(traceback.format_exc())
        return False