# 面经爬虫集成系统

---

> 本项目部分爬虫与数据处理代码参考自 [chadqiu/newcoder-crawler](https://github.com/chadqiu/newcoder-crawler?tab=Apache-2.0-1-ov-file)。
>
> 该项目遵循 [Apache-2.0 license](https://github.com/chadqiu/newcoder-crawler/blob/main/LICENSE)。
>
> 原作者：chadqiu（详见其 [GitHub 主页](https://github.com/chadqiu) 及 [项目主页](https://github.com/chadqiu/newcoder-crawler)）。
>
> 本集成系统在遵循 Apache-2.0 协议的前提下进行了二次开发与集成。

---

## 概述

本集成系统将牛客网面经爬虫与论坛后端系统整合，实现以下功能：

1. **自动创建测试用户** - 创建10个专用的爬虫测试账号
2. **智能标签生成** - 使用讯飞大模型从帖子内容中提取公司、岗位、技能等标签
3. **统一数据库管理** - 使用论坛项目的数据库配置，不再依赖单独的数据库
4. **帖子自动发布** - 将爬取的面经内容直接转换为论坛帖子

## 系统架构

```
面经爬虫集成系统
├── 数据获取层
│   ├── 牛客网API爬取
│   ├── 内容过滤与去重
│   └── 分类模型过滤
├── 数据处理层
│   ├── 讯飞大模型标签生成
│   ├── 测试用户随机分配
│   └── 帖子格式转换
└── 数据存储层
    ├── Django ORM
    ├── 帖子表 (posts_post)
    ├── 标签表 (posts_tag)
    └── 用户表 (users_user)
```

## 安装与配置

### 1. 确保基础环境

```bash
# 确保已安装依赖
pip install -r requirements.txt

# 确保数据库已迁移
python manage.py migrate
```

### 2. 配置讯飞API

在 `config/local_settings.py` 中配置讯飞API密钥：

```python
# 讯飞API配置
XUNFEI_APP_ID = "your_app_id"
XUNFEI_API_SECRET = "your_api_secret"  
XUNFEI_API_KEY = "your_api_key"
```

### 3. 创建测试用户

```bash
python manage.py create_test_users
```

这将创建10个测试用户：`crawler_user_01` 到 `crawler_user_10`

## 使用方法

### 方式一：直接运行集成爬虫

```bash
cd crawler/interview_experience
python crawler_integrated.py
```

### 功能说明

### 数据获取

- **来源**: 牛客网讨论区
- **关键词**: 实习、招聘、面经
- **过滤**: 自动过滤招聘信息，保留面经内容
- **去重**: 基于内容去重，避免重复帖子

### 标签生成

使用讯飞大模型自动提取以下类型标签：

- **公司标签** (`company`): 阿里巴巴、腾讯、字节跳动等
- **岗位标签** (`position`): Java开发、前端工程师、产品经理等
- **技能标签** (`skill`): Python、MySQL、算法、React等
- **行业标签** (`industry`): 互联网、金融、教育等
- **级别标签** (`level`): 实习、校招、社招等

### 用户分配

- 从10个测试用户中随机选择作为帖子发布者
- 用户信息：
  - 用户名: `crawler_user_01` ~ `crawler_user_10`
  - 密码: `crawler123` (统一密码)
  - 邮箱: `user01@example.com` ~ `user10@example.com`

## 数据库结构

### 帖子表 (posts_post)


| 字段          | 类型         | 说明           |
| ------------- | ------------ | -------------- |
| title         | VARCHAR(200) | 帖子标题       |
| content       | TEXT         | 帖子内容       |
| author_id     | INT          | 发布用户ID     |
| likes_count   | INT          | 点赞数 (默认0) |
| replies_count | INT          | 回复数 (默认0) |
| created_at    | DATETIME     | 创建时间       |

### 标签表 (posts_tag)


| 字段        | 类型        | 说明     |
| ----------- | ----------- | -------- |
| name        | VARCHAR(50) | 标签名称 |
| tag_type    | VARCHAR(20) | 标签类型 |
| description | TEXT        | 标签描述 |

### 标签关联表 (posts_post_tags)


| 字段    | 类型 | 说明   |
| ------- | ---- | ------ |
| post_id | INT  | 帖子ID |
| tag_id  | INT  | 标签ID |

## 配置参数

### 爬虫参数

```python
# 搜索关键词
keywords = ['实习', '招聘', "面经"]

# 过滤词汇 (避免无效内容)
skip_words = [
    '求捞', '泡池子', '池子了', 'offer对比', 
    '给个建议', '求助', 'kpi吗'
]

# 最大页数限制
max_pages = 5  # 每个关键词最多爬取5页
```

### 模型配置

```python
# 分类模型路径
model_name = "roberta4h512"  # 本地模型目录

# 讯飞API模型
model = "generalv3.5"  # 使用的讯飞大模型版本
```

## 监控与日志

### 日志级别

- `INFO`: 正常运行信息
- `WARNING`: 警告信息（如API配置缺失）
- `ERROR`: 错误信息（如网络请求失败）

### 关键日志

```
INFO - 开始运行面经爬虫...
INFO - 搜索关键词: 面经
INFO - 去重后共获取 45 条数据  
INFO - 过滤后剩余 32 条经验贴
INFO - 创建帖子成功: 15 - 阿里巴巴Java实习面经分享
INFO - 为帖子 15 生成了 5 个标签
INFO - 成功创建 32 个帖子
```

## 常见问题

### Q: 讯飞API调用失败怎么办？

A: 系统会自动降级到关键词匹配模式，确保基本功能正常：

```python
# 备用标签提取（关键词匹配）
company_keywords = ['阿里', '腾讯', '字节', '美团']
position_keywords = ['前端', '后端', 'java', 'python']
```

### Q: 如何避免重复爬取？

A: 系统通过以下方式避免重复：

1. 检查帖子标题是否已存在
2. 基于牛客网ID去重
3. 基于内容相似度去重

### Q: 如何自定义爬取范围？

A: 修改 `crawler_integrated.py` 中的参数：

```python
# 时间范围（天数）
days_back = 15  # 爬取最近15天的内容

# 页数限制  
max_pages = 10  # 每个关键词最多10页

# 关键词配置
keywords = ['你的关键词1', '你的关键词2']
```

## 维护说明

### 定期任务

1. **清理测试数据**: 定期清理测试帖子和标签
2. **用户管理**: 监控测试用户状态
3. **日志清理**: 清理过期日志文件

### 监控指标

- 爬取成功率
- 标签生成准确率
- API调用频率
- 数据库存储量

## 扩展功能

### 1. 定时任务

使用Celery配置定时爬取：

```python
# 在 tasks.py 中
@periodic_task(run_every=crontab(hour=2, minute=0))  # 每天凌晨2点
def auto_crawl_posts():
    from crawler.interview_experience.crawler_integrated import main
    return main()
```

### 2. 智能推荐

基于标签实现相关帖子推荐：

```python
def get_related_posts(post, limit=5):
    related_posts = Post.objects.filter(
        tags__in=post.tags.all()
    ).exclude(id=post.id).distinct()[:limit]
    return related_posts
```

### 3. 数据分析

生成爬取和标签统计报告：

```python
def generate_crawl_report():
    # 按时间统计帖子数量
    # 按标签类型统计分布
    # 按公司统计面经数量
    pass
```
