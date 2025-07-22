import os
from django.core.management.base import BaseCommand
import MySQLdb
from django.conf import settings
import re

class Command(BaseCommand):
    help = 'Import data from nowcoder_data_export.sql file'

    def clean_sql_command(self, command):
        """清理和修复SQL命令"""
        if not command.strip():
            return None
            
        # 替换表名中的双引号和连字符
        command = command.replace('"NowCoder-Data"', '`nowcoder_data`')
        
        # 确保命令以分号结尾
        command = command.strip()
        if not command.endswith(';'):
            command += ';'
            
        return command

    def create_table(self, cursor):
        """创建表结构"""
        # 删除已存在的表
        cursor.execute("DROP TABLE IF EXISTS `nowcoder_data`;")
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS `nowcoder_data` (
            `id` int NOT NULL AUTO_INCREMENT,
            `job_name` varchar(500) NOT NULL,
            `company` varchar(255) NOT NULL,
            `url` text NOT NULL,
            `salary` varchar(100) DEFAULT NULL,
            `address` text DEFAULT NULL,
            `view_rate` varchar(100) DEFAULT NULL,
            `ave_speed` varchar(100) DEFAULT NULL,
            `add_info` varchar(100) DEFAULT NULL,
            `work_style` varchar(100) DEFAULT NULL,
            `work_time` varchar(200) DEFAULT NULL,
            `upgrade_chance` varchar(50) DEFAULT NULL,
            `introduction` text DEFAULT NULL,
            `job_request` text DEFAULT NULL,
            PRIMARY KEY (`id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        cursor.execute(create_table_sql)

    def handle(self, *args, **options):
        try:
            # 获取数据库配置
            db_settings = settings.DATABASES['default']
            
            # 连接到数据库
            connection = MySQLdb.connect(
                host=db_settings['HOST'],
                user=db_settings['USER'],
                passwd=db_settings['PASSWORD'],
                db=db_settings['NAME'],
                port=int(db_settings['PORT']),
                charset='utf8mb4'
            )
            
            cursor = connection.cursor()
            
            # 创建表结构
            self.create_table(cursor)
            
            # 读取SQL文件
            sql_file_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'nowcoder_data_export.sql'
            )
            
            self.stdout.write(f"Reading SQL file from: {sql_file_path}")
            
            with open(sql_file_path, 'r', encoding='utf-8') as sql_file:
                sql_content = sql_file.read()
            
            # 先检查文件内容
            lines = sql_content.split('\n')
            insert_lines = [line for line in lines if line.strip().startswith('INSERT INTO')]
            self.stdout.write(f"Found {len(insert_lines)} INSERT statements in the file")
            
            # 使用改进的正则表达式，处理跨行的情况
            pattern = r'INSERT INTO "NowCoder-Data" VALUES\((.*?)\);?(?=\s*(?:INSERT|$))'
            matches = re.findall(pattern, sql_content, re.DOTALL | re.MULTILINE)
            
            self.stdout.write(f"Regex found {len(matches)} matches")
            
            # 使用参数化查询重新插入数据
            insert_sql = """
                INSERT INTO `nowcoder_data` 
                (job_name, company, url, salary, address, view_rate, ave_speed, 
                 add_info, work_style, work_time, upgrade_chance, introduction, job_request) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            success_count = 0
            error_count = 0
            
            for i, match in enumerate(matches):  # 处理所有记录
                try:
                    # 改进的字段解析逻辑
                    values_str = match.strip()
                    
                    # 使用正则表达式来分割字段，处理嵌套引号的情况
                    field_pattern = r"'((?:[^']|'')*?)'"
                    fields = re.findall(field_pattern, values_str)
                    
                    # 处理转义的单引号
                    fields = [field.replace("''", "'") for field in fields]
                    
                    if len(fields) != 13:
                        # 尝试另一种解析方法 - 手动解析
                        fields = []
                        current_field = ""
                        in_quotes = False
                        i = 0
                        
                        while i < len(values_str):
                            char = values_str[i]
                            if char == "'" and not in_quotes:
                                in_quotes = True
                            elif char == "'" and in_quotes:
                                # 检查是否是转义的单引号
                                if i + 1 < len(values_str) and values_str[i + 1] == "'":
                                    current_field += "'"
                                    i += 1  # 跳过下一个单引号
                                else:
                                    in_quotes = False
                                    fields.append(current_field)
                                    current_field = ""
                            elif char == "," and not in_quotes:
                                # 跳过逗号和空格
                                while i + 1 < len(values_str) and values_str[i + 1] in [' ', '\n', '\r']:
                                    i += 1
                            elif in_quotes:
                                current_field += char
                            i += 1
                        
                        # 添加最后一个字段（如果有的话）
                        if current_field:
                            fields.append(current_field)
                    
                    if len(fields) != 13:
                        if (i + 1) <= 10:  # 只在前10条显示详细错误信息
                            self.stdout.write(
                                self.style.WARNING(f"Row {i+1}: Found {len(fields)} fields instead of 13")
                            )
                            self.stdout.write(f"Raw data: {values_str[:200]}...")
                        error_count += 1
                        continue
                    
                    cursor.execute(insert_sql, tuple(fields))
                    connection.commit()
                    success_count += 1
                    
                    # 每1000条记录显示一次进度
                    if success_count % 1000 == 0:
                        self.stdout.write(self.style.SUCCESS(
                            f"Successfully imported {success_count} records..."
                        ))
                    
                except Exception as e:
                    error_count += 1
                    if error_count <= 10:  # 只显示前10个错误
                        self.stdout.write(
                            self.style.ERROR(f"Error inserting row {i+1}: {e}")
                        )
                    connection.rollback()
            
            self.stdout.write(self.style.SUCCESS(
                f"\nImport completed!\nSuccessfully imported: {success_count} records\nFailed: {error_count} records"
            ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
        
        finally:
            if 'connection' in locals():
                cursor.close()
                connection.close() 