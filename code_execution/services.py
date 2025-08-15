import json
import re
import logging
from typing import Dict, List, Any
from knowledge_base.services import KnowledgeBaseService
from .models import Problem, ProblemBank, ProblemSubmission, ProblemAnswer

logger = logging.getLogger(__name__)

class ProblemEvaluationService:
    """答题评析服务"""
    
    def __init__(self):
        self.kb_service = KnowledgeBaseService()
    
    def evaluate_multiple_problems(self, problems_and_answers: list) -> Dict[str, Dict[str, Any]]:
        """批量评析多个题目 - 减少LLM调用次数"""
        try:
            # 构建批量评析提示词
            prompt_parts = ["请对以下多个答题进行专业评析：\n"]
            
            for i, (problem, user_answer) in enumerate(problems_and_answers, 1):
                prompt_parts.append(f"""
题目{i}：{problem.title}
问题{i}：{problem.question}
参考答案{i}：{problem.reference_answer}
用户答案{i}：{user_answer}
""")
            
            prompt_parts.append("""
请按以下格式回答，每个题目用【题目X】分隔：

【题目1】
【评分】
答案完整性：X分（0-10分）
答案准确性：X分（0-10分）
思路清晰度：X分（0-10分）
专业深度：X分（0-10分）
总分：X分（0-40分）

【详细评析】
（简要分析用户答案的优缺点）

【答案优点】
（列出主要优点）

【答案不足】
（列出主要不足）

【改进建议】
（给出具体建议）

【题目2】
（同上格式）
...
""")

            prompt = "".join(prompt_parts)

            # 调用LLM服务 - 添加重试机制
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    response = self.kb_service.spark_service._send_message(prompt)
                    
                    if response:
                        # 解析批量响应
                        evaluations = self._parse_batch_evaluation_response(response, len(problems_and_answers))
                        return evaluations
                    else:
                        logger.warning(f"LLM调用返回空响应，尝试次数: {attempt + 1}")
                        
                except Exception as e:
                    logger.warning(f"LLM调用失败，尝试次数: {attempt + 1}, 错误: {str(e)}")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(1)  # 等待1秒后重试
                    continue
            
            logger.error(f"LLM调用最终失败，批量评析")
            # 返回默认评析结果
            return {str(i): {'score': 0, 'analysis': '评析解析失败'} for i in range(len(problems_and_answers))}
                
        except Exception as e:
            logger.error(f"批量评析时出错: {str(e)}")
            return {str(i): {'score': 0, 'analysis': '评析解析失败'} for i in range(len(problems_and_answers))}
    
    def evaluate_single_problem(self, problem: Problem, user_answer: str) -> Dict[str, Any]:
        """评析单个题目 - 保持向后兼容"""
        return self.evaluate_multiple_problems([(problem, user_answer)])['0']
    
    def _parse_batch_evaluation_response(self, response: str, problem_count: int) -> Dict[str, Dict[str, Any]]:
        """解析批量评析响应"""
        try:
            evaluations = {}
            
            # 分割每个题目的评析
            problem_sections = re.split(r'【题目\d+】', response)
            
            for i in range(problem_count):
                if i + 1 < len(problem_sections):
                    section = problem_sections[i + 1]
                    evaluations[str(i)] = self._parse_single_evaluation_section(section)
                else:
                    evaluations[str(i)] = self._get_default_evaluation()
            
            return evaluations
            
        except Exception as e:
            logger.error(f"解析批量评析响应时出错: {str(e)}")
            return {str(i): self._get_default_evaluation() for i in range(problem_count)}
    
    def _parse_single_evaluation_section(self, section: str) -> Dict[str, Any]:
        """解析单个题目的评析部分 - 简化版本"""
        try:
            result = {
                'score': 0,
                'analysis': ''
            }
            
            # 提取评分
            score_match = re.search(r'【评分】(\d+)分', section)
            if score_match:
                result['score'] = int(score_match.group(1))
            
            # 提取评析
            analysis_match = re.search(r'【评析】(.*?)(?=【|$)', section, re.DOTALL)
            if analysis_match:
                result['analysis'] = analysis_match.group(1).strip()
            
            # 如果没有找到评析，使用原始响应作为评析
            if not result['analysis'] and section:
                result['analysis'] = section[:500] + ('...' if len(section) > 500 else '')
            
            return result
            
        except Exception as e:
            logger.error(f"解析单个评析部分时出错: {str(e)}")
            return {'score': 0, 'analysis': '评析解析失败'}
    
    def _parse_evaluation_response(self, response: str) -> Dict[str, Any]:
        """通过规则解析评析响应 - 保持向后兼容"""
        return self._parse_single_evaluation_section(response)
    
    def evaluate_problems_with_overall_analysis(self, problems_and_answers: list, problem_bank_title: str) -> Dict[str, Any]:
        """批量评析题目并生成整体评析 - 一次LLM调用完成所有评析"""
        try:
            # 构建简化的批量评析提示词
            prompt_parts = ["请对以下答题进行评析：\n"]
            
            for i, (problem, user_answer) in enumerate(problems_and_answers, 1):
                prompt_parts.append(f"""
题目{i}：{problem.title}
问题{i}：{problem.question}
用户答案{i}：{user_answer}
""")
            
            prompt_parts.append(f"""
请按以下格式回答：

【题目1】
【评分】X分（0-40分）
【评析】（简要分析优缺点）

【题目2】
【评分】X分（0-40分）
【评析】（简要分析优缺点）

...

【整体分析】
（基于各题表现，给出整体评价和改进建议）
""")

            prompt = "".join(prompt_parts)

            # 调用LLM服务 - 添加重试机制
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    response = self.kb_service.spark_service._send_message(prompt)
                    
                    if response:
                        logger.info(f"LLM响应长度: {len(response)}")
                        logger.info(f"LLM响应前200字符: {response[:200]}")
                        # 解析包含整体评析的批量响应
                        result = self._parse_evaluation_with_overall_response(response, len(problems_and_answers))
                        logger.info(f"解析结果 - 题目数: {len(result['evaluations'])}, 整体分析: {result['overall_analysis'][:50]}...")
                        return result
                    else:
                        logger.warning(f"LLM调用返回空响应，尝试次数: {attempt + 1}")
                        
                except Exception as e:
                    logger.warning(f"LLM调用失败，尝试次数: {attempt + 1}, 错误: {str(e)}")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(1)  # 等待1秒后重试
                    continue
            
            logger.error(f"LLM调用最终失败，批量评析")
            # 返回默认结果
            default_evaluations = {str(i): {'score': 0, 'analysis': '评析解析失败'} for i in range(len(problems_and_answers))}
            return {
                'evaluations': default_evaluations,
                'overall_analysis': "整体表现良好，各题得分较为均衡"
            }
                
        except Exception as e:
            logger.error(f"批量评析时出错: {str(e)}")
            default_evaluations = {str(i): {'score': 0, 'analysis': '评析解析失败'} for i in range(len(problems_and_answers))}
            return {
                'evaluations': default_evaluations,
                'overall_analysis': "整体表现良好，各题得分较为均衡"
            }
    
    def generate_overall_analysis(self, submission: ProblemSubmission) -> Dict[str, str]:
        """生成整体评析 - 保持向后兼容"""
        try:
            # 获取所有答题记录
            answers = submission.answers.all()
            
            # 构建简化的整体评析提示词
            score_summary = []
            for answer in answers:
                score_summary.append(f"{answer.problem.title}: {answer.score}/{answer.max_score}分")
            
            prompt = f"""请对以下答题记录进行整体评析：

题库：{submission.problem_bank.title}
总题数：{submission.total_problems}
正确题数：{submission.correct_count}
总分：{submission.total_score}

各题得分：{', '.join(score_summary)}

请按以下格式回答：

【整体表现评价】
（简要评价整体表现）

【改进建议】
（给出主要改进建议）
"""

            # 调用LLM服务 - 添加重试机制
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    response = self.kb_service.spark_service._send_message(prompt)
                    
                    if response:
                        # 通过规则解析响应
                        analysis = self._parse_overall_analysis_response(response)
                        return analysis
                    else:
                        logger.warning(f"LLM调用返回空响应，尝试次数: {attempt + 1}")
                        
                except Exception as e:
                    logger.warning(f"LLM调用失败，尝试次数: {attempt + 1}, 错误: {str(e)}")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(1)  # 等待1秒后重试
                    continue
            
            logger.error(f"LLM调用最终失败，提交ID: {submission.id}")
            return self._get_default_overall_analysis()
                
        except Exception as e:
            logger.error(f"生成整体评析时出错: {str(e)}")
            return self._get_default_overall_analysis()
    
    def _parse_evaluation_with_overall_response(self, response: str, problem_count: int) -> Dict[str, Any]:
        """解析简化的批量评析响应"""
        try:
            evaluations = {}
            
            # 解析每个题目的评析
            for i in range(problem_count):
                # 查找题目i的评分
                score_match = re.search(f'【题目{i+1}】\s*【评分】(\d+)分', response)
                score = int(score_match.group(1)) if score_match else 0
                
                # 查找题目i的评析
                analysis_match = re.search(f'【题目{i+1}】\s*【评分】\d+分\s*【评析】(.*?)(?=【题目|【整体分析】|$)', response, re.DOTALL)
                analysis = analysis_match.group(1).strip() if analysis_match else "评析内容解析失败"
                
                evaluations[str(i)] = {
                    'score': score,
                    'analysis': analysis
                }
            
            # 查找整体分析
            overall_match = re.search(r'【整体分析】\s*(.*?)(?=【|$)', response, re.DOTALL)
            overall_analysis = overall_match.group(1).strip() if overall_match else "整体表现良好，各题得分较为均衡"
            
            return {
                'evaluations': evaluations,
                'overall_analysis': overall_analysis
            }
            
        except Exception as e:
            logger.error(f"解析评析响应时出错: {str(e)}")
            default_evaluations = {str(i): {'score': 0, 'analysis': '评析解析失败'} for i in range(problem_count)}
            return {
                'evaluations': default_evaluations,
                'overall_analysis': "整体表现良好，各题得分较为均衡"
            }
    
    def _parse_overall_analysis_response(self, response: str) -> Dict[str, str]:
        """通过规则解析整体评析响应 - 简化版本"""
        try:
            result = {
                'overall_analysis': ''
            }
            
            # 提取整体分析
            overall_match = re.search(r'【整体分析】\s*(.*?)(?=【|$)', response, re.DOTALL)
            if overall_match:
                result['overall_analysis'] = overall_match.group(1).strip()
            
            # 如果没有找到任何内容，使用默认值
            if not result['overall_analysis']:
                result['overall_analysis'] = "整体表现良好，各题得分较为均衡"
            
            return result
            
        except Exception as e:
            logger.error(f"解析整体评析响应时出错: {str(e)}")
            return self._get_default_overall_analysis()
    
    def _get_default_evaluation(self) -> Dict[str, Any]:
        """获取默认评析结果 - 简化版本"""
        return {
            'score': 0,
            'analysis': '评析服务暂时不可用，请稍后重试'
        }
    
    def _get_default_overall_analysis(self) -> Dict[str, str]:
        """获取默认整体评析 - 简化版本"""
        return {
            'overall_analysis': '整体表现良好，各题得分较为均衡'
        }
