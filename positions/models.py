from django.db import models

# Create your models here.

# 原有的Position模型 - 保持简单不变
class Position(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    position_name = models.CharField(max_length=255, verbose_name='职位名称')
    company_name = models.CharField(max_length=255, verbose_name='公司名称')
    position_url = models.TextField(verbose_name='职位链接')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'nowcoder_data'  # 使用默认的表名
        managed = True
        verbose_name = '职位信息（已废弃）'
        verbose_name_plural = verbose_name
        ordering = ['-id']

    def __str__(self):
        return f"{self.company_name} - {self.position_name}"


# 新的NowCoderPosition模型 - 对接nowcoder_data表
class NowCoderPosition(models.Model):
    TYPE_CHOICES = [
        ('backend', '后端开发'),
        ('frontend', '前端开发'),
        ('pm', '产品经理'), 
        ('qa', '测试'),
        ('algo', '算法'),
        ('data', '数据'),
        ('other', '其他'),
    ]
    
    id = models.AutoField(primary_key=True)
    
    # 对应nowcoder_data表的字段
    job_name = models.CharField(max_length=500, verbose_name='职位名称')
    company = models.CharField(max_length=255, verbose_name='公司名称')
    url = models.TextField(verbose_name='职位链接')
    salary = models.CharField(max_length=100, blank=True, null=True, verbose_name='薪资')
    address = models.TextField(blank=True, null=True, verbose_name='地址')
    view_rate = models.CharField(max_length=100, blank=True, null=True, verbose_name='简历处理率')
    ave_speed = models.CharField(max_length=100, blank=True, null=True, verbose_name='平均处理时间')
    add_info = models.CharField(max_length=100, blank=True, null=True, verbose_name='附加信息')
    work_style = models.CharField(max_length=100, blank=True, null=True, verbose_name='工作类型')
    work_time = models.CharField(max_length=200, blank=True, null=True, verbose_name='工作时间')
    upgrade_chance = models.CharField(max_length=50, blank=True, null=True, verbose_name='晋升机会')
    introduction = models.TextField(blank=True, null=True, verbose_name='职位介绍')
    job_request = models.TextField(blank=True, null=True, verbose_name='职位要求')

    class Meta:
        db_table = 'nowcoder_data'  # 对接nowcoder_data表
        managed = False  # 不让Django管理这个表的结构
        verbose_name = '牛客网职位信息'
        verbose_name_plural = verbose_name
        ordering = ['-id']

    def __str__(self):
        return f"{self.company} - {self.job_name}"
    
    @property
    def position_type(self):
        """根据岗位名称和要求检测岗位类型"""
        text_to_check = f"{self.job_name or ''} {self.job_request or ''} {self.add_info or ''}".lower()
        
        # 关键字映射
        keywords_map = {
            'backend': ['后端', 'backend', 'java', 'python', 'go', 'nodejs', 'node.js', 'php', 'c++', '服务端', 'api', 'spring', 'django', 'flask'],
            'frontend': ['前端', 'frontend', 'javascript', 'js', 'react', 'vue', 'angular', 'html', 'css', 'typescript', 'ts', 'ui', 'ux'],
            'pm': ['产品', 'product', 'pm', '产品经理', 'product manager', '需求', '运营'],
            'qa': ['测试', 'test', 'qa', 'quality', '自动化测试', '接口测试', '性能测试'],
            'algo': ['算法', 'algorithm', '机器学习', 'ml', '深度学习', 'ai', '人工智能'],
            'data': ['数据', 'data', '大数据', 'bigdata', '数据分析', '数据挖掘', '数据科学', '数据工程']
        }
        
        # 遍历关键字映射，找到匹配的类型
        for position_type, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword in text_to_check:
                    return position_type
        
        return 'other'
    
    @property
    def position_name(self):
        """兼容性属性，返回job_name"""
        return self.job_name
        
    @property
    def company_name(self):
        """兼容性属性，返回company"""
        return self.company
        
    @property
    def position_url(self):
        """兼容性属性，返回url"""
        return self.url
