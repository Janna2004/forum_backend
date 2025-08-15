from django.core.management.base import BaseCommand
from code_execution.models import ProblemBank, Problem

class Command(BaseCommand):
    help = '创建测试题目数据'

    def handle(self, *args, **options):
        # 创建算法题库
        algorithm_bank, created = ProblemBank.objects.get_or_create(
            id='basic-algorithm',
            defaults={
                'title': '算法题测试题库',
                'description': '包含各种算法题的测试题库',
                'category': '算法设计',
                'difficulty': 'Medium',
                'is_algorithm': True,
                'tags': ['算法', '数据结构', '动态规划'],
                'color': 'bg-blue-300'
            }
        )
        
        if created:
            self.stdout.write(f'创建算法题库: {algorithm_bank.title}')
        
        # 创建算法题
        algorithm_problem, created = Problem.objects.get_or_create(
            id='algo-001',
            defaults={
                'problem_set': algorithm_bank,
                'category': '算法设计',
                'title': '两数之和',
                'description': '给定一个整数数组 nums 和一个整数目标值 target，请你在该数组中找出和为目标值 target 的那两个整数，并返回它们的数组下标。',
                'scenario': '在数组中查找两个数的和等于目标值',
                'difficulty': 'Easy',
                'tags': ['数组', '哈希表'],
                'is_algorithm': True,
                'question': '请实现一个函数，找出数组中两个数的和等于目标值的下标。',
                'reference_answer': '使用哈希表存储已遍历的数字，时间复杂度O(n)',
                'analysis': '这是一道经典的哈希表应用题目',
                'algorithm_constraints': {
                    'time_complexity': 'O(n)',
                    'space_complexity': 'O(n)',
                    'array_length': '2 <= nums.length <= 10^4',
                    'target_range': '-10^9 <= target <= 10^9'
                },
                'algorithm_test_cases': {
                    'public': [
                        {
                            'id': 1,
                            'name': '示例 1',
                            'input': '[2,7,11,15]\n9',
                            'expectedOutput': '[0,1]',
                            'status': 'pending',
                            'actualOutput': '',
                            'error': ''
                        },
                        {
                            'id': 2,
                            'name': '示例 2',
                            'input': '[3,2,4]\n6',
                            'expectedOutput': '[1,2]',
                            'status': 'pending',
                            'actualOutput': '',
                            'error': ''
                        },
                        {
                            'id': 3,
                            'name': '示例 3',
                            'input': '[3,3]\n6',
                            'expectedOutput': '[0,1]',
                            'status': 'pending',
                            'actualOutput': '',
                            'error': ''
                        }
                    ],
                    'hidden': [
                        {
                            'id': 4,
                            'name': '隐藏测试用例 1',
                            'status': 'pending'
                        },
                        {
                            'id': 5,
                            'name': '隐藏测试用例 2',
                            'status': 'pending'
                        },
                        {
                            'id': 6,
                            'name': '隐藏测试用例 3',
                            'status': 'pending'
                        }
                    ]
                },
                'algorithm_solution': '''
def twoSum(nums, target):
    """
    使用哈希表解决两数之和问题
    时间复杂度: O(n)
    空间复杂度: O(n)
    """
    hash_map = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in hash_map:
            return [hash_map[complement], i]
        hash_map[num] = i
    return []
                ''',
                'algorithm_code_template': '''
def twoSum(nums, target):
    # 在这里实现你的解决方案
    pass
                '''
            }
        )
        
        if created:
            self.stdout.write(f'创建算法题: {algorithm_problem.title}')
        
        # 创建非算法题库
        non_algorithm_bank, created = ProblemBank.objects.get_or_create(
            id='non-algorithm-test',
            defaults={
                'title': '非算法题测试题库',
                'description': '包含各种非算法题的测试题库',
                'category': '后端开发',
                'difficulty': 'Medium',
                'is_algorithm': False,
                'tags': ['Java', 'Spring', '数据库'],
                'color': 'bg-green-300'
            }
        )
        
        if created:
            self.stdout.write(f'创建非算法题库: {non_algorithm_bank.title}')
        
        # 创建非算法题
        non_algorithm_problem, created = Problem.objects.get_or_create(
            id='non-algo-001',
            defaults={
                'problem_set': non_algorithm_bank,
                'category': '后端开发',
                'title': 'Spring Boot自动配置原理',
                'description': '请详细解释Spring Boot的自动配置机制是如何工作的。',
                'scenario': '面试中经常被问到的Spring Boot核心概念',
                'difficulty': 'Medium',
                'tags': ['Spring Boot', '自动配置', 'Java'],
                'is_algorithm': False,
                'question': '请详细解释Spring Boot的自动配置机制，包括@EnableAutoConfiguration注解的作用、自动配置的条件注解、以及如何自定义自动配置。',
                'reference_answer': '''
Spring Boot自动配置机制的核心原理：

1. @EnableAutoConfiguration注解：
   - 通过@Import导入AutoConfigurationImportSelector
   - 扫描classpath下的META-INF/spring.factories文件
   - 加载所有自动配置类

2. 条件注解：
   - @ConditionalOnClass：类路径下存在指定类时生效
   - @ConditionalOnMissingClass：类路径下不存在指定类时生效
   - @ConditionalOnBean：容器中存在指定Bean时生效
   - @ConditionalOnMissingBean：容器中不存在指定Bean时生效
   - @ConditionalOnProperty：指定属性有特定值时生效

3. 自动配置类：
   - 使用@Configuration注解标记为配置类
   - 使用@Conditional注解控制条件
   - 使用@Bean注解创建Bean

4. 自定义自动配置：
   - 创建配置类
   - 在META-INF/spring.factories中注册
   - 使用条件注解控制生效条件
                ''',
                'analysis': '这是Spring Boot的核心特性，理解自动配置机制对于深入理解Spring Boot非常重要。',
                'non_algorithm_knowledge_points': [
                    'Spring Boot自动配置',
                    '@EnableAutoConfiguration注解',
                    '条件注解',
                    'META-INF/spring.factories',
                    '自定义自动配置'
                ],
                'non_algorithm_scoring_criteria': {
                    'excellent': {
                        'score_range': [90, 100],
                        'criteria': '能够详细解释自动配置的完整流程，包括条件注解的使用和自定义配置方法'
                    },
                    'good': {
                        'score_range': [70, 89],
                        'criteria': '能够解释自动配置的基本原理和主要条件注解'
                    },
                    'fair': {
                        'score_range': [50, 69],
                        'criteria': '能够简单描述自动配置的概念和作用'
                    },
                    'poor': {
                        'score_range': [0, 49],
                        'criteria': '对自动配置概念模糊或完全不了解'
                    }
                }
            }
        )
        
        if created:
            self.stdout.write(f'创建非算法题: {non_algorithm_problem.title}')
        
        self.stdout.write(
            self.style.SUCCESS('成功创建测试数据！')
        )
