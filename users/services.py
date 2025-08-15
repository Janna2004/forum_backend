import json
import re
import logging
from typing import Dict, List, Any
from knowledge_base.services import KnowledgeBaseService
from positions.models import NowCoderPosition
from code_execution.models import ProblemBank

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
                # 用真实数据替换推荐的公司和题库
                recommendations = self._enhance_with_real_data(recommendations, user_profile)
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
    
    def _enhance_with_real_data(self, recommendations: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """用真实数据增强推荐结果"""
        try:
            target_position = user_profile.get('target_position', {})
            position_name = target_position.get('position_name', '')
            
            print(f"增强推荐数据 - 岗位名称: {position_name}")
            
            # 获取真实的岗位数据
            real_companies = self._get_real_companies(position_name)
            print(f"获取到 {len(real_companies)} 个真实公司数据")
            if real_companies:
                recommendations['recommendedCompanies'] = real_companies
            
            # 获取真实的题库数据
            real_topics = self._get_real_topics(position_name)
            print(f"获取到 {len(real_topics)} 个真实题库数据")
            if real_topics:
                recommendations['recommendedTopics'] = real_topics
            
            return recommendations
            
        except Exception as e:
            logger.error(f"增强推荐数据时出错: {str(e)}")
            return recommendations
    
    def _get_real_companies(self, position_name: str) -> List[Dict[str, Any]]:
        """获取真实的公司岗位数据"""
        try:
            print(f"查询公司数据 - 岗位名称: {position_name}")
            
            companies = []
            seen_companies = set()
            
            # 策略1：根据岗位名称进行模糊搜索
            if position_name:
                # 提取关键词进行搜索
                keywords = self._extract_keywords(position_name)
                print(f"提取的关键词: {keywords}")
                
                for keyword in keywords:
                    if len(companies) >= 5:
                        break
                        
                    positions = NowCoderPosition.objects.filter(
                        job_name__icontains=keyword
                    ).order_by('-id')[:20]  # 获取更多候选
                    
                    print(f"关键词 '{keyword}' 搜索，找到 {positions.count()} 个岗位")
                    
                    for position in positions:
                        if position.company in seen_companies:
                            continue
                        
                        if len(companies) >= 5:
                            break
                        
                        companies.append({
                            "name": position.company,
                            "matchRate": 85 - len(companies) * 3,
                            "position": position.job_name
                        })
                        seen_companies.add(position.company)
            
            # 策略2：如果还不够5个，获取一些热门岗位
            if len(companies) < 5:
                remaining_count = 5 - len(companies)
                positions = NowCoderPosition.objects.all().order_by('-id')[:50]
                
                for position in positions:
                    if position.company in seen_companies:
                        continue
                    
                    if len(companies) >= 5:
                        break
                    
                    companies.append({
                        "name": position.company,
                        "matchRate": 85 - len(companies) * 3,
                        "position": position.job_name
                    })
                    seen_companies.add(position.company)
            
            print(f"最终获取到 {len(companies)} 个公司数据")
            return companies
            
        except Exception as e:
            logger.error(f"获取真实公司数据时出错: {str(e)}")
            return []
    
    def _get_real_topics(self, position_name: str) -> List[Dict[str, Any]]:
        """获取真实的题库数据"""
        try:
            print(f"查询题库数据 - 岗位名称: {position_name}")
            
            topics = []
            
            # 策略1：根据岗位类型匹配题库
            position_type = self._get_position_type(position_name)
            print(f"推断岗位类型: {position_type}")
            
            # 获取相关题库
            problem_banks = ProblemBank.objects.filter(
                category__icontains=position_type
            ).order_by('-created_at')[:20]
            print(f"岗位类型 '{position_type}' 搜索，找到 {problem_banks.count()} 个相关题库")
            
            for bank in problem_banks:
                if len(topics) >= 5:
                    break
                
                topics.append({
                    "name": bank.title,
                    "difficulty": bank.difficulty,
                    "matchRate": 90 - len(topics) * 2,
                    "count": bank.real_problem_count
                })
            
            # 策略2：如果还不够5个，获取一些通用题库
            if len(topics) < 5:
                remaining_count = 5 - len(topics)
                all_banks = ProblemBank.objects.all().order_by('-created_at')[:50]
                
                for bank in all_banks:
                    if len(topics) >= 5:
                        break
                    
                    # 检查是否已经添加过
                    if any(topic['name'] == bank.title for topic in topics):
                        continue
                    
                    topics.append({
                        "name": bank.title,
                        "difficulty": bank.difficulty,
                        "matchRate": 90 - len(topics) * 2,
                        "count": bank.real_problem_count
                    })
            
            print(f"最终获取到 {len(topics)} 个题库数据")
            return topics
            
        except Exception as e:
            logger.error(f"获取真实题库数据时出错: {str(e)}")
            return []
    
    def _extract_keywords(self, position_name: str) -> List[str]:
        """从岗位名称中提取关键词"""
        if not position_name:
            return []
        
        keywords = []
        position_name_lower = position_name.lower()
        
        # 技术关键词
        tech_keywords = [
            'java', 'python', 'go', 'golang', 'c++', 'c#', 'javascript', 'js', 'typescript', 'ts',
            'react', 'vue', 'angular', 'nodejs', 'node.js', 'spring', 'django', 'flask', 'express',
            'mysql', 'postgresql', 'mongodb', 'redis', 'docker', 'kubernetes', 'k8s', 'aws', 'azure',
            '算法', '机器学习', 'ml', 'ai', '深度学习', '数据挖掘', '大数据', 'hadoop', 'spark'
        ]
        
        # 岗位类型关键词
        position_keywords = [
            '后端', 'backend', '前端', 'frontend', '全栈', 'fullstack', '算法', 'algorithm',
            '测试', 'test', 'qa', '运维', 'devops', '产品', 'product', 'pm', '数据', 'data',
            '实习', 'intern', '应届', '校招', '社招', '初级', '中级', '高级', '资深', '专家'
        ]
        
        # 提取技术关键词
        for keyword in tech_keywords:
            if keyword in position_name_lower:
                keywords.append(keyword)
        
        # 提取岗位类型关键词
        for keyword in position_keywords:
            if keyword in position_name_lower:
                keywords.append(keyword)
        
        # 如果没有找到关键词，使用一些通用关键词
        if not keywords:
            keywords = ['后端', '开发', '工程师', '实习']
        
        # 去重并限制数量
        keywords = list(set(keywords))[:5]
        
        return keywords
    
    def _get_position_type(self, position_name: str) -> str:
        """根据岗位名称推断岗位类型"""
        if not position_name:
            return "后端开发"
        
        position_name_lower = position_name.lower()
        
        if any(keyword in position_name_lower for keyword in ['前端', 'frontend', 'react', 'vue', 'javascript', 'js']):
            return "前端开发"
        elif any(keyword in position_name_lower for keyword in ['后端', 'backend', 'java', 'python', 'go', 'nodejs']):
            return "后端开发"
        elif any(keyword in position_name_lower for keyword in ['算法', 'algorithm', '机器学习', 'ml', 'ai']):
            return "算法设计"
        elif any(keyword in position_name_lower for keyword in ['测试', 'test', 'qa']):
            return "测试开发"
        elif any(keyword in position_name_lower for keyword in ['产品', 'product', 'pm']):
            return "产品经理"
        elif any(keyword in position_name_lower for keyword in ['数据', 'data', '数据分析']):
            return "数据分析"
        else:
            return "后端开发"  # 默认
    
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
        try:
            # 尝试获取真实数据作为默认推荐
            real_companies = self._get_real_companies("")
            real_topics = self._get_real_topics("")
            
            return {
                "currentGoal": {
                    "title": "前端开发工程师",
                    "company": "字节跳动",
                    "salary": "25-35K",
                    "matchRate": 85
                },
                "recommendedCompanies": real_companies if real_companies else self._get_default_companies(),
                "recommendedTopics": real_topics if real_topics else self._get_default_topics()
            }
        except Exception as e:
            logger.error(f"获取默认推荐时出错: {str(e)}")
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
