import os
import sys
import json
import re
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from interviews.models import CodingProblem, CodingExample


class Command(BaseCommand):
    help = '从SQL或JSON文件导入代码题数据到interviews_codingproblem表'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['sql', 'json'],
            default='sql',
            help='数据源类型 (sql, json)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='导入前清空现有数据'
        )
        parser.add_argument(
            '--file',
            type=str,
            help='指定数据文件路径（可选）'
        )

    def handle(self, *args, **options):
        source_type = options.get('source', 'sql')
        clear_data = options.get('clear', False)
        file_path = options.get('file')
        
        # 数据文件路径
        if file_path:
            data_file = Path(file_path)
        else:
            base_path = Path(__file__).resolve().parent.parent.parent.parent / 'crawler' / 'interviews_codingproblem'
            if source_type == 'sql':
                data_file = base_path / 'interviews_codingproblem.sql'
            else:
                data_file = base_path / 'interviews_codingproblem.json'
        
        if clear_data:
            self.stdout.write(self.style.WARNING('清空现有数据...'))
            CodingExample.objects.all().delete()
            CodingProblem.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('现有数据已清空'))

        try:
            if source_type == 'sql':
                self.import_from_sql(data_file)
            elif source_type == 'json':
                self.import_from_json(data_file)
                
        except Exception as e:
            raise CommandError(f'导入数据时出错: {str(e)}')

    def import_from_json(self, file_path):
        """从JSON文件导入数据"""
        self.stdout.write(f'从JSON文件导入数据: {file_path}')
        
        if not file_path.exists():
            raise CommandError(f'文件不存在: {file_path}')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.stdout.write(f'找到 {len(data)} 条记录')
        
        imported_count = 0
        skipped_count = 0
        
        with transaction.atomic():
            for item in data:
                try:
                    # 检查是否已存在相同的题目
                    if CodingProblem.objects.filter(number=item.get('number', '')).exists():
                        skipped_count += 1
                        continue
                    
                    # 创建代码题记录
                    problem = CodingProblem(
                        number=item.get('number', ''),
                        title=item.get('title', ''),
                        description=item.get('description', ''),
                        difficulty=item.get('difficulty', 'medium'),
                        tags=item.get('tags', []),
                        companies=item.get('companies', []),
                        position_types=item.get('position_types', [])
                    )
                    problem.save()
                    
                    # 创建样例记录
                    examples = item.get('examples', [])
                    for example_data in examples:
                        example = CodingExample(
                            problem=problem,
                            input_data=example_data.get('input_data', ''),
                            output_data=example_data.get('output_data', ''),
                            explanation=example_data.get('explanation', ''),
                            order=example_data.get('order', 1)
                        )
                        example.save()
                    
                    imported_count += 1
                    
                    if imported_count % 10 == 0:
                        self.stdout.write(f'已导入 {imported_count} 条记录...')
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'导入记录失败: {str(e)}')
                    )
                    continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f'导入完成！成功导入 {imported_count} 条记录，跳过重复记录 {skipped_count} 条'
            )
        )

    def import_from_sql(self, file_path):
        """从SQL文件导入数据（解析INSERT语句）"""
        self.stdout.write(f'从SQL文件导入数据: {file_path}')
        
        if not file_path.exists():
            raise CommandError(f'文件不存在: {file_path}')
        
        # 读取SQL文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 解析SQL文件，提取代码题和样例数据
        problems_data = self._parse_sql_content(sql_content)
        
        imported_count = 0
        skipped_count = 0
        
        with transaction.atomic():
            for problem_data in problems_data:
                try:
                    # 检查是否已存在相同的题目
                    if CodingProblem.objects.filter(number=problem_data['number']).exists():
                        skipped_count += 1
                        continue
                    
                    # 创建代码题记录
                    problem = CodingProblem(
                        number=problem_data['number'],
                        title=problem_data['title'],
                        description=problem_data['description'],
                        difficulty=problem_data['difficulty'],
                        tags=problem_data['tags'],
                        companies=problem_data['companies'],
                        position_types=problem_data['position_types']
                    )
                    problem.save()
                    
                    # 创建样例记录
                    for example_data in problem_data['examples']:
                        example = CodingExample(
                            problem=problem,
                            input_data=example_data['input_data'],
                            output_data=example_data['output_data'],
                            explanation=example_data['explanation'],
                            order=example_data['order']
                        )
                        example.save()
                    
                    imported_count += 1
                    
                    if imported_count % 10 == 0:
                        self.stdout.write(f'已导入 {imported_count} 条记录...')
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'导入记录失败: {str(e)}')
                    )
                    continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f'导入完成！成功导入 {imported_count} 条记录，跳过重复记录 {skipped_count} 条'
            )
        )

    def _parse_sql_content(self, sql_content):
        """解析SQL文件内容，提取代码题和样例数据"""
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
                problem_data = self._parse_problem_insert(statement)
                if problem_data:
                    problem_data['examples'] = []
                    problems_data.append(problem_data)
            
            # 解析样例INSERT语句
            elif 'INSERT INTO interviews_codingexample' in statement:
                example_data = self._parse_example_insert(statement)
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

    def _parse_problem_insert(self, statement):
        """解析代码题INSERT语句"""
        try:
            # 检查是否有明确的字段列表
            if 'INSERT INTO interviews_codingproblem (' in statement:
                # 第一种格式：有明确字段列表
                values_match = re.search(r'VALUES\s*\((.+?)\)', statement, re.DOTALL | re.IGNORECASE)
                if not values_match:
                    return None
                
                values_text = values_match.group(1)
                values = self._parse_sql_values(values_text)
                
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
                values = self._parse_sql_values(values_text)
                
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
            self.stdout.write(f'解析代码题INSERT语句失败: {str(e)}')
            return None

    def _parse_example_insert(self, statement):
        """解析样例INSERT语句"""
        try:
            # 提取VALUES部分
            values_match = re.search(r'VALUES\s*\((.+?)\)', statement, re.DOTALL | re.IGNORECASE)
            if not values_match:
                return None
            
            values_text = values_match.group(1)
            
            # 解析字段值
            values = self._parse_sql_values(values_text)
            
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
            self.stdout.write(f'解析样例INSERT语句失败: {str(e)}')
            return None

    def _parse_sql_values(self, values_text):
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
