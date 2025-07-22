import os
import sys
import json
import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from positions.models import Position


class Command(BaseCommand):
    help = '从NowCoder爬虫数据导入岗位信息到positions表'

    def add_arguments(self, parser):
        # 所有参数都是可选的
        parser.add_argument(
            '--source',
            type=str,
            choices=['sql', 'csv', 'json'],
            default='sql',  # 默认使用SQL导入
            help='数据源类型 (sql, csv, json)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='导入前清空现有数据'
        )

    def handle(self, *args, **options):
        source_type = options.get('source', 'sql')  # 如果没有指定source参数，默认使用sql
        clear_data = options.get('clear', False)
        
        # 数据文件路径
        base_path = Path(__file__).resolve().parent.parent.parent.parent / 'crawler' / 'interview_position'
        
        if clear_data:
            self.stdout.write(self.style.WARNING('清空现有数据...'))
            Position.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('现有数据已清空'))

        try:
            if source_type == 'sql':
                self.import_from_sql(base_path / 'nowcoder_data_export.sql')
            elif source_type == 'csv':
                self.import_from_csv(base_path / 'nowcoder_data.csv')
            elif source_type == 'json':
                self.import_from_json(base_path / 'nowcoder_data.json')
                
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
                    # 检查是否已存在相同的岗位
                    if Position.objects.filter(
                        position_name=item.get('JobName', ''),
                        company_name=item.get('Company', ''),
                        position_url=item.get('Url', '')
                    ).exists():
                        skipped_count += 1
                        continue
                    
                    # 创建岗位记录
                    position = Position(
                        position_name=item.get('JobName', ''),
                        company_name=item.get('Company', ''),
                        position_url=item.get('Url', ''),
                        salary=item.get('Salary', ''),
                        address=item.get('Address', ''),
                        view_rate=item.get('ViewRate', ''),
                        ave_speed=item.get('AveSpeed', ''),
                        add_info=item.get('AddInfo', ''),
                        work_style=item.get('WorkStyle', ''),
                        work_time=item.get('WorkTime', ''),
                        upgrade_chance=item.get('UpgradeChance', ''),
                        introduction=item.get('Introduction', ''),
                        job_request=item.get('JobRequest', ''),
                    )
                    
                    # save方法会自动检测position_type
                    position.save()
                    imported_count += 1
                    
                    if imported_count % 100 == 0:
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

    def import_from_csv(self, file_path):
        """从CSV文件导入数据"""
        self.stdout.write(f'从CSV文件导入数据: {file_path}')
        
        if not file_path.exists():
            raise CommandError(f'文件不存在: {file_path}')
        
        imported_count = 0
        skipped_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            with transaction.atomic():
                for row in reader:
                    try:
                        # 检查是否已存在相同的岗位
                        if Position.objects.filter(
                            position_name=row.get('JobName', ''),
                            company_name=row.get('Company', ''),
                            position_url=row.get('Url', '')
                        ).exists():
                            skipped_count += 1
                            continue
                        
                        # 创建岗位记录
                        position = Position(
                            position_name=row.get('JobName', ''),
                            company_name=row.get('Company', ''),
                            position_url=row.get('Url', ''),
                            salary=row.get('Salary', ''),
                            address=row.get('Address', ''),
                            view_rate=row.get('ViewRate', ''),
                            ave_speed=row.get('AveSpeed', ''),
                            add_info=row.get('AddInfo', ''),
                            work_style=row.get('WorkStyle', ''),
                            work_time=row.get('WorkTime', ''),
                            upgrade_chance=row.get('UpgradeChance', ''),
                            introduction=row.get('Introduction', ''),
                            job_request=row.get('JobRequest', ''),
                        )
                        
                        # save方法会自动检测position_type
                        position.save()
                        imported_count += 1
                        
                        if imported_count % 100 == 0:
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
        
        # 简单的SQL解析，提取INSERT语句中的VALUES
        import re
        
        # 查找INSERT INTO语句
        insert_pattern = r'INSERT INTO[^(]+\([^)]+\)\s+VALUES\s*(.+?);'
        matches = re.findall(insert_pattern, sql_content, re.DOTALL | re.IGNORECASE)
        
        if not matches:
            raise CommandError('在SQL文件中未找到有效的INSERT语句')
        
        imported_count = 0
        skipped_count = 0
        
        with transaction.atomic():
            for match in matches:
                # 解析VALUES部分
                values_text = match.strip()
                
                # 简单解析VALUES中的数据行
                # 这里假设每行数据格式为: ('value1', 'value2', ...)
                value_pattern = r'\(([^)]+)\)'
                value_matches = re.findall(value_pattern, values_text)
                
                for value_match in value_matches:
                    try:
                        # 解析单行数据
                        values = [v.strip().strip("'\"") for v in value_match.split(',')]
                        
                        if len(values) < 3:  # 至少需要JobName, Company, Url
                            continue
                        
                        # 映射字段 (根据SQL文件中的字段顺序)
                        job_name = values[0] if len(values) > 0 else ''
                        company = values[1] if len(values) > 1 else ''
                        url = values[2] if len(values) > 2 else ''
                        salary = values[3] if len(values) > 3 else ''
                        address = values[4] if len(values) > 4 else ''
                        view_rate = values[5] if len(values) > 5 else ''
                        ave_speed = values[6] if len(values) > 6 else ''
                        add_info = values[7] if len(values) > 7 else ''
                        work_style = values[8] if len(values) > 8 else ''
                        work_time = values[9] if len(values) > 9 else ''
                        upgrade_chance = values[10] if len(values) > 10 else ''
                        introduction = values[11] if len(values) > 11 else ''
                        job_request = values[12] if len(values) > 12 else ''
                        
                        # 检查是否已存在相同的岗位
                        if Position.objects.filter(
                            position_name=job_name,
                            company_name=company,
                            position_url=url
                        ).exists():
                            skipped_count += 1
                            continue
                        
                        # 创建岗位记录
                        position = Position(
                            position_name=job_name,
                            company_name=company,
                            position_url=url,
                            salary=salary,
                            address=address,
                            view_rate=view_rate,
                            ave_speed=ave_speed,
                            add_info=add_info,
                            work_style=work_style,
                            work_time=work_time,
                            upgrade_chance=upgrade_chance,
                            introduction=introduction,
                            job_request=job_request,
                        )
                        
                        # save方法会自动检测position_type
                        position.save()
                        imported_count += 1
                        
                        if imported_count % 100 == 0:
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