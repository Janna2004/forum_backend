from django.db import models

# Create your models here.

class Position(models.Model):
    id = models.AutoField(primary_key=True)  # 显式定义id字段
    position_name = models.CharField(max_length=255, verbose_name='职位名称')
    company_name = models.CharField(max_length=255, verbose_name='公司名称')
    position_url = models.TextField(verbose_name='职位链接')

    class Meta:
        db_table = 'nowcoder_data'  # 使用已有的表名
        managed = False  # 告诉Django这个表已经存在，不需要管理
        verbose_name = '职位信息'
        verbose_name_plural = verbose_name
        ordering = ['-id']  # 默认按id倒序排序

    def __str__(self):
        return f"{self.company_name} - {self.position_name}"
