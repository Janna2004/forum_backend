import os
from celery import Celery
from django.conf import settings

# 设置默认的Django settings模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 创建Celery实例
app = Celery('forum_backend')

# 从Django设置中加载Celery配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 设置Celery的任务发现机制
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=False,
)

# 自动发现并注册任务
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 