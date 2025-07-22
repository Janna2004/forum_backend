# Generated manually to handle position field change
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('interviews', '0007_interview_question_queue'),
    ]

    operations = [
        # 添加新的nowcoder_position_id字段
        migrations.AddField(
            model_name='interview',
            name='nowcoder_position_id',
            field=models.IntegerField(blank=True, null=True, verbose_name='牛客网岗位ID'),
        ),
        
        # 更新position_type字段的选择项
        migrations.AlterField(
            model_name='interview',
            name='position_type',
            field=models.CharField(
                choices=[
                    ('backend', '后端开发'),
                    ('frontend', '前端开发'),
                    ('pm', '产品经理'),
                    ('qa', '测试'),
                    ('algo', '算法'),
                    ('data', '数据'),
                    ('other', '其他'),
                ],
                default='backend',
                max_length=20,
                verbose_name='岗位类型'
            ),
        ),
    ] 