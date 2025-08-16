#!/usr/bin/env python
"""
测试修复后的评析服务
"""

import os
import sys
import django

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 设置Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 初始化Django
django.setup()

from code_execution.services import ProblemEvaluationService
from code_execution.models import Problem

def test_problem_evaluation_service():
    """测试ProblemEvaluationService是否正常工作"""
    
    print("开始测试ProblemEvaluationService...")
    
    # 创建服务实例
    service = ProblemEvaluationService()
    
    # 检查方法是否存在
    methods_to_check = [
        'evaluate_multiple_problems',
        'evaluate_single_problem', 
        'evaluate_problems_with_overall_analysis',
        'generate_overall_analysis'
    ]
    
    for method_name in methods_to_check:
        if hasattr(service, method_name):
            print(f"✅ 方法存在: {method_name}")
        else:
            print(f"❌ 方法缺失: {method_name}")
    
    # 测试evaluate_problems_with_overall_analysis方法
    try:
        # 获取一个测试题目
        test_problem = Problem.objects.filter(is_algorithm=False).first()
        if test_problem:
            print(f"✅ 找到测试题目: {test_problem.title}")
            
            # 测试方法调用
            test_data = [(test_problem, "这是一个测试答案")]
            result = service.evaluate_problems_with_overall_analysis(test_data, "测试题库")
            
            if 'evaluations' in result and 'overall_analysis' in result:
                print("✅ evaluate_problems_with_overall_analysis 方法正常工作")
                print(f"   评析结果数量: {len(result['evaluations'])}")
                print(f"   整体分析: {result['overall_analysis'][:50]}...")
            else:
                print("❌ evaluate_problems_with_overall_analysis 返回格式错误")
        else:
            print("⚠️ 没有找到非算法题目用于测试")
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
    
    print("\n测试完成!")

if __name__ == "__main__":
    test_problem_evaluation_service()
