import sqlite3
import json

# 连接到数据库
conn = sqlite3.connect('./static/Data.db')
conn.row_factory = sqlite3.Row

# 获取所有数据
cursor = conn.cursor()
cursor.execute("SELECT * FROM 'NowCoder-Data'")
rows = cursor.fetchall()

# 将数据转换为字典列表
data = []
for row in rows:
    data.append({key: row[key] for key in row.keys()})

# 将数据写入SQL文件
with open('nowcoder_data_export.sql', 'w', encoding='utf-8') as f:
    # 写入建表语句
    f.write("""CREATE TABLE IF NOT EXISTS "NowCoder-Data" (
    "JobName" TEXT,
    "Company" TEXT,
    "Url" TEXT,
    "Salary" TEXT,
    "Address" TEXT,
    "ViewRate" TEXT,
    "AveSpeed" TEXT,
    "AddInfo" TEXT,
    "WorkStyle" TEXT,
    "WorkTime" TEXT,
    "UpgradeChance" TEXT,
    "Introduction" TEXT,
    "JobRequest" TEXT
);\n\n""")
    
    # 写入数据
    for item in data:
        values = [
            item['JobName'] if item['JobName'] else 'NULL',
            item['Company'] if item['Company'] else 'NULL',
            item['Url'] if item['Url'] else 'NULL',
            item['Salary'] if item['Salary'] else 'NULL',
            item['Address'] if item['Address'] else 'NULL',
            item['ViewRate'] if item['ViewRate'] else 'NULL',
            item['AveSpeed'] if item['AveSpeed'] else 'NULL',
            item['AddInfo'] if item['AddInfo'] else 'NULL',
            item['WorkStyle'] if item['WorkStyle'] else 'NULL',
            item['WorkTime'] if item['WorkTime'] else 'NULL',
            item['UpgradeChance'] if item['UpgradeChance'] else 'NULL',
            item['Introduction'] if item['Introduction'] else 'NULL',
            item['JobRequest'] if item['JobRequest'] else 'NULL'
        ]
        # 处理字符串中的特殊字符
        values = ["'" + str(v).replace("'", "''") + "'" if v != 'NULL' else 'NULL' for v in values]
        f.write(f"INSERT INTO \"NowCoder-Data\" VALUES({','.join(values)});\n")

# 同时导出JSON格式（便于查看）
with open('nowcoder_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

conn.close()
print("数据导出完成！") 