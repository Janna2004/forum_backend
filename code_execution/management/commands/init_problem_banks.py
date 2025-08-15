from django.core.management.base import BaseCommand
from code_execution.models import ProblemBank, Problem
import json
import os

class Command(BaseCommand):
    help = '初始化题库和题目数据'

    def handle(self, *args, **options):
        self.stdout.write('开始初始化题库数据...')
        
        # 读取题库列表数据
        problem_bank_file = os.path.join(os.path.dirname(__file__), '..', '..', 'problem_bank_list.json')
        
        try:
            with open(problem_bank_file, 'r', encoding='utf-8') as f:
                problem_banks_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'题库文件不存在: {problem_bank_file}'))
            return
        
        # 创建题库
        created_banks = 0
        for bank_data in problem_banks_data:
            bank, created = ProblemBank.objects.get_or_create(
                id=bank_data['id'],
                defaults={
                    'title': bank_data['title'],
                    'description': bank_data['description'],
                    'category': bank_data['category'],
                    'difficulty': bank_data['difficulty'],
                    'problem_count': bank_data['problemCount'],
                    'completed_count': bank_data['completedCount'],
                    'tags': bank_data['tags'],
                    'color': bank_data['color'],
                    'is_algorithm': bank_data['isAlgorithm']
                }
            )
            if created:
                created_banks += 1
                self.stdout.write(f'创建题库: {bank.title}')
        
        self.stdout.write(f'题库初始化完成，创建了 {created_banks} 个新题库')
        
        # 创建示例题目数据
        self.create_sample_problems()
        
        self.stdout.write(self.style.SUCCESS('题库和题目数据初始化完成！'))

    def create_sample_problems(self):
        """创建示例题目数据"""
        sample_problems = [
        {
            "id": "backend-001",
            "problemSetId": "java-backend",
            "category": "后端开发",
            "title": "Spring Boot微服务设计",
            "description": "设计一个基于Spring Boot的微服务架构。",
            "scenario": "需要将单体应用拆分为多个微服务，包括用户服务、订单服务、支付服务等。",
            "difficulty": "Hard",
            "tags": ["Spring Boot", "微服务", "架构设计"],
            "question": "请设计微服务架构，包括服务拆分原则、通信方式、数据一致性等。",
            "reference_answer": "服务拆分：按业务边界划分；通信：REST API + 消息队列；数据一致性：分布式事务、最终一致性；服务发现：Eureka；配置管理：Config Server。",
            "analysis": "考察微服务架构设计能力。"
        },
        {
            "id": "backend-002",
            "problemSetId": "java-backend",
            "category": "后端开发",
            "title": "Spring Security权限管理",
            "description": "为企业系统实现基于角色的权限控制。",
            "scenario": "某内部管理系统需要区分管理员、普通员工和访客的访问权限。",
            "difficulty": "Medium",
            "tags": ["Spring Security", "权限管理", "RBAC"],
            "question": "请设计权限控制方案，包括用户认证与授权的流程。",
            "reference_answer": "认证：JWT或Session验证用户身份；授权：基于角色的权限检查；资源保护：在方法或URL层面配置访问规则。",
            "analysis": "考察后端安全机制设计能力。"
        },
        {
            "id": "backend-003",
            "problemSetId": "java-backend",
            "category": "后端开发",
            "title": "数据库索引优化",
            "description": "优化慢查询性能。",
            "scenario": "一个订单查询接口响应时间超过5秒，需要优化数据库。",
            "difficulty": "Medium",
            "tags": ["MySQL", "索引优化", "性能调优"],
            "question": "请列出三种常见的索引优化方法，并说明适用场景。",
            "reference_answer": "创建覆盖索引减少回表；联合索引优化多列查询；避免在索引列使用函数或计算。",
            "analysis": "考察数据库性能优化能力。"
        },
        {
            "id": "backend-004",
            "problemSetId": "java-backend",
            "category": "后端开发",
            "title": "高并发订单处理",
            "description": "设计高并发情况下的安全订单处理机制。",
            "scenario": "秒杀活动中同时有10万人下单，需要防止超卖。",
            "difficulty": "Hard",
            "tags": ["高并发", "分布式锁", "秒杀系统"],
            "question": "请提出防止超卖的解决方案。",
            "reference_answer": "使用Redis分布式锁控制库存扣减；引入消息队列削峰；数据库层加库存校验。",
            "analysis": "考察高并发系统设计与一致性处理。"
        },
        {
            "id": "backend-005",
            "problemSetId": "java-backend",
            "category": "后端开发",
            "title": "分布式事务处理",
            "description": "在微服务环境中保持数据一致性。",
            "scenario": "用户下单后需同时扣减库存和更新余额。",
            "difficulty": "Hard",
            "tags": ["分布式事务", "一致性", "微服务"],
            "question": "请列出三种分布式事务方案，并分析优缺点。",
            "reference_answer": "两阶段提交（强一致性但性能差）；本地消息表（最终一致性且实现简单）；TCC（灵活性高但开发复杂度大）。",
            "analysis": "考察分布式系统一致性设计能力。"
        },
        {
            "id": "backend-006",
            "problemSetId": "java-backend",
            "category": "后端开发",
            "title": "缓存设计策略",
            "description": "优化接口响应速度。",
            "scenario": "首页热门商品列表访问频繁，需要加速加载。",
            "difficulty": "Medium",
            "tags": ["缓存", "Redis", "性能优化"],
            "question": "请给出缓存策略设计，并说明缓存击穿、雪崩、穿透的应对方案。",
            "reference_answer": "缓存击穿：热点key加互斥锁；缓存雪崩：过期时间随机化；缓存穿透：使用布隆过滤器。",
            "analysis": "考察缓存系统设计能力。"
        },
        {
            "id": "backend-007",
            "problemSetId": "java-backend",
            "category": "后端开发",
            "title": "API网关设计",
            "description": "统一管理微服务的对外接口。",
            "scenario": "多个微服务需要统一鉴权、限流、路由转发。",
            "difficulty": "Medium",
            "tags": ["API网关", "微服务", "Zuul", "Spring Cloud Gateway"],
            "question": "请设计API网关的核心功能模块。",
            "reference_answer": "鉴权模块、限流模块、路由转发模块、日志与监控模块。",
            "analysis": "考察后端网关设计与微服务整合能力。"
        },
        {
            "id": "backend-008",
            "problemSetId": "java-backend",
            "category": "后端开发",
            "title": "日志追踪系统设计",
            "description": "实现分布式系统的调用链追踪。",
            "scenario": "微服务系统中调用链复杂，难以排查问题。",
            "difficulty": "Medium",
            "tags": ["日志追踪", "链路追踪", "监控"],
            "question": "请列出实现分布式调用链追踪的技术方案。",
            "reference_answer": "使用Zipkin或SkyWalking实现Trace ID传递，采集调用链日志并存储分析。",
            "analysis": "考察后端可观测性与问题排查能力。"
        },
        {
            "id": "backend-009",
            "problemSetId": "java-backend",
            "category": "后端开发",
            "title": "消息队列的应用场景",
            "description": "利用MQ解耦系统与削峰填谷。",
            "scenario": "电商订单系统需要异步发送短信与邮件通知。",
            "difficulty": "Easy",
            "tags": ["消息队列", "解耦", "削峰"],
            "question": "请描述MQ的三种典型应用场景。",
            "reference_answer": "异步处理、系统解耦、流量削峰。",
            "analysis": "考察后端架构设计与消息中间件应用能力。"
        },
        {
            "id": "backend-010",
            "problemSetId": "java-backend",
            "category": "后端开发",
            "title": "RESTful API设计规范",
            "description": "设计符合REST规范的接口。",
            "scenario": "开发一套用户管理接口，需保证API设计规范化。",
            "difficulty": "Easy",
            "tags": ["RESTful", "API设计"],
            "question": "请列出RESTful API的五个关键设计要点。",
            "reference_answer": "使用HTTP方法表达操作；资源路径名词化；状态码语义化；统一响应格式；支持分页与过滤。",
            "analysis": "考察后端接口设计规范化能力。"
        },
        {
            "id": "django-001",
            "problemSetId": "python-django",
            "category": "后端开发",
            "title": "Django项目结构规划",
            "description": "合理规划Django项目目录结构。",
            "scenario": "团队准备开发一个大型Django电商平台。",
            "difficulty": "Easy",
            "tags": ["Django", "项目结构", "后端开发"],
            "question": "请列出一个大型Django项目的推荐目录结构。",
            "reference_answer": "apps（功能模块）、templates（模板）、static（静态文件）、settings（配置）、urls（路由）、manage.py。",
            "analysis": "考察Django项目组织与可维护性。"
        },
        {
            "id": "django-002",
            "problemSetId": "python-django",
            "category": "后端开发",
            "title": "Django ORM优化",
            "description": "优化查询性能。",
            "scenario": "一个接口需要关联查询多个表，响应慢。",
            "difficulty": "Medium",
            "tags": ["Django", "ORM", "性能优化"],
            "question": "请列出三种Django ORM优化方法。",
            "reference_answer": "使用select_related减少外键查询；prefetch_related优化多对多；分页加载减少数据量。",
            "analysis": "考察Django ORM性能调优能力。"
        },
        {
            "id": "django-003",
            "problemSetId": "python-django",
            "category": "后端开发",
            "title": "Django中间件应用",
            "description": "实现请求日志记录功能。",
            "scenario": "需要记录所有HTTP请求的时间、路径与响应状态码。",
            "difficulty": "Easy",
            "tags": ["Django", "中间件", "日志"],
            "question": "请描述Django中间件实现请求日志的步骤。",
            "reference_answer": "编写中间件类实现process_request与process_response方法；记录请求与响应信息；注册到settings.MIDDLEWARE。",
            "analysis": "考察Django中间件开发能力。"
        },
        {
            "id": "django-004",
            "problemSetId": "python-django",
            "category": "后端开发",
            "title": "Django权限控制",
            "description": "为不同用户角色分配权限。",
            "scenario": "系统中有管理员、教师、学生三种角色。",
            "difficulty": "Medium",
            "tags": ["Django", "权限管理", "RBAC"],
            "question": "请列出Django实现权限控制的三种方式。",
            "reference_answer": "基于用户组权限；自定义装饰器检查权限；基于权限Mixin的类视图控制。",
            "analysis": "考察Django权限与安全机制设计能力。"
        },
        {
            "id": "django-005",
            "problemSetId": "python-django",
            "category": "后端开发",
            "title": "Django REST Framework设计API",
            "description": "设计RESTful API。",
            "scenario": "需要为移动端提供商品管理接口。",
            "difficulty": "Medium",
            "tags": ["DRF", "API设计"],
            "question": "请列出DRF实现REST API的三个关键组件。",
            "reference_answer": "Serializer序列化数据；ViewSet处理请求；Router自动生成路由。",
            "analysis": "考察DRF框架应用能力。"
        },
        {
            "id": "django-006",
            "problemSetId": "python-django",
            "category": "后端开发",
            "title": "Django缓存策略",
            "description": "优化接口响应速度。",
            "scenario": "首页接口访问量大，需要加速响应。",
            "difficulty": "Easy",
            "tags": ["Django", "缓存", "性能优化"],
            "question": "请列出Django实现缓存的三种方式。",
            "reference_answer": "页面缓存；视图缓存；模板片段缓存。",
            "analysis": "考察Django缓存机制的应用能力。"
        },
        {
            "id": "django-007",
            "problemSetId": "python-django",
            "category": "后端开发",
            "title": "Django文件上传处理",
            "description": "实现用户头像上传功能。",
            "scenario": "用户可上传头像图片到个人资料。",
            "difficulty": "Easy",
            "tags": ["Django", "文件上传"],
            "question": "请描述Django实现文件上传的步骤。",
            "reference_answer": "在Model中定义ImageField；在表单或API中接收文件；在settings中配置MEDIA_URL与MEDIA_ROOT。",
            "analysis": "考察Django文件处理能力。"
        },
        {
            "id": "django-008",
            "problemSetId": "python-django",
            "category": "后端开发",
            "title": "Django信号机制",
            "description": "在用户注册后发送欢迎邮件。",
            "scenario": "用户注册成功后需自动发送邮件。",
            "difficulty": "Easy",
            "tags": ["Django", "信号", "异步任务"],
            "question": "请描述Django使用信号机制的实现步骤。",
            "reference_answer": "定义receiver函数；使用@receiver装饰器监听post_save信号；在函数中发送邮件。",
            "analysis": "考察Django信号机制与业务事件处理能力。"
        },
        {
            "id": "django-009",
            "problemSetId": "python-django",
            "category": "后端开发",
            "title": "Django国际化与本地化",
            "description": "支持多语言切换功能。",
            "scenario": "平台需要支持中英双语切换。",
            "difficulty": "Medium",
            "tags": ["Django", "国际化", "本地化"],
            "question": "请列出Django实现国际化的三个步骤。",
            "reference_answer": "在模板与代码中标记可翻译字符串；使用makemessages生成翻译文件；使用compilemessages编译翻译文件。",
            "analysis": "考察Django国际化功能应用能力。"
        },
        {
            "id": "django-010",
            "problemSetId": "python-django",
            "category": "后端开发",
            "title": "Django Celery任务队列",
            "description": "实现异步任务处理。",
            "scenario": "订单支付成功后异步发送短信。",
            "difficulty": "Medium",
            "tags": ["Django", "Celery", "异步任务"],
            "question": "请列出Django集成Celery的三个关键步骤。",
            "reference_answer": "安装并配置Celery；定义任务函数；启动Celery worker处理任务。",
            "analysis": "考察Django与Celery的结合使用能力。"
        }
        ]

        
        created_problems = 0
        for problem_data in sample_problems:
            try:
                problem_bank = ProblemBank.objects.get(id=problem_data['problemSetId'])
                
                problem, created = Problem.objects.get_or_create(
                    id=problem_data['id'],
                    defaults={
                        'problem_set': problem_bank,
                        'category': problem_data['category'],
                        'title': problem_data['title'],
                        'description': problem_data['description'],
                        'scenario': problem_data['scenario'],
                        'difficulty': problem_data['difficulty'],
                        'tags': problem_data['tags'],
                        'question': problem_data['question'],
                        'reference_answer': problem_data['reference_answer'],
                        'analysis': problem_data['analysis']
                    }
                )
                if created:
                    created_problems += 1
                    self.stdout.write(f'创建题目: {problem.title}')
            except ProblemBank.DoesNotExist:
                self.stdout.write(f'题库不存在: {problem_data["problemSetId"]}')
        
        self.stdout.write(f'题目初始化完成，创建了 {created_problems} 个新题目')
