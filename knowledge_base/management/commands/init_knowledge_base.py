from django.core.management.base import BaseCommand
from knowledge_base.models import KnowledgeBaseEntry, JobPosition

class Command(BaseCommand):
    help = '初始化面试知识库数据'

    def handle(self, *args, **options):
        self.stdout.write('开始初始化知识库...')
        
        # 创建一些示例岗位
        positions = [
            {
                'name': 'Python后端开发工程师',
                'company_name': '示例公司',
                'description': '负责公司核心业务系统的后端开发，使用Python、Django、MySQL等技术栈',
                'requirements': '熟悉Python、Django、MySQL，有2年以上开发经验'
            },
            {
                'name': '前端开发工程师',
                'company_name': '示例公司',
                'description': '负责公司产品的前端开发，使用React、Vue、JavaScript等技术',
                'requirements': '熟悉React、Vue、JavaScript，有前端开发经验'
            },
            {
                'name': '全栈开发工程师',
                'company_name': '示例公司',
                'description': '负责公司产品的全栈开发，前后端都要精通',
                'requirements': '熟悉前后端技术栈，有全栈开发经验'
            }
        ]
        
        created_positions = []
        for pos_data in positions:
            position, created = JobPosition.objects.get_or_create(
                name=pos_data['name'],
                company_name=pos_data['company_name'],
                defaults=pos_data
            )
            created_positions.append(position)
            if created:
                self.stdout.write(f'创建岗位: {position.name}')
        
        # 创建知识库条目
        knowledge_entries = [
            {
                'question': '请介绍一下Django的MVT架构模式？',
                'answer': 'Django采用MVT（Model-View-Template）架构模式：\n1. Model：数据模型层，负责数据库操作\n2. View：视图层，处理业务逻辑\n3. Template：模板层，负责页面展示',
                'category': 'technical',
                'difficulty_level': 2,
                'tags': ['python', 'django', '架构'],
                'company_name': '字节跳动',
                'position_type': 'backend',
            },
            {
                'question': 'React和Vue的区别是什么？你更倾向于使用哪个？',
                'answer': 'React和Vue的主要区别：\n1. 学习曲线：Vue更简单易学\n2. 生态系统：React更丰富\n3. 灵活性：React更灵活\n4. 性能：两者都很优秀',
                'category': 'technical',
                'difficulty_level': 2,
                'tags': ['react', 'vue', '前端框架'],
                'company_name': '腾讯',
                'position_type': 'frontend',
            },
            {
                'question': '你如何设计一个新产品的需求文档？',
                'answer': '需求文档应包括：目标用户、核心功能、用户流程、界面原型、技术可行性分析、上线计划等。',
                'category': 'project',
                'difficulty_level': 3,
                'tags': ['产品设计', '需求分析'],
                'company_name': '美团',
                'position_type': 'pm',
            },
            {
                'question': '请描述测试用例的设计方法。',
                'answer': '常见测试用例设计方法有：等价类划分、边界值分析、因果图法、判定表法、场景法等。',
                'category': 'technical',
                'difficulty_level': 2,
                'tags': ['测试', '用例设计'],
                'company_name': '阿里巴巴',
                'position_type': 'qa',
            },
            {
                'question': '什么是二分查找？时间复杂度是多少？',
                'answer': '二分查找是一种在有序数组中查找目标值的算法，时间复杂度为O(log n)。',
                'category': 'technical',
                'difficulty_level': 1,
                'tags': ['算法', '查找'],
                'company_name': '百度',
                'position_type': 'algo',
            },
            {
                'question': '你在项目中遇到过最大的技术挑战是什么？如何解决的？',
                'answer': '这是一个行为面试问题，需要结合具体项目经历来回答，重点展示问题分析能力和解决方案。',
                'category': 'behavioral',
                'difficulty_level': 3,
                'tags': ['项目管理', '问题解决'],
                'company_name': '字节跳动',
                'position_type': 'backend',
            },
            {
                'question': '请解释一下RESTful API的设计原则？',
                'answer': 'RESTful API设计原则：\n1. 使用HTTP动词表示操作（GET、POST、PUT、DELETE）\n2. 使用名词表示资源\n3. 状态码表示响应结果\n4. 无状态设计',
                'category': 'technical',
                'difficulty_level': 2,
                'tags': ['api', 'rest', '设计'],
                'company_name': '腾讯',
                'position_type': 'frontend',
            },
            {
                'question': '如何优化数据库查询性能？',
                'answer': '数据库查询优化方法：\n1. 合理使用索引\n2. 避免SELECT *\n3. 使用分页查询\n4. 优化SQL语句\n5. 使用缓存',
                'category': 'technical',
                'difficulty_level': 3,
                'tags': ['数据库', '性能优化', 'sql'],
                'company_name': '美团',
                'position_type': 'pm',
            },
            {
                'question': '请描述一个你负责的项目，包括技术选型和架构设计？',
                'answer': '这是一个项目经验问题，需要详细描述项目背景、技术选型理由、架构设计思路和最终效果。',
                'category': 'project',
                'difficulty_level': 4,
                'tags': ['项目管理', '架构设计', '技术选型'],
                'company_name': '阿里巴巴',
                'position_type': 'qa',
            },
            {
                'question': '什么是动态规划？请举例说明。',
                'answer': '动态规划是一种将复杂问题分解为子问题的方法，常用于求解最优子结构问题，如背包问题、斐波那契数列等。',
                'category': 'technical',
                'difficulty_level': 3,
                'tags': ['算法', '动态规划'],
                'company_name': '百度',
                'position_type': 'algo',
            },
        ]
        
        for entry_data in knowledge_entries:
            entry, created = KnowledgeBaseEntry.objects.get_or_create(
                question=entry_data['question'],
                defaults=entry_data
            )
            if created:
                # 关联到相关岗位
                if 'python' in entry_data['tags'] or 'django' in entry_data['tags']:
                    entry.related_positions.add(created_positions[0])  # Python后端
                if 'react' in entry_data['tags'] or 'vue' in entry_data['tags']:
                    entry.related_positions.add(created_positions[1])  # 前端
                if '架构' in entry_data['tags'] or '微服务' in entry_data['tags']:
                    entry.related_positions.add(created_positions[2])  # 全栈
                
                self.stdout.write(f'创建知识库条目: {entry.question[:50]}...')
        
        self.stdout.write(self.style.SUCCESS('知识库初始化完成！')) 