#!/usr/bin/env python
import os
import sys
import django
import asyncio

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from webrtc.consumers import WebRTCConsumer
from knowledge_base.services import KnowledgeBaseService

async def test_async_knowledge_points():
    print("=== 异步知识点生成功能测试 ===\n")
    
    # 创建消费者实例
    consumer = WebRTCConsumer()
    
    # 模拟面试数据
    consumer.interview_id = 34  # 使用一个存在的面试ID
    consumer.resume_id = 1      # 使用一个存在的简历ID
    
    # 创建知识库服务
    kb_service = KnowledgeBaseService()
    
    print("开始测试异步知识点生成...")
    
    try:
        # 调用初始化问题队列
        questions = await consumer.init_question_queue()
        
        print(f"\n生成的问题数量: {len(questions)}")
        
        # 显示前几个问题的初始状态
        for i, question_data in enumerate(questions[:3]):
            print(f"\n问题 {i+1}:")
            print(f"  问题: {question_data['question'][:100]}...")
            print(f"  初始知识点: {question_data['knowledge_points']}")
            print(f"  知识点已生成: {question_data.get('knowledge_points_generated', False)}")
        
        # 等待一段时间让异步任务完成
        print("\n等待异步知识点生成...")
        await asyncio.sleep(5)
        
        # 检查知识点是否已更新
        print("\n检查知识点更新状态:")
        for i, question_data in enumerate(questions[:3]):
            print(f"\n问题 {i+1}:")
            print(f"  问题: {question_data['question'][:100]}...")
            print(f"  当前知识点: {question_data['knowledge_points']}")
            print(f"  知识点已生成: {question_data.get('knowledge_points_generated', False)}")
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"测试出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test_async_knowledge_points())
