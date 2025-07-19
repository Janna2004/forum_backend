# 论坛后端系统

基于Django的论坛后端API，支持用户认证、帖子管理和AI对话功能。

## 功能特性

- 用户注册/登录（JWT认证）
- 帖子增删改查（分页）
- 讯飞大模型AI对话
- WebRTC视频流处理
- **智能面试问题生成**（基于讯飞星火+知识库）
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

> **注意：如需使用WebSocket（如WebRTC），必须用ASGI服务器启动，不能用`runserver`！**

开发环境推荐（requirement里已包含该包）：

```bash
python -m uvicorn config.asgi:application --host 0.0.0.0 --port 8000
```

或（requirements里未包含，需要自行下载）

```bash
python -m daphne config.asgi:application
```

如只需普通REST API，可用：

```bash
python manage.py runserver
```

但此时WebSocket接口不可用。

## webSocet接口使用方法

请查看WebRTC_WebSocket_Testing_Guide.md

## 面试问题生成功能

### 功能说明

基于讯飞星火大模型和知识库的智能面试问题生成系统，能够根据岗位信息和候选人简历，生成个性化的面试问题。

### 快速开始

1. **初始化知识库**

```bash
python manage.py init_knowledge_base
```

2. **配置讯飞API**
   在 `config/local_settings.py` 中配置讯飞API密钥：

```python
XUNFEI_APP_ID = "your_app_id"
XUNFEI_API_SECRET = "your_api_secret"
XUNFEI_API_KEY = "your_api_key"
```

3. **API接口**

- 生成面试问题：`POST /knowledge/generate-questions/`
- 获取面试历史：`GET /knowledge/interview-history/`
- 获取面试详情：`GET /knowledge/interview-detail/{id}/`

详细API文档请查看：`面试问题生成API文档.md`

## 安全说明

- 敏感配置信息存储在 `config/local_settings.py` 中
- 该文件已被 `.gitignore` 忽略，不会提交到版本控制
- 生产环境请使用强随机SECRET_KEY
- 定期更新API密钥和数据库密码
