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
            `position_name` varchar(255) NOT NULL,
            `company_name` varchar(255) NOT NULL,
            `position_url` text NOT NULL,
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
            
            # 使用正则表达式提取INSERT语句中的值
            pattern = r'INSERT INTO "NowCoder-Data" VALUES\(\'(.*?)\',\'(.*?)\',\'(.*?)\'\)'
            matches = re.findall(pattern, sql_content)
            
            # 使用参数化查询重新插入数据
            insert_sql = """
                INSERT INTO `nowcoder_data` 
                (position_name, company_name, position_url) 
                VALUES (%s, %s, %s)
            """
            
            success_count = 0
            error_count = 0
            
            for match in matches:
                try:
                    position_name, company_name, position_url = match
                    cursor.execute(insert_sql, (position_name, company_name, position_url))
                    connection.commit()
                    success_count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"Successfully inserted: {position_name[:30]}..."
                    ))
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"Error inserting data: {e}")
                    )
                    self.stdout.write(
                        self.style.WARNING(f"Failed data: {position_name[:50]}...")
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