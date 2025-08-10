#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试代码题导入功能
"""

import os
import sys
import django
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from interviews.models import CodingProblem, CodingExample


def test_models():
    """测试模型是否正常工作"""
    print("测试模型...")
    
    # 创建测试代码题
    problem = CodingProblem(
        number='TEST001',
        title='测试题目',
        description='这是一个测试题目',
        difficulty='easy',
        tags=['测试', '数组'],
        companies=['测试公司'],
        position_types=['backend']
    )
    problem.save()
    
    # 创建测试样例
    example = CodingExample(
        problem=problem,
        input_data='nums = [1, 2, 3]',
        output_data='6',
        explanation='数组元素之和',
        order=1
    )
    example.save()
    
    print(f"创建测试代码题: {problem.number} - {problem.title}")
    print(f"创建测试样例: {example.input_data} -> {example.output_data}")
    
    # 查询测试
    problems = CodingProblem.objects.all()
    print(f"数据库中共有 {problems.count()} 个代码题")
    
    # 清理测试数据
    problem.delete()
    print("测试数据已清理")


def test_sql_parsing():
    """测试SQL解析功能"""
    print("\n测试SQL解析...")
    
    # 导入解析函数
    from interviews.management.commands.import_coding_problem import Command
    
    command = Command()
    
    # 测试SQL解析
    test_sql = """
    INSERT INTO interviews_codingproblem (
        number, title, description, difficulty, tags, companies, position_types, created_at, updated_at
    ) VALUES (
        'TEST002',
        '测试题目2',
        '这是另一个测试题目',
        'medium',
        '["测试", "字符串"]',
        '["测试公司2"]',
        '["frontend"]',
        NOW(), NOW()
    );
    INSERT INTO interviews_codingexample (problem_id, input_data, output_data, explanation, `order`) VALUES
    (1, 's = "hello"', '5', '字符串长度', 1);
    """
    
    problems_data = command._parse_sql_content(test_sql)
    print(f"解析出 {len(problems_data)} 个代码题")
    
    if problems_data:
        problem = problems_data[0]
        print(f"代码题: {problem['number']} - {problem['title']}")
        print(f"样例数: {len(problem['examples'])}")


if __name__ == '__main__':
    print("开始测试代码题导入功能...")
    
    try:
        test_models()
        test_sql_parsing()
        print("\n所有测试通过！")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
