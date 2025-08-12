from django.core.management.base import BaseCommand
from interviews.models import KnowledgePoint

class Command(BaseCommand):
    help = '初始化知识点标签库'

    def handle(self, *args, **options):
        self.stdout.write('开始初始化知识点标签库...')
        
        # 定义各岗位类型的知识点
        knowledge_points_data = {
            'backend': [
                '数据库设计', 'SQL优化', '索引原理', '事务管理', 'ACID特性',
                '并发编程', '线程安全', '锁机制', '性能优化', '内存管理',
                '系统架构', '微服务设计', '分布式系统', '服务治理', '负载均衡',
                'Spring框架', 'Java核心', '设计模式', 'JVM调优', '垃圾回收',
                '缓存机制', 'Redis', '消息队列', 'RPC', 'API设计',
                '网络安全', '认证授权', '数据加密', 'HTTPS', '防火墙',
                '容器化', 'Docker', 'Kubernetes', 'CI/CD', '自动化部署',
                '监控告警', '日志管理', '故障排查', '性能测试', '压力测试'
            ],
            'frontend': [
                '前端框架', 'React', 'Vue', 'Angular', 'JavaScript',
                'TypeScript', 'HTML5', 'CSS3', '组件化', '状态管理',
                '路由管理', '数据绑定', '事件处理', 'DOM操作', 'AJAX',
                '性能优化', '代码质量', '最佳实践', '用户体验', '响应式设计',
                '移动端适配', 'PWA', 'Webpack', 'Babel', 'ES6+',
                '浏览器兼容性', '跨域处理', '安全防护', 'XSS', 'CSRF',
                '单元测试', '集成测试', 'E2E测试', '代码规范', 'Git工作流'
            ],
            'pm': [
                '产品设计', '用户需求', '需求分析', '用户调研', '竞品分析',
                '项目管理', '敏捷开发', 'Scrum', '产品规划', '版本管理',
                '数据分析', '用户行为', '转化率', 'A/B测试', '数据埋点',
                '用户体验', '交互设计', '信息架构', '原型设计', '用户测试',
                '商业模式', '市场分析', '商业计划', 'ROI分析', '成本控制',
                '团队协作', '沟通技巧', '领导力', '决策能力', '时间管理'
            ],
            'qa': [
                '测试方法', '质量保证', '自动化测试', '缺陷管理', '测试用例设计',
                '功能测试', '性能测试', '安全测试', '兼容性测试', '用户体验测试',
                '单元测试', '集成测试', '系统测试', '回归测试', '冒烟测试',
                '测试工具', 'Selenium', 'JMeter', 'Postman', 'Charles',
                '测试环境', '测试数据', '测试报告', '缺陷跟踪', '质量指标',
                '持续集成', '持续部署', '测试左移', '测试右移', '质量文化'
            ],
            'algo': [
                '算法设计', '数据结构', '计算复杂度', '数学建模', '动态规划',
                '贪心算法', '回溯算法', '分治算法', '图论', '树结构',
                '排序算法', '查找算法', '字符串算法', '数组操作', '链表操作',
                '栈和队列', '哈希表', '堆', '并查集', '线段树',
                '机器学习', '深度学习', '神经网络', '自然语言处理', '计算机视觉',
                '优化算法', '遗传算法', '模拟退火', '粒子群优化', '蚁群算法'
            ],
            'data': [
                '数据分析', '机器学习', '数据挖掘', '统计学', '概率论',
                '数据清洗', '数据预处理', '特征工程', '数据可视化', '数据建模',
                'Python', 'R语言', 'SQL', 'Pandas', 'NumPy',
                'Scikit-learn', 'TensorFlow', 'PyTorch', 'Keras', 'Spark',
                '大数据处理', 'Hadoop', 'Hive', 'HBase', 'Kafka',
                '数据仓库', 'ETL', '数据湖', '实时计算', '流处理'
            ]
        }
        
        created_count = 0
        for position_type, points in knowledge_points_data.items():
            for point_name in points:
                knowledge_point, created = KnowledgePoint.objects.get_or_create(
                    name=point_name,
                    defaults={
                        'position_type': position_type,
                        'description': f'{point_name}相关知识点'
                    }
                )
                if created:
                    created_count += 1
                    self.stdout.write(f'创建知识点: {position_type} - {point_name}')
        
        self.stdout.write(self.style.SUCCESS(f'知识点标签库初始化完成！共创建 {created_count} 个知识点标签'))
