# 数据库配置示例
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "your_database_name",
        "USER": "your_username",
        "PASSWORD": "your_password",
        "HOST": "localhost",
        "PORT": "3306",
    }
}

# 讯飞API配置示例
XUNFEI_APP_ID = "your_app_id"
XUNFEI_API_SECRET = "your_api_secret"
XUNFEI_API_KEY = "your_api_key"
XUNFEI_ASR_API_KEY = "your_asr_api_key"

# Django密钥（生产环境应使用强随机密钥）
SECRET_KEY = "your-secret-key-here" 