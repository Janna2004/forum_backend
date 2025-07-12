# 论坛后端系统

基于Django的论坛后端API，支持用户认证、帖子管理和AI对话功能。

## 功能特性

- 用户注册/登录（JWT认证）
- 帖子增删改查（分页）
- 讯飞大模型AI对话
- WebRTC视频流处理
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

## webSocet接口使用方法

请查看WebRTC_WebSocket_Testing_Guide.md

## 安全说明

- 敏感配置信息存储在 `config/local_settings.py` 中
- 该文件已被 `.gitignore` 忽略，不会提交到版本控制
- 生产环境请使用强随机SECRET_KEY
- 定期更新API密钥和数据库密码
