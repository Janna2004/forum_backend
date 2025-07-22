import os
import sys
import django
import MySQLdb
from pathlib import Path

# 添加项目根目录到Python路径
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def import_sql_to_database():
    try:
        # 获取数据库配置
        from django.conf import settings
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
        
        # 读取SQL文件
        sql_file_path = os.path.join(os.path.dirname(__file__), 'nowcoder_data_export.sql')
        with open(sql_file_path, 'r', encoding='utf-8') as sql_file:
            sql_content = sql_file.read()
            
        # 执行SQL语句
        # 分割SQL语句（假设语句以分号结尾）
        sql_commands = sql_content.split(';')
        
        for command in sql_commands:
            # 跳过空命令
            if command.strip():
                try:
                    cursor.execute(command)
                    connection.commit()
                except Exception as e:
                    print(f"Error executing SQL command: {e}")
                    print(f"Problematic SQL: {command[:100]}...")  # 只打印前100个字符
                    connection.rollback()
        
        print("SQL import completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        if 'connection' in locals():
            cursor.close()
            connection.close()

if __name__ == '__main__':
    import_sql_to_database() 