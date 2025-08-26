#!/usr/bin/env python
import os
import sys
import django
import requests
import json
import time

# 设置Django环境
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def test_local_execution():
    """测试本地代码执行"""
    print("🔍 测试本地代码执行...")
    
    # 测试数据
    test_cases = [
        {
            "name": "Python Hello World",
            "source_code": "print('Hello, World!')",
            "language_id": 71,  # Python
            "stdin": ""
        },
        {
            "name": "Python 简单计算",
            "source_code": "a = 5\nb = 3\nprint(a + b)",
            "language_id": 71,  # Python
            "stdin": ""
        },
        {
            "name": "Python 输入输出",
            "source_code": "name = input()\nprint(f'Hello, {name}!')",
            "language_id": 71,  # Python
            "stdin": "World"
        },
        {
            "name": "Python 错误代码",
            "source_code": "print('Hello')\nprint(1/0)",  # 故意制造错误
            "language_id": 71,  # Python
            "stdin": ""
        },
        {
            "name": "JavaScript Hello World",
            "source_code": "console.log('Hello, World!');",
            "language_id": 63,  # JavaScript
            "stdin": ""
        }
    ]
    
    url = "http://localhost:8000/code/run-code/"
    headers = {
        "Content-Type": "application/json"
    }
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {test_case['name']}")
        print(f"语言ID: {test_case['language_id']}")
        print(f"输入: {test_case['stdin'] if test_case['stdin'] else '(无)'}")
        
        start_time = time.time()
        
        try:
            response = requests.post(url, json=test_case, headers=headers, timeout=30)
            end_time = time.time()
            
            print(f"状态码: {response.status_code}")
            print(f"响应时间: {end_time - start_time:.3f}秒")
            
            if response.status_code == 200:
                result = response.json()
                status = result.get('status', {})
                status_id = status.get('id')
                status_description = status.get('description', 'Unknown')
                
                print(f"✅ 执行状态: {status_description} (ID: {status_id})")
                
                stdout = result.get('stdout', '')
                stderr = result.get('stderr', '')
                time_taken = result.get('time', 'N/A')
                memory = result.get('memory', 'N/A')
                
                print(f"  输出: {stdout.strip() if stdout else '(无)'}")
                if stderr:
                    print(f"  错误: {stderr.strip()}")
                print(f"  执行时间: {time_taken}ms")
                print(f"  内存使用: {memory}KB")
                success_count += 1
            else:
                print(f"❌ 请求失败，状态码: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"  错误信息: {error_data.get('error', 'Unknown error')}")
                except:
                    print(f"  错误响应: {response.text}")
                    
        except requests.exceptions.Timeout:
            print("❌ 请求超时")
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
    
    print(f"\n📊 测试结果: {success_count}/{total_count} 成功")
    print(f"成功率: {(success_count/total_count)*100:.1f}%")
    
    if success_count == total_count:
        print("🎉 所有测试通过！本地执行功能正常工作！")
    else:
        print("⚠️ 部分测试失败，请检查Django服务器状态")

if __name__ == "__main__":
    print("🚀 开始测试本地代码执行...")
    test_local_execution()
    print("\n✅ 测试完成!")
