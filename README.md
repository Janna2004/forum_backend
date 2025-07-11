# 论坛后端系统

基于Django的论坛后端API，支持用户认证、帖子管理和AI对话功能。

## 功能特性

- 用户注册/登录（JWT认证）
- 帖子增删改查（分页）
- 讯飞大模型AI对话
- MySQL数据库支持

## 安装配置

### 1. 克隆项目
```bash
git clone <repository-url>
cd forum_backend
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置数据库和API密钥
复制配置示例文件：
```bash
cp config/local_settings_example.py config/local_settings.py
```

编辑 `config/local_settings.py`，填入你的配置：
- 数据库连接信息
- 讯飞API密钥
- Django SECRET_KEY

### 4. 数据库迁移
```bash
python manage.py migrate
```

### 5. 启动服务
```bash
python manage.py runserver
```

## API接口

### 用户认证
- `POST /users/register/` - 用户注册
- `POST /users/login/` - 用户登录

### 帖子管理
- `POST /posts/create/` - 创建帖子（需JWT）
- `DELETE /posts/delete/{id}/` - 删除帖子（需JWT）
- `POST /posts/update/{id}/` - 更新帖子（需JWT）
- `GET /posts/list/` - 获取帖子列表（分页）

### AI对话
- `POST /posts/chat/` - 讯飞AI对话（流式响应）

## 环境要求

- Python 3.8+
- Django 5.2+
- MySQL 5.7+
- PyJWT
- websocket-client

## 安全说明

- 敏感配置信息存储在 `config/local_settings.py` 中
- 该文件已被 `.gitignore` 忽略，不会提交到版本控制
- 生产环境请使用强随机SECRET_KEY
- 定期更新API密钥和数据库密码 