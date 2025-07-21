import requests
import json
import time
import hashlib
import base64
import hmac
from urllib.parse import urlencode
from datetime import datetime, timezone
from django.conf import settings
from .models import Tag, Post
import re
import logging

logger = logging.getLogger(__name__)

class XunfeiTagService:
    """讯飞大模型标签生成服务"""
    
    def __init__(self):
        self.app_id = getattr(settings, 'XUNFEI_APP_ID', '')
        self.api_secret = getattr(settings, 'XUNFEI_API_SECRET', '')
        self.api_key = getattr(settings, 'XUNFEI_API_KEY', '')
        
        if not all([self.app_id, self.api_secret, self.api_key]):
            logger.warning("讯飞API配置不完整，请在local_settings.py中配置")
    
    def generate_auth_url(self):
        """生成认证URL"""
        host = "spark-api.xf-yun.com"
        path = "/v3.1/chat/completions"
        url = f"wss://{host}{path}"
        
        # 生成RFC1123格式的时间戳
        now = datetime.now(timezone.utc)
        date = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # 拼接字符串
        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
        
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        
        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')
        
        authorization_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": host
        }
        
        # 拼接鉴权参数，生成url
        url = url + '?' + urlencode(v)
        return url
    
    def generate_tags_from_content(self, title, content):
        """
        使用讯飞大模型从帖子标题和内容中生成标签
        返回: {'companies': [], 'positions': [], 'skills': [], 'industries': [], 'levels': []}
        """
        if not all([self.app_id, self.api_secret, self.api_key]):
            logger.error("讯飞API配置不完整")
            return self._fallback_extract_tags(title, content)
        
        try:
            # 构建提示词
            prompt = self._build_tag_extraction_prompt(title, content)
            
            # 调用讯飞API
            result = self._call_xunfei_api(prompt)
            
            # 解析结果
            tags = self._parse_tag_result(result)
            
            return tags
            
        except Exception as e:
            logger.error(f"讯飞大模型调用失败: {e}")
            return self._fallback_extract_tags(title, content)
    
    def _build_tag_extraction_prompt(self, title, content):
        """构建标签提取的提示词"""
        prompt = f"""
请从以下面试经验分享的标题和内容中提取相关标签信息，并按照指定格式返回JSON：

标题：{title}
内容：{content[:500]}  # 截取前500字符避免过长

请提取以下类型的标签：
1. 公司名称（如：阿里巴巴、腾讯、字节跳动等）
2. 岗位名称（如：前端工程师、Java开发、产品经理等）
3. 技能要求（如：Python、MySQL、算法、设计模式等）
4. 行业分类（如：互联网、金融、教育等）
5. 级别要求（如：实习、校招、社招、高级等）

返回格式严格按照以下JSON格式：
{{
    "companies": ["公司1", "公司2"],
    "positions": ["岗位1", "岗位2"],
    "skills": ["技能1", "技能2", "技能3"],
    "industries": ["行业1"],
    "levels": ["级别1"]
}}

注意：
- 只返回JSON，不要其他文字
- 如果某个类型没有相关信息，返回空数组
- 公司名称要准确，避免简称
- 技能要具体化，避免过于宽泛
"""
        return prompt
    
    def _call_xunfei_api(self, prompt):
        """调用讯飞API（使用HTTP接口）"""
        url = "https://spark-api-open.xf-yun.com/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "generalv3.5",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1024,
            "temperature": 0.1,
            "stream": False
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            else:
                raise Exception("API返回格式错误")
                
        except Exception as e:
            logger.error(f"讯飞API调用失败: {e}")
            raise
    
    def _parse_tag_result(self, result):
        """解析讯飞大模型返回的标签结果"""
        try:
            # 尝试从结果中提取JSON
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                tags = json.loads(json_str)
                
                # 验证并清理数据
                cleaned_tags = {
                    'companies': [tag.strip() for tag in tags.get('companies', []) if tag.strip()],
                    'positions': [tag.strip() for tag in tags.get('positions', []) if tag.strip()],
                    'skills': [tag.strip() for tag in tags.get('skills', []) if tag.strip()],
                    'industries': [tag.strip() for tag in tags.get('industries', []) if tag.strip()],
                    'levels': [tag.strip() for tag in tags.get('levels', []) if tag.strip()],
                }
                
                return cleaned_tags
            else:
                raise ValueError("无法从结果中提取JSON")
                
        except Exception as e:
            logger.error(f"解析标签结果失败: {e}")
            return {
                'companies': [],
                'positions': [],
                'skills': [],
                'industries': [],
                'levels': []
            }
    
    def _fallback_extract_tags(self, title, content):
        """备用标签提取方法（基于关键词匹配）"""
        text = f"{title} {content}".lower()
        
        # 定义常见的标签关键词
        company_keywords = ['阿里', '腾讯', '字节', '美团', '滴滴', '京东', '百度', '网易', '小米', '华为']
        position_keywords = ['前端', '后端', 'java', 'python', '产品', '运营', '测试', '算法', 'ai', '数据']
        skill_keywords = ['mysql', 'redis', 'spring', 'vue', 'react', 'docker', 'kubernetes', 'git']
        industry_keywords = ['互联网', '金融', '教育', '医疗', '电商', '游戏']
        level_keywords = ['实习', '校招', '社招', '应届', '经验']
        
        result = {
            'companies': [kw for kw in company_keywords if kw in text],
            'positions': [kw for kw in position_keywords if kw in text],
            'skills': [kw for kw in skill_keywords if kw in text],
            'industries': [kw for kw in industry_keywords if kw in text],
            'levels': [kw for kw in level_keywords if kw in text]
        }
        
        return result
    
    def create_tags_for_post(self, post):
        """为帖子创建标签"""
        try:
            # 生成标签
            tag_data = self.generate_tags_from_content(post.title, post.content)
            
            created_tags = []
            
            # 创建各类型标签
            tag_type_mapping = {
                'companies': 'company',
                'positions': 'position', 
                'skills': 'skill',
                'industries': 'industry',
                'levels': 'level'
            }
            
            for key, tag_type in tag_type_mapping.items():
                for tag_name in tag_data.get(key, []):
                    tag, created = Tag.objects.get_or_create(
                        name=tag_name,
                        tag_type=tag_type,
                        defaults={'description': f'自动生成的{tag_type}标签'}
                    )
                    created_tags.append(tag)
                    if created:
                        logger.info(f"创建新标签: [{tag.get_tag_type_display()}] {tag.name}")
            
            # 关联标签到帖子
            if created_tags:
                post.tags.set(created_tags)
                logger.info(f"为帖子 {post.id} 设置了 {len(created_tags)} 个标签")
            
            return created_tags
            
        except Exception as e:
            logger.error(f"为帖子创建标签失败: {e}")
            return []


# 服务实例
tag_service = XunfeiTagService() 