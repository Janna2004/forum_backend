#!/usr/bin/env python3
"""
获取JWT token用于WebSocket测试
"""

import requests
import json

# 配置
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/users/login/"

def get_token():
    """获取JWT token"""
    login_data = {
        "username": "testuser",
        "password": "testpass123"
    }
    
    try:
        response = requests.post(LOGIN_URL, json=login_data)
        if response.status_code == 200:
            token = response.json().get('token')
            print(f"登录成功！")
            print(f"JWT Token: {token}")
            print(f"\nWebSocket连接URL:")
            print(f"ws://localhost:8000/ws/webrtc/?token={token}")
            print(f"\n测试页面URL:")
            print(f"http://localhost:8000/webrtc/test/")
            return token
        else:
            print(f"登录失败: {response.text}")
            return None
    except Exception as e:
        print(f"请求失败: {str(e)}")
        return None

if __name__ == "__main__":
    print("=== 获取JWT Token用于WebSocket测试 ===")
    get_token() 