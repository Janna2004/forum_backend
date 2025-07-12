#!/usr/bin/env python3
"""
创建测试用户
"""

import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import User

def create_test_user():
    """创建测试用户"""
    try:
        # 检查用户是否已存在
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        if created:
            # 设置密码
            user.set_password('testpass123')
            user.save()
            print(f"用户创建成功: {user.username}")
        else:
            # 更新密码
            user.set_password('testpass123')
            user.save()
            print(f"用户已存在，密码已更新: {user.username}")
        
        return user
        
    except Exception as e:
        print(f"创建用户失败: {str(e)}")
        return None

if __name__ == "__main__":
    print("=== 创建测试用户 ===")
    create_test_user() 