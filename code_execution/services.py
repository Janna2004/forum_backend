import json
import re
import logging
import subprocess
import tempfile
import os
from typing import Dict, List, Any, Tuple
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
                    evaluation = self._parse_single_evaluation(section)
                    evaluations[str(i)] = evaluation
                else:
                    evaluations[str(i)] = {'score': 0, 'analysis': '解析失败'}
            
            return evaluations
            
        except Exception as e:
            logger.error(f"解析批量评析响应失败: {str(e)}")
            return {str(i): {'score': 0, 'analysis': '解析失败'} for i in range(problem_count)}
    
    def _parse_single_evaluation(self, section: str) -> Dict[str, Any]:
        """解析单个题目的评析"""
        try:
            # 提取总分
            score_match = re.search(r'总分：(\d+)分', section)
            score = int(score_match.group(1)) if score_match else 0
            
            # 提取详细评析
            analysis_match = re.search(r'【详细评析】\n(.*?)(?=\n【|$)', section, re.DOTALL)
            analysis = analysis_match.group(1).strip() if analysis_match else ''
            
            # 提取优点
            strengths_match = re.search(r'【答案优点】\n(.*?)(?=\n【|$)', section, re.DOTALL)
            strengths = strengths_match.group(1).strip() if strengths_match else ''
            
            # 提取不足
            weaknesses_match = re.search(r'【答案不足】\n(.*?)(?=\n【|$)', section, re.DOTALL)
            weaknesses = weaknesses_match.group(1).strip() if weaknesses_match else ''
            
            # 提取建议
            suggestions_match = re.search(r'【改进建议】\n(.*?)(?=\n【|$)', section, re.DOTALL)
            suggestions = suggestions_match.group(1).strip() if suggestions_match else ''
            
            return {
                'score': score,
                'analysis': analysis,
                'strengths': strengths,
                'weaknesses': weaknesses,
                'suggestions': suggestions
            }
            
        except Exception as e:
            logger.error(f"解析单个评析失败: {str(e)}")
            return {'score': 0, 'analysis': '解析失败'}

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
            # 返回默认评析结果
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
                score_match = re.search(f'【题目{i+1}】\\s*【评分】(\\d+)分', response)
                score = int(score_match.group(1)) if score_match else 0
                
                # 查找题目i的评析
                analysis_match = re.search(f'【题目{i+1}】\\s*【评分】\\d+分\\s*【评析】(.*?)(?=【题目|【整体分析】|$)', response, re.DOTALL)
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

    def _get_default_overall_analysis(self) -> Dict[str, str]:
        """获取默认整体评析 - 简化版本"""
        return {
            'overall_analysis': '整体表现良好，各题得分较为均衡'
        }

class CodeEvaluationService:
    """代码题答案评析服务"""
    
    def __init__(self):
        self.kb_service = KnowledgeBaseService()
    
    def evaluate_code_answers(self, problem_answers: List[Dict]) -> Dict[str, Any]:
        """
        批量评析代码题答案
        
        Args:
            problem_answers: 包含题目ID、源代码的列表
            [
                {
                    "problem_id": "algo-001",
                    "source_code": "def twoSum(nums, target):..."
                }
            ]
        
        Returns:
            评析结果
        """
        try:
            # 1. 获取题目信息和测试用例
            problems_data = []
            for answer in problem_answers:
                problem_id = answer['problem_id']
                source_code = answer['source_code']
                
                try:
                    problem = Problem.objects.get(id=problem_id)
                    if not problem.is_algorithm:
                        continue
                    
                    # 运行测试用例
                    test_results = self._run_test_cases(problem, source_code)
                    
                    problems_data.append({
                        'problem': problem,
                        'source_code': source_code,
                        'test_results': test_results
                    })
                    
                except Problem.DoesNotExist:
                    logger.warning(f"题目不存在: {problem_id}")
                    continue
            
            if not problems_data:
                return {
                    'success': False,
                    'error': '没有找到有效的算法题目'
                }
            
            # 2. 构建批量评析提示词
            prompt = self._build_evaluation_prompt(problems_data)
            
            # 3. 调用LLM进行评析
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    response = self.kb_service.spark_service._send_message(prompt)
                    if response:
                        # 4. 解析评析结果
                        evaluation_results = self._parse_evaluation_response(response, problems_data)
                        return {
                            'success': True,
                            'results': evaluation_results
                        }
                    else:
                        logger.warning(f"LLM调用返回空响应，尝试次数: {attempt + 1}")
                        
                except Exception as e:
                    logger.warning(f"LLM调用失败，尝试次数: {attempt + 1}, 错误: {str(e)}")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(1)
                    continue
            
            return {
                'success': False,
                'error': 'LLM调用失败'
            }
            
        except Exception as e:
            logger.error(f"代码评析失败: {str(e)}")
            return {
                'success': False,
                'error': f'评析失败: {str(e)}'
            }
    
    def _run_test_cases(self, problem: Problem, source_code: str) -> Dict[str, Any]:
        """运行测试用例"""
        try:
            test_cases = problem.algorithm_test_cases
            if not test_cases:
                return {'error': '题目没有测试用例'}
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                # 写入代码模板和用户代码
                code_template = problem.algorithm_code_template or ""
                full_code = f"{code_template}\n{source_code}\n"
                f.write(full_code)
                temp_file = f.name
            
            try:
                results = {
                    'public_cases': [],
                    'hidden_cases': [],
                    'summary': {
                        'public_passed': 0,
                        'public_total': 0,
                        'hidden_passed': 0,
                        'hidden_total': 0
                    }
                }
                
                # 运行公开测试用例
                if 'public' in test_cases:
                    for i, case in enumerate(test_cases['public']):
                        case_result = self._run_single_test_case(temp_file, case)
                        results['public_cases'].append(case_result)
                        results['summary']['public_total'] += 1
                        if case_result['passed']:
                            results['summary']['public_passed'] += 1
                
                # 运行隐藏测试用例
                if 'hidden' in test_cases:
                    for i, case in enumerate(test_cases['hidden']):
                        case_result = self._run_single_test_case(temp_file, case)
                        results['hidden_cases'].append(case_result)
                        results['summary']['hidden_total'] += 1
                        if case_result['passed']:
                            results['summary']['hidden_passed'] += 1
                
                return results
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    
        except Exception as e:
            logger.error(f"运行测试用例失败: {str(e)}")
            return {'error': f'运行测试用例失败: {str(e)}'}
    
    def _run_single_test_case(self, code_file: str, test_case: Dict) -> Dict[str, Any]:
        """运行单个测试用例"""
        try:
            # 构建测试输入
            input_data = test_case.get('input', '')
            expected_output = test_case.get('output', '')
            
            # 运行代码
            result = subprocess.run(
                ['python', code_file],
                input=input_data.encode(),
                capture_output=True,
                timeout=5  # 5秒超时
            )
            
            actual_output = result.stdout.decode().strip()
            error_output = result.stderr.decode().strip()
            
            # 判断是否通过
            passed = actual_output == expected_output
            
            return {
                'input': input_data,
                'expected': expected_output,
                'actual': actual_output,
                'error': error_output,
                'passed': passed
            }
            
        except subprocess.TimeoutExpired:
            return {
                'input': test_case.get('input', ''),
                'expected': test_case.get('output', ''),
                'actual': '',
                'error': '执行超时',
                'passed': False
            }
        except Exception as e:
            return {
                'input': test_case.get('input', ''),
                'expected': test_case.get('output', ''),
                'actual': '',
                'error': f'执行错误: {str(e)}',
                'passed': False
            }
    
    def _build_evaluation_prompt(self, problems_data: List[Dict]) -> str:
        """构建评析提示词"""
        prompt_parts = [
            "请对以下代码题答案进行专业评析，重点关注代码正确性、算法效率和代码质量：\n\n"
        ]
        
        for i, data in enumerate(problems_data, 1):
            problem = data['problem']
            source_code = data['source_code']
            test_results = data['test_results']
            
            # 计算通过率
            public_rate = 0
            hidden_rate = 0
            if test_results['summary']['public_total'] > 0:
                public_rate = test_results['summary']['public_passed'] / test_results['summary']['public_total']
            if test_results['summary']['hidden_total'] > 0:
                hidden_rate = test_results['summary']['hidden_passed'] / test_results['summary']['hidden_total']
            
            prompt_parts.append(f"""
题目{i}：{problem.title}
题目描述：{problem.description}
用户代码：
{source_code}

测试结果：
公开测试用例通过率：{public_rate:.1%} ({test_results['summary']['public_passed']}/{test_results['summary']['public_total']})
隐藏测试用例通过率：{hidden_rate:.1%} ({test_results['summary']['hidden_passed']}/{test_results['summary']['hidden_total']})

""")
        
        prompt_parts.append("""
请按以下格式输出评析结果，每个题目用【题目X】分隔：

【题目1】
【评分】
代码正确性：X分（0-10分，基于测试用例通过情况）
算法效率：X分（0-10分，时间空间复杂度）
代码质量：X分（0-10分，可读性、规范性）
总分：X分（0-30分）

【测试分析】
（分析测试用例通过情况，指出问题所在）

【代码优点】
（列出代码的主要优点）

【代码问题】
（列出代码的主要问题）

【改进建议】
（给出具体的改进建议和优化思路）

【题目2】
（同上格式）
...

注意：输出要简洁明了，每个部分不超过50字。
""")
        
        return "".join(prompt_parts)
    
    def _parse_evaluation_response(self, response: str, problems_data: List[Dict]) -> List[Dict[str, Any]]:
        """解析评析响应"""
        try:
            results = []
            
            # 分割每个题目的评析
            problem_sections = re.split(r'【题目\d+】', response)
            
            for i, data in enumerate(problems_data):
                if i + 1 < len(problem_sections):
                    section = problem_sections[i + 1]
                    evaluation = self._parse_single_code_evaluation(section)
                    
                    # 合并测试结果和评析结果
                    result = {
                        'problem_id': data['problem'].id,
                        'problem_title': data['problem'].title,
                        'test_results': data['test_results'],
                        'evaluation': evaluation
                    }
                    results.append(result)
                else:
                    # 解析失败，使用默认结果
                    result = {
                        'problem_id': data['problem'].id,
                        'problem_title': data['problem'].title,
                        'test_results': data['test_results'],
                        'evaluation': {
                            'score': 0,
                            'test_analysis': '评析解析失败',
                            'strengths': '',
                            'problems': '',
                            'suggestions': ''
                        }
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"解析代码评析响应失败: {str(e)}")
            # 返回默认结果
            return [{
                'problem_id': data['problem'].id,
                'problem_title': data['problem'].title,
                'test_results': data['test_results'],
                'evaluation': {
                    'score': 0,
                    'test_analysis': '评析解析失败',
                    'strengths': '',
                    'problems': '',
                    'suggestions': ''
                }
            } for data in problems_data]
    
    def _parse_single_code_evaluation(self, section: str) -> Dict[str, Any]:
        """解析单个代码评析"""
        try:
            # 提取总分
            score_match = re.search(r'总分：(\d+)分', section)
            score = int(score_match.group(1)) if score_match else 0
            
            # 提取测试分析
            test_analysis_match = re.search(r'【测试分析】\n(.*?)(?=\n【|$)', section, re.DOTALL)
            test_analysis = test_analysis_match.group(1).strip() if test_analysis_match else ''
            
            # 提取代码优点
            strengths_match = re.search(r'【代码优点】\n(.*?)(?=\n【|$)', section, re.DOTALL)
            strengths = strengths_match.group(1).strip() if strengths_match else ''
            
            # 提取代码问题
            problems_match = re.search(r'【代码问题】\n(.*?)(?=\n【|$)', section, re.DOTALL)
            problems = problems_match.group(1).strip() if problems_match else ''
            
            # 提取改进建议
            suggestions_match = re.search(r'【改进建议】\n(.*?)(?=\n【|$)', section, re.DOTALL)
            suggestions = suggestions_match.group(1).strip() if suggestions_match else ''
            
            return {
                'score': score,
                'test_analysis': test_analysis,
                'strengths': strengths,
                'problems': problems,
                'suggestions': suggestions
            }
            
        except Exception as e:
            logger.error(f"解析单个代码评析失败: {str(e)}")
            return {
                'score': 0,
                'test_analysis': '解析失败',
                'strengths': '',
                'problems': '',
                'suggestions': ''
            }
