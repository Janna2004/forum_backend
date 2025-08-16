#!/usr/bin/env python
"""
测试代码题答案评析接口
"""

import os
import sys
import django
import json

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 设置Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 初始化Django
django.setup()

from code_execution.services import CodeEvaluationService
from code_execution.models import Problem

def test_code_evaluation():
    """测试代码评析功能"""
    
    # 测试数据
    test_answers = [
        {
            "problem_id": "algo-001",
            "source_code": """
def twoSum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
"""
        },
        {
            "problem_id": "algo-002", 
            "source_code": """
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def reverseList(head):
    prev = None
    curr = head
    while curr:
        next_temp = curr.next
        curr.next = prev
        prev = curr
        curr = next_temp
    return prev
"""
        }
    ]
    
    print("开始测试代码评析功能...")
    
    # 检查题目是否存在
    for answer in test_answers:
        problem_id = answer['problem_id']
        try:
            problem = Problem.objects.get(id=problem_id)
            print(f"✅ 找到题目: {problem.title}")
        except Problem.DoesNotExist:
            print(f"❌ 题目不存在: {problem_id}")
            return
    
    # 创建评析服务
    code_evaluation_service = CodeEvaluationService()
    
    # 执行评析
    print("\n开始执行代码评析...")
    result = code_evaluation_service.evaluate_code_answers(test_answers)
    
    if result['success']:
        print("✅ 代码评析成功")
        print("\n评析结果:")
        
        for i, problem_result in enumerate(result['results'], 1):
            print(f"\n--- 题目 {i}: {problem_result['problem_title']} ---")
            
            # 测试结果
            test_results = problem_result['test_results']
            if 'error' in test_results:
                print(f"测试错误: {test_results['error']}")
            else:
                summary = test_results['summary']
                print(f"公开测试用例: {summary['public_passed']}/{summary['public_total']}")
                print(f"隐藏测试用例: {summary['hidden_passed']}/{summary['hidden_total']}")
            
            # 评析结果
            evaluation = problem_result['evaluation']
            print(f"总分: {evaluation['score']}/30")
            print(f"测试分析: {evaluation['test_analysis']}")
            print(f"代码优点: {evaluation['strengths']}")
            print(f"代码问题: {evaluation['problems']}")
            print(f"改进建议: {evaluation['suggestions']}")
    else:
        print(f"❌ 代码评析失败: {result['error']}")

def test_single_problem():
    """测试单个题目的评析"""
    
    test_answer = {
        "problem_id": "algo-001",
        "source_code": """
def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
"""
    }
    
    print("\n开始测试单个题目评析...")
    
    code_evaluation_service = CodeEvaluationService()
    result = code_evaluation_service.evaluate_code_answers([test_answer])
    
    if result['success']:
        print("✅ 单个题目评析成功")
        problem_result = result['results'][0]
        evaluation = problem_result['evaluation']
        print(f"题目: {problem_result['problem_title']}")
        print(f"总分: {evaluation['score']}/30")
        print(f"改进建议: {evaluation['suggestions']}")
    else:
        print(f"❌ 单个题目评析失败: {result['error']}")

if __name__ == "__main__":
    print("=== 代码题答案评析接口测试 ===\n")
    
    # 测试批量评析
    test_code_evaluation()
    
    # 测试单个题目评析
    test_single_problem()
    
    print("\n=== 测试完成 ===")
