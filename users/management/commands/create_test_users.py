from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import random

User = get_user_model()

class Command(BaseCommand):
    help = '创建10个测试用户用于爬虫数据的发帖'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='删除已存在的测试用户后重新创建',
        )

    def handle(self, *args, **options):
        test_users = [
            {'username': 'crawler_user_01', 'email': 'user01@example.com'},
            {'username': 'crawler_user_02', 'email': 'user02@example.com'},
            {'username': 'crawler_user_03', 'email': 'user03@example.com'},
            {'username': 'crawler_user_04', 'email': 'user04@example.com'},
            {'username': 'crawler_user_05', 'email': 'user05@example.com'},
            {'username': 'crawler_user_06', 'email': 'user06@example.com'},
            {'username': 'crawler_user_07', 'email': 'user07@example.com'},
            {'username': 'crawler_user_08', 'email': 'user08@example.com'},
            {'username': 'crawler_user_09', 'email': 'user09@example.com'},
            {'username': 'crawler_user_10', 'email': 'user10@example.com'},
        ]

        # 如果指定了reset选项，先删除已存在的测试用户
        if options['reset']:
            self.stdout.write('删除已存在的测试用户...')
            deleted_count = User.objects.filter(
                username__in=[user['username'] for user in test_users]
            ).delete()[0]
            self.stdout.write(f'已删除 {deleted_count} 个测试用户')

        created_count = 0
        skipped_count = 0

        for user_data in test_users:
            username = user_data['username']
            email = user_data['email']
            
            if User.objects.filter(username=username).exists():
                self.stdout.write(f'用户 {username} 已存在，跳过创建')
                skipped_count += 1
                continue

            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password='crawler123',  # 统一密码
                    first_name='爬虫',
                    last_name=f'用户{username[-2:]}'
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'成功创建用户: {username}')
                )
            except ValidationError as e:
                self.stdout.write(
                    self.style.ERROR(f'创建用户 {username} 失败: {e}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'创建用户 {username} 时发生错误: {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n任务完成！共创建 {created_count} 个用户，跳过 {skipped_count} 个已存在的用户'
            )
        )

    @classmethod
    def get_random_test_user(cls):
        """获取一个随机的测试用户，供爬虫使用"""
        test_usernames = [f'crawler_user_{i:02d}' for i in range(1, 11)]
        try:
            users = User.objects.filter(username__in=test_usernames)
            if users.exists():
                return random.choice(users)
            else:
                # 如果没有测试用户，创建一个默认用户
                return User.objects.get_or_create(
                    username='crawler_user_01',
                    defaults={
                        'email': 'user01@example.com',
                        'password': 'crawler123'
                    }
                )[0]
        except Exception:
            # 出错时返回第一个普通用户
            return User.objects.first() 