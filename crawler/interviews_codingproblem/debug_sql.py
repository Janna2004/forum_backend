#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试SQL解析问题
"""

import re
import json

def parse_sql_values(values_text):
    """解析SQL VALUES中的字段值"""
    values = []
    current_value = ''
    in_quotes = False
    quote_char = None
    brace_count = 0
    
    for char in values_text:
        if char in ['"', "'"] and not in_quotes:
            in_quotes = True
            quote_char = char
            current_value += char
        elif char == quote_char and in_quotes:
            in_quotes = False
            quote_char = None
            current_value += char
        elif char == '[' and not in_quotes:
            brace_count += 1
            current_value += char
        elif char == ']' and not in_quotes:
            brace_count -= 1
            current_value += char
        elif char == ',' and not in_quotes and brace_count == 0:
            values.append(current_value.strip())
            current_value = ''
        else:
            current_value += char
    
    # 添加最后一个值
    if current_value.strip():
        values.append(current_value.strip())
    
    return values

def debug_parse_problem_insert(statement):
    """调试解析代码题INSERT语句"""
    print(f"=== 调试语句 ===")
    print(statement)
    print()
    
    try:
        # 检查是否有明确的字段列表
        if 'INSERT INTO interviews_codingproblem (' in statement:
            print("检测到第一种格式：有明确字段列表")
            # 第一种格式：有明确字段列表
            values_match = re.search(r'VALUES\s*\((.+?)\)', statement, re.DOTALL | re.IGNORECASE)
            if not values_match:
                print("未找到VALUES部分")
                return None
            
            values_text = values_match.group(1)
            print(f"VALUES文本: {values_text}")
            print()
            
            values = parse_sql_values(values_text)
            print(f"解析出的字段值: {values}")
            print(f"字段数量: {len(values)}")
            print()
            
            if len(values) < 8:
                print("字段数量不足8个")
                return None
            
            # 映射字段（按字段顺序）
            number = values[0].strip("'\"")
            title = values[1].strip("'\"")
            description = values[2].strip("'\"")
            difficulty = values[3].strip("'\"")
            
            print(f"number: {number}")
            print(f"title: {title}")
            print(f"description: {description}")
            print(f"difficulty: {difficulty}")
            print(f"tags原始值: {values[4]}")
            print(f"companies原始值: {values[5]}")
            print(f"position_types原始值: {values[6]}")
            print()
            
            # 尝试解析JSON
            try:
                tags = json.loads(values[4])
                print(f"tags解析成功: {tags}")
            except Exception as e:
                print(f"tags解析失败: {e}")
                return None
            
            try:
                companies = json.loads(values[5])
                print(f"companies解析成功: {companies}")
            except Exception as e:
                print(f"companies解析失败: {e}")
                return None
            
            try:
                position_types = json.loads(values[6])
                print(f"position_types解析成功: {position_types}")
            except Exception as e:
                print(f"position_types解析失败: {e}")
                return None
            
        else:
            print("检测到第二种格式：使用DEFAULT")
            # 第二种格式：使用DEFAULT，按默认字段顺序
            values_match = re.search(r'VALUES\s*\((.+?)\)', statement, re.DOTALL | re.IGNORECASE)
            if not values_match:
                print("未找到VALUES部分")
                return None
            
            values_text = values_match.group(1)
            print(f"VALUES文本: {values_text}")
            print()
            
            values = parse_sql_values(values_text)
            print(f"解析出的字段值: {values}")
            print(f"字段数量: {len(values)}")
            print()
            
            if len(values) < 8:
                print("字段数量不足8个")
                return None
            
            # 映射字段（跳过DEFAULT，按默认顺序）
            number = values[1].strip("'\"")  # 跳过DEFAULT
            title = values[2].strip("'\"")
            description = values[3].strip("'\"")
            difficulty = values[4].strip("'\"")
            
            print(f"number: {number}")
            print(f"title: {title}")
            print(f"description: {description}")
            print(f"difficulty: {difficulty}")
            print(f"tags原始值: {values[5]}")
            print(f"companies原始值: {values[6]}")
            print(f"position_types原始值: {values[7]}")
            print()
            
            # 尝试解析JSON
            try:
                tags = json.loads(values[5])
                print(f"tags解析成功: {tags}")
            except Exception as e:
                print(f"tags解析失败: {e}")
                return None
            
            try:
                companies = json.loads(values[6])
                print(f"companies解析成功: {companies}")
            except Exception as e:
                print(f"companies解析失败: {e}")
                return None
            
            try:
                position_types = json.loads(values[7])
                print(f"position_types解析成功: {position_types}")
            except Exception as e:
                print(f"position_types解析失败: {e}")
                return None
        
        return {
            'number': number,
            'title': title,
            'description': description,
            'difficulty': difficulty,
            'tags': tags,
            'companies': companies,
            'position_types': position_types
        }
        
    except Exception as e:
        print(f'解析代码题INSERT语句失败: {str(e)}')
        return None

def main():
    """主函数"""
    # 测试第一个INSERT语句
    test_sql1 = """INSERT INTO interviews_codingproblem (
    number, title, description, difficulty, tags, companies, position_types, created_at, updated_at
) VALUES (
    'LC001',
    '两数之和',
    '给定一个整数数组 nums 和一个整数目标值 target，请你在该数组中找出和为目标值的那两个整数，并返回它们的数组下标。',
    'easy',
    '["数组", "哈希表"]',
    '["字节跳动", "腾讯"]',
    '["backend", "frontend"]',
    NOW(), NOW()
);"""
    
    print("=== 测试第一个INSERT语句 ===")
    result1 = debug_parse_problem_insert(test_sql1)
    print(f"解析结果: {result1}")
    print("\n" + "="*50 + "\n")
    
    # 测试第二个INSERT语句
    test_sql2 = """INSERT INTO interviews_codingproblem VALUES (
    DEFAULT, 'LC002', '两数相加', 
    '给你两个非空的链表，表示两个非负的整数。它们每位数字是按逆序存储的，每个节点只能存储一位数字。请将这两个数相加并以链表形式返回。', 
    'medium', '["链表", "数学"]', '["阿里巴巴", "谷歌"]', '["backend", "algo"]', NOW(), NOW()
);"""
    
    print("=== 测试第二个INSERT语句 ===")
    result2 = debug_parse_problem_insert(test_sql2)
    print(f"解析结果: {result2}")

if __name__ == '__main__':
    main()
