from django.db import models

# Create your models here.

class Position(models.Model):
    TYPE_CHOICES = [
        ('backend', '后端开发'),
        ('frontend', '前端开发'),
        ('pm', '产品经理'),
        ('qa', '测试'),
        ('algo', '算法'),
        ('other', '其他标签'),
    ]
    
    id = models.AutoField(primary_key=True)  # 显式定义id字段
    
    # 原有字段
    position_name = models.CharField(max_length=255, verbose_name='职位名称', db_column='JobName')
    company_name = models.CharField(max_length=255, verbose_name='公司名称', db_column='Company')
    position_url = models.TextField(verbose_name='职位链接', db_column='Url')
    
    # 新增字段，匹配爬虫数据结构
    salary = models.CharField(max_length=255, blank=True, null=True, verbose_name='薪资', db_column='Salary')
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name='地址', db_column='Address')
    view_rate = models.CharField(max_length=255, blank=True, null=True, verbose_name='查看率', db_column='ViewRate')
    ave_speed = models.CharField(max_length=255, blank=True, null=True, verbose_name='平均速度', db_column='AveSpeed')
    add_info = models.TextField(blank=True, null=True, verbose_name='附加信息', db_column='AddInfo')
    work_style = models.CharField(max_length=255, blank=True, null=True, verbose_name='工作方式', db_column='WorkStyle')
    work_time = models.CharField(max_length=255, blank=True, null=True, verbose_name='工作时间', db_column='WorkTime')
    upgrade_chance = models.CharField(max_length=255, blank=True, null=True, verbose_name='升级机会', db_column='UpgradeChance')
    introduction = models.TextField(blank=True, null=True, verbose_name='公司介绍', db_column='Introduction')
    job_request = models.TextField(blank=True, null=True, verbose_name='岗位要求', db_column='JobRequest')
    
    # 类型字段，用于关键字标签检测
    position_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='other', verbose_name='岗位类型')
    
    # 时间戳字段
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'nowcoder_data'  # 使用已有的表名
        managed = True  # 修改为True，让Django管理这个表
        verbose_name = '职位信息'
        verbose_name_plural = verbose_name
        ordering = ['-id']  # 默认按id倒序排序

    def __str__(self):
        return f"{self.company_name} - {self.position_name}"

    def save(self, *args, **kwargs):
        """保存时自动检测岗位类型"""
        if not self.position_type or self.position_type == 'other':
            self.position_type = self.detect_position_type()
        super().save(*args, **kwargs)
    
    def detect_position_type(self):
        """根据岗位名称和要求检测岗位类型"""
        # 检测文本，包括岗位名称、岗位要求、附加信息
        text_to_check = f"{self.position_name or ''} {self.job_request or ''} {self.add_info or ''}".lower()
        
        # 关键字映射
        keywords_map = {
            'backend': ['后端', 'backend', 'java', 'python', 'go', 'nodejs', 'node.js', 'php', 'c++', '服务端', 'api', 'spring', 'django', 'flask'],
            'frontend': ['前端', 'frontend', 'javascript', 'js', 'react', 'vue', 'angular', 'html', 'css', 'typescript', 'ts', 'ui', 'ux'],
            'pm': ['产品', 'product', 'pm', '产品经理', 'product manager', '需求', '运营'],
            'qa': ['测试', 'test', 'qa', 'quality', '自动化测试', '接口测试', '性能测试'],
            'algo': ['算法', 'algorithm', '机器学习', 'ml', '深度学习', 'ai', '人工智能', '数据挖掘', '大数据']
        }
        
        # 遍历关键字映射，找到匹配的类型
        for position_type, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword in text_to_check:
                    return position_type
        
        return 'other'
