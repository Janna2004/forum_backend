import json
import re
import logging
from typing import Dict, List, Any
from knowledge_base.services import KnowledgeBaseService

logger = logging.getLogger(__name__)

class PersonalizedRecommendationService:
    """个性化路径推荐服务"""
    
    def __init__(self):
        self.kb_service = KnowledgeBaseService()
    
    def get_personalized_recommendations(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """获取个性化推荐"""
        try:
            # 构建推荐提示词
            prompt = self._build_recommendation_prompt(user_profile)
            
            # 调用LLM服务
            response = self.kb_service.spark_service._send_message(prompt)
            
            if response:
                # 解析LLM响应
                recommendations = self._parse_recommendation_response(response)
                return recommendations
            else:
                logger.warning("LLM调用返回空响应")
                return self._get_default_recommendations()
                
        except Exception as e:
            logger.error(f"获取个性化推荐时出错: {str(e)}")
            return self._get_default_recommendations()
    
    def _build_recommendation_prompt(self, user_profile: Dict[str, Any]) -> str:
        """构建推荐提示词"""
        target_position = user_profile.get('target_position', {})
        position_name = target_position.get('position_name', '前端开发工程师')
        company_name = target_position.get('company_name', '')
        salary_range = target_position.get('expected_salary', [])
        
        salary_text = f"{salary_range[0]}-{salary_range[1]}K" if salary_range and len(salary_range) == 2 else "面议"
        
        prompt = f"""请根据用户信息推荐个性化的职业发展路径：

用户信息：
- 目标岗位：{position_name}
- 目标公司：{company_name}
- 期望薪资：{salary_text}

请推荐：
1. 5个匹配的公司-岗位组合
2. 5个匹配的题库

请按以下JSON格式返回：

{{
  "currentGoal": {{
    "title": "{position_name}",
    "company": "{company_name}",
    "salary": "{salary_text}",
    "matchRate": 85
  }},
  "recommendedCompanies": [
    {{
      "name": "公司名称",
      "matchRate": 85,
      "position": "岗位名称"
    }}
  ],
  "recommendedTopics": [
    {{
      "name": "题库名称",
      "difficulty": "难度",
      "matchRate": 90,
      "count": 150
    }}
  ]
}}

注意：
- matchRate为匹配度，范围0-100
- 题库难度为：简单、中等、困难
- 题库count为题目数量
- 只返回JSON格式，不要其他内容
"""
        return prompt
    
    def _parse_recommendation_response(self, response: str) -> Dict[str, Any]:
        """解析推荐响应"""
        try:
            # 尝试直接解析JSON
            try:
                # 查找JSON部分
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
            
            # 如果直接解析失败，使用规则解析
            return self._parse_recommendation_by_rules(response)
            
        except Exception as e:
            logger.error(f"解析推荐响应时出错: {str(e)}")
            return self._get_default_recommendations()
    
    def _parse_recommendation_by_rules(self, response: str) -> Dict[str, Any]:
        """使用规则解析推荐响应"""
        try:
            result = {
                "currentGoal": {
                    "title": "前端开发工程师",
                    "company": "字节跳动",
                    "salary": "25-35K",
                    "matchRate": 85
                },
                "recommendedCompanies": [],
                "recommendedTopics": []
            }
            
            # 解析推荐公司
            companies_section = re.search(r'"recommendedCompanies":\s*\[(.*?)\]', response, re.DOTALL)
            if companies_section:
                companies_text = companies_section.group(1)
                company_matches = re.findall(r'\{[^}]+\}', companies_text)
                
                for company_match in company_matches[:5]:  # 最多5个
                    name_match = re.search(r'"name":\s*"([^"]+)"', company_match)
                    match_rate_match = re.search(r'"matchRate":\s*(\d+)', company_match)
                    position_match = re.search(r'"position":\s*"([^"]+)"', company_match)
                    
                    if name_match and match_rate_match and position_match:
                        result["recommendedCompanies"].append({
                            "name": name_match.group(1),
                            "matchRate": int(match_rate_match.group(1)),
                            "position": position_match.group(1)
                        })
            
            # 解析推荐题库
            topics_section = re.search(r'"recommendedTopics":\s*\[(.*?)\]', response, re.DOTALL)
            if topics_section:
                topics_text = topics_section.group(1)
                topic_matches = re.findall(r'\{[^}]+\}', topics_text)
                
                for topic_match in topic_matches[:5]:  # 最多5个
                    name_match = re.search(r'"name":\s*"([^"]+)"', topic_match)
                    difficulty_match = re.search(r'"difficulty":\s*"([^"]+)"', topic_match)
                    match_rate_match = re.search(r'"matchRate":\s*(\d+)', topic_match)
                    count_match = re.search(r'"count":\s*(\d+)', topic_match)
                    
                    if name_match and difficulty_match and match_rate_match and count_match:
                        result["recommendedTopics"].append({
                            "name": name_match.group(1),
                            "difficulty": difficulty_match.group(1),
                            "matchRate": int(match_rate_match.group(1)),
                            "count": int(count_match.group(1))
                        })
            
            # 如果解析结果为空，使用默认值
            if not result["recommendedCompanies"]:
                result["recommendedCompanies"] = self._get_default_companies()
            
            if not result["recommendedTopics"]:
                result["recommendedTopics"] = self._get_default_topics()
            
            return result
            
        except Exception as e:
            logger.error(f"规则解析推荐响应时出错: {str(e)}")
            return self._get_default_recommendations()
    
    def _get_default_recommendations(self) -> Dict[str, Any]:
        """获取默认推荐"""
        return {
            "currentGoal": {
                "title": "前端开发工程师",
                "company": "字节跳动",
                "salary": "25-35K",
                "matchRate": 85
            },
            "recommendedCompanies": self._get_default_companies(),
            "recommendedTopics": self._get_default_topics()
        }
    
    def _get_default_companies(self) -> List[Dict[str, Any]]:
        """获取默认推荐公司"""
        return [
            {"name": "字节跳动", "matchRate": 85, "position": "前端开发工程师"},
            {"name": "阿里巴巴", "matchRate": 82, "position": "前端开发工程师"},
            {"name": "腾讯", "matchRate": 78, "position": "前端开发工程师"},
            {"name": "美团", "matchRate": 75, "position": "前端开发工程师"},
            {"name": "滴滴", "matchRate": 72, "position": "前端开发工程师"}
        ]
    
    def _get_default_topics(self) -> List[Dict[str, Any]]:
        """获取默认推荐题库"""
        return [
            {"name": "React高级特性", "difficulty": "困难", "matchRate": 90, "count": 150},
            {"name": "TypeScript实战", "difficulty": "中等", "matchRate": 88, "count": 120},
            {"name": "前端性能优化", "difficulty": "困难", "matchRate": 85, "count": 189},
            {"name": "Vue3生态", "difficulty": "中等", "matchRate": 82, "count": 167},
            {"name": "微前端架构", "difficulty": "困难", "matchRate": 80, "count": 98}
        ]
