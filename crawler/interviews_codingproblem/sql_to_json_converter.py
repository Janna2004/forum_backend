#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQL到JSON转换器
将interviews_codingproblem.sql文件转换为JSON格式
"""

import json
import re
from pathlib import Path


def parse_sql_file(sql_file_path):
    """解析SQL文件，提取代码题和样例数据"""
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    problems_data = []
    examples_data = []
    
    # 分割SQL语句
    sql_statements = sql_content.split(';')
    
    for statement in sql_statements:
        statement = statement.strip()
        if not statement:
            continue
        
        # 解析代码题INSERT语句
        if 'INSERT INTO interviews_codingproblem' in statement:
            problem_data = parse_problem_insert(statement)
            if problem_data:
                problem_data['examples'] = []
                problems_data.append(problem_data)
        
        # 解析样例INSERT语句
        elif 'INSERT INTO interviews_codingexample' in statement:
            example_data = parse_example_insert(statement)
            if example_data:
                examples_data.append(example_data)
    
    # 根据problem_id关联样例到对应的代码题
    for example in examples_data:
        problem_id = example.get('problem_id')
        if problem_id:
            # 找到对应的代码题（基于数组索引，因为problem_id通常是1,2,3...）
            try:
                problem_index = int(problem_id) - 1
                if 0 <= problem_index < len(problems_data):
                    problems_data[problem_index]['examples'].append({
                        'input_data': example['input_data'],
                        'output_data': example['output_data'],
                        'explanation': example['explanation'],
                        'order': example['order']
                    })
            except (ValueError, IndexError):
                # 如果problem_id不是数字或超出范围，跳过
                continue
    
    return problems_data


def parse_problem_insert(statement):
    """解析代码题INSERT语句"""
    try:
        # 检查是否有明确的字段列表
        if 'INSERT INTO interviews_codingproblem (' in statement:
            # 第一种格式：有明确字段列表
            values_match = re.search(r'VALUES\s*\((.+?)\)', statement, re.DOTALL | re.IGNORECASE)
            if not values_match:
                return None
            
            values_text = values_match.group(1)
            values = parse_sql_values(values_text)
            
            if len(values) < 8:  # 至少需要8个字段
                return None
            
            # 映射字段（按字段顺序）
            number = values[0].strip("'\"")
            title = values[1].strip("'\"")
            description = values[2].strip("'\"")
            difficulty = values[3].strip("'\"")
            tags = json.loads(values[4].strip("'"))
            companies = json.loads(values[5].strip("'"))
            position_types = json.loads(values[6].strip("'"))
            
        else:
            # 第二种格式：使用DEFAULT，按默认字段顺序
            values_match = re.search(r'VALUES\s*\((.+?)\)', statement, re.DOTALL | re.IGNORECASE)
            if not values_match:
                return None
            
            values_text = values_match.group(1)
            values = parse_sql_values(values_text)
            
            if len(values) < 8:  # 至少需要8个字段
                return None
            
            # 映射字段（跳过DEFAULT，按默认顺序）
            number = values[1].strip("'\"")  # 跳过DEFAULT
            title = values[2].strip("'\"")
            description = values[3].strip("'\"")
            difficulty = values[4].strip("'\"")
            tags = json.loads(values[5].strip("'"))
            companies = json.loads(values[6].strip("'"))
            position_types = json.loads(values[7].strip("'"))
        
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


def parse_example_insert(statement):
    """解析样例INSERT语句"""
    try:
        # 提取VALUES部分
        values_match = re.search(r'VALUES\s*\((.+?)\)', statement, re.DOTALL | re.IGNORECASE)
        if not values_match:
            return None
        
        values_text = values_match.group(1)
        
        # 解析字段值
        values = parse_sql_values(values_text)
        
        if len(values) < 4:  # 至少需要4个字段
            return None
        
        # 映射字段（包含problem_id）
        problem_id = values[0].strip("'\"") if len(values) > 0 else ''
        input_data = values[1].strip("'\"") if len(values) > 1 else ''
        output_data = values[2].strip("'\"") if len(values) > 2 else ''
        explanation = values[3].strip("'\"") if len(values) > 3 else ''
        order = int(values[4]) if len(values) > 4 and values[4].isdigit() else 1
        
        return {
            'problem_id': problem_id,
            'input_data': input_data,
            'output_data': output_data,
            'explanation': explanation,
            'order': order
        }
        
    except Exception as e:
        print(f'解析样例INSERT语句失败: {str(e)}')
        return None


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


def main():
    """主函数"""
    # 文件路径
    current_dir = Path(__file__).parent
    sql_file = current_dir / 'interviews_codingproblem.sql'
    json_file = current_dir / 'interviews_codingproblem.json'
    
    print(f'正在解析SQL文件: {sql_file}')
    
    # 解析SQL文件
    problems_data = parse_sql_file(sql_file)
    
    print(f'找到 {len(problems_data)} 个代码题')
    
    # 保存为JSON文件
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(problems_data, f, ensure_ascii=False, indent=2)
    
    print(f'JSON文件已保存: {json_file}')
    
    # 显示统计信息
    total_examples = sum(len(problem['examples']) for problem in problems_data)
    print(f'总计: {len(problems_data)} 个代码题, {total_examples} 个样例')
    
    # 显示前几个题目的信息
    print('\n前3个题目的信息:')
    for i, problem in enumerate(problems_data[:3]):
        print(f'{i+1}. {problem["number"]} - {problem["title"]} ({problem["difficulty"]})')
        print(f'   标签: {", ".join(problem["tags"])}')
        print(f'   公司: {", ".join(problem["companies"])}')
        print(f'   样例数: {len(problem["examples"])}')


if __name__ == '__main__':
    main()
