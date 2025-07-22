# -*- coding: utf-8 -*-
"""
集成版面经爬虫
- 使用Django数据库配置
- 自动创建帖子并生成标签
- 随机分配发帖用户
"""

import os
import sys
import django
from pathlib import Path

# 添加项目根目录到Python路径
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 设置Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 初始化Django
django.setup()

import requests
import json
import time
import re
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import logging
from django.contrib.auth import get_user_model
from posts.models import Post, Tag
from posts.services import tag_service
from users.management.commands.create_test_users import Command as CreateTestUsersCommand
import random

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

User = get_user_model()

def _parse_newcoder_page(data, skip_words, start_date):
    """解析牛客网页面数据"""
    assert data['success'] == True
    pattern = re.compile("|".join(skip_words)) if skip_words else None
    res = []
    
    for x in data['data']['records']:
        x = x['data']
        dic = {"user": x['userBrief']['nickname']}

        x = x['contentData'] if 'contentData' in x else x['momentData']
        dic['title'] = x['title']
        dic['content'] = x['content']
        dic['id'] = int(x['id'])
        dic['url'] = 'https://www.nowcoder.com/discuss/' + str(x['id'])
        
        text = str(x['title']) if x['title'] else "" + str(x['content']) if x['content'] else ""
        
        # 关键词过滤
        if pattern and pattern.search(text):
            continue

        createdTime = x['createdAt'] if 'createdAt' in x else x['createTime']
        dic['createTime'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(createdTime // 1000))
        dic['editTime'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(x['editTime'] // 1000))

        # 时间过滤
        if dic['editTime'] < start_date:
            continue
            
        res.append(dic)

    return res


def get_newcoder_page(page=1, keyword="校招", skip_words=[], start_date='2023'):
    """获取牛客网单页数据"""
    header = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
        "content-type": "application/json"
    }
    data = {
        "type": "all",
        "query": keyword,
        "page": page,
        "tag": [],
        "order": "create"
    }
    
    try:
        response = requests.post(
            'https://gw-c.nowcoder.com/api/sparta/pc/search', 
            data=json.dumps(data), 
            headers=header,
            timeout=10
        )
        response.raise_for_status()
        return _parse_newcoder_page(response.json(), skip_words, start_date)
    except Exception as e:
        logger.error(f"获取牛客网页面失败: {e}")
        return []


def _batch_generate(texts, model, tokenizer, id2label={0: '招聘信息', 1: '经验贴', 2: '求助贴'}, max_length=128):
    """批量分类"""
    inputs = tokenizer(texts, return_tensors="pt", max_length=128, padding=True, truncation=True)
    outputs = model(**inputs).logits.argmax(-1).tolist()
    return [id2label[x] for x in outputs]


def model_predict(text_list, model=None, tokenizer=None, model_name="roberta4h512", batch_size=4):
    """模型预测"""
    if not text_list: 
        return []
        
    if not model:
        model_path = os.path.join(os.path.dirname(__file__), model_name)
        if os.path.exists(model_path):
            model = AutoModelForSequenceClassification.from_pretrained(model_path)
        else:
            logger.warning(f"模型路径不存在: {model_path}，跳过模型过滤")
            return ['经验贴'] * len(text_list)
            
    if not tokenizer:
        tokenizer_path = os.path.join(os.path.dirname(__file__), model_name)
        if os.path.exists(tokenizer_path):
            tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
        else:
            logger.warning(f"分词器路径不存在: {tokenizer_path}，跳过模型过滤")
            return ['经验贴'] * len(text_list)
    
    model.eval()
    result, start = [], 0
    while (start < len(text_list)):
        result.extend(_batch_generate(text_list[start: start + batch_size], model, tokenizer))
        start += batch_size
    return result


def filter_recruitment_posts(data, unique_content, model=None, tokenizer=None):
    """过滤招聘信息，保留经验贴"""
    try:
        # 模型过滤
        labels = model_predict([(str(x['title']) if x['title'] else "") + "\t" +
                               (str(x['content']) if x['content'] else "") for x in data], model, tokenizer)
        
        result = []
        for i, x in enumerate(data):
            # 跳过招聘信息和重复内容
            if x['content'] in unique_content or labels[i] == "招聘信息":
                continue
            unique_content.add(x['content'])
            result.append(x)
        
        return result
    except Exception as e:
        logger.error(f"过滤数据时出错: {e}")
        # 出错时只做去重处理
        result = []
        for x in data:
            if x['content'] not in unique_content:
                unique_content.add(x['content'])
                result.append(x)
        return result


def create_post_from_crawler_data(crawler_item):
    """将爬虫数据转换为帖子"""
    try:
        # 检查是否已存在相同标题的帖子
        if Post.objects.filter(title=crawler_item['title']).exists():
            logger.info(f"帖子已存在，跳过: {crawler_item['title']}")
            return None
        
        # 获取随机测试用户
        author = CreateTestUsersCommand.get_random_test_user()
        if not author:
            logger.error("无法获取测试用户")
            return None
        
        # 创建帖子
        post = Post.objects.create(
            title=crawler_item['title'] or "无标题",
            content=crawler_item['content'] or "无内容",
            author=author,
            likes_count=0,
            replies_count=0
        )
        
        logger.info(f"创建帖子成功: {post.id} - {post.title[:50]}")
        
        # 生成并创建标签
        try:
            tags = tag_service.create_tags_for_post(post)
            logger.info(f"为帖子 {post.id} 生成了 {len(tags)} 个标签")
        except Exception as e:
            logger.error(f"为帖子生成标签失败: {e}")
        
        return post
        
    except Exception as e:
        logger.error(f"创建帖子失败: {e}")
        return None


def save_crawler_data_as_posts(crawler_data):
    """将爬虫数据批量保存为帖子"""
    created_posts = []
    
    for item in crawler_data:
        post = create_post_from_crawler_data(item)
        if post:
            created_posts.append(post)
    
    return created_posts


def run_crawler(keywords, skip_words, max_pages=20):
    """运行爬虫主流程"""
    logger.info("开始运行面经爬虫...")
    
    # 确保测试用户存在
    try:
        from django.core.management import call_command
        call_command('create_test_users')
    except Exception as e:
        logger.warning(f"创建测试用户失败: {e}")
    
    res = []
    unique_content = set()
    
    for key in keywords:
        logger.info(f"搜索关键词: {key}")
        for i in range(1, max_pages + 1):
            logger.info(f"  处理第 {i} 页")
            
            page_data = get_newcoder_page(
                i, key, skip_words,
                start_date=time.strftime("%Y-%m-%d", time.localtime(time.time() - 15 * 24 * 60 * 60))
            )
            
            if not page_data:
                logger.info(f"  第 {i} 页无数据，停止该关键词")
                break
                
            res.extend(page_data)
            time.sleep(1)  # 避免请求过快

    # 根据内容长度排序
    res.sort(key=lambda x: len(x['content']))
    
    # 根据ID去重
    result, ids = [], set()
    for x in res:
        if x['id'] in ids:
            continue
        ids.add(x['id'])
        result.append(x)

    logger.info(f"去重后共获取 {len(result)} 条数据")

    # 使用模型过滤数据
    filtered_data = filter_recruitment_posts(result, unique_content)
    logger.info(f"过滤后剩余 {len(filtered_data)} 条经验贴")

    # 保存为帖子
    created_posts = save_crawler_data_as_posts(filtered_data)
    logger.info(f"成功创建 {len(created_posts)} 个帖子")

    return created_posts


def main():
    """主函数"""
    try:
        # 配置参数
        skip_words = [
            '求捞', '泡池子', '池子了', '池子中', 'offer对比', '总结一下', 
            '给个建议', '开奖群', '没消息', '有消息', '拉垮', '求一个', 
            '求助', '池子的', '决赛圈', 'offer比较', '求捞', '补录面经', 
            '捞捞', '收了我吧', 'offer选择', '有offer了', '想问一下', 
            'kpi吗', 'kpi面吗', 'kpi面吧'
        ]

        keywords = ['实习', '招聘', "面经"]

        # 运行爬虫
        created_posts = run_crawler(keywords, skip_words, max_pages=5)  # 限制页数避免过多数据
        
        logger.info(f"爬虫运行完成，共创建 {len(created_posts)} 个帖子")
        
        # 输出统计信息
        if created_posts:
            tag_counts = {}
            for post in created_posts:
                for tag in post.tags.all():
                    tag_type = tag.get_tag_type_display()
                    tag_counts[tag_type] = tag_counts.get(tag_type, 0) + 1
            
            logger.info("标签统计:")
            for tag_type, count in tag_counts.items():
                logger.info(f"  {tag_type}: {count}")
        
        return created_posts
        
    except Exception as e:
        logger.error(f"爬虫运行失败: {e}")
        return []


if __name__ == "__main__":
    main()
    logger.info("程序结束") 