# Generated by Django 5.2.4 on 2025-07-12 09:21

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="user",
            options={"verbose_name": "用户", "verbose_name_plural": "用户"},
        ),
        migrations.AddField(
            model_name="user",
            name="avatar",
            field=models.URLField(blank=True, null=True, verbose_name="头像"),
        ),
        migrations.AddField(
            model_name="user",
            name="phone",
            field=models.CharField(
                blank=True, max_length=20, null=True, verbose_name="手机号"
            ),
        ),
        migrations.CreateModel(
            name="Resume",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=50, verbose_name="姓名")),
                ("age", models.IntegerField(verbose_name="年龄")),
                ("graduation_date", models.DateField(verbose_name="毕业时间")),
                (
                    "education_level",
                    models.CharField(max_length=50, verbose_name="学历"),
                ),
                (
                    "expected_position",
                    models.CharField(max_length=100, verbose_name="期望职位"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resume",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "简历",
                "verbose_name_plural": "简历",
            },
        ),
        migrations.CreateModel(
            name="ProjectExperience",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("start_date", models.DateField(verbose_name="开始时间")),
                (
                    "end_date",
                    models.DateField(blank=True, null=True, verbose_name="结束时间"),
                ),
                (
                    "project_name",
                    models.CharField(max_length=100, verbose_name="项目名称"),
                ),
                (
                    "project_role",
                    models.CharField(max_length=100, verbose_name="项目角色"),
                ),
                (
                    "project_link",
                    models.URLField(blank=True, null=True, verbose_name="项目链接"),
                ),
                ("project_content", models.TextField(verbose_name="项目内容")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "resume",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="project_experiences",
                        to="users.resume",
                        verbose_name="简历",
                    ),
                ),
            ],
            options={
                "verbose_name": "项目经历",
                "verbose_name_plural": "项目经历",
                "ordering": ["-start_date"],
            },
        ),
        migrations.CreateModel(
            name="EducationExperience",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("start_date", models.DateField(verbose_name="开始时间")),
                (
                    "end_date",
                    models.DateField(blank=True, null=True, verbose_name="结束时间"),
                ),
                (
                    "school_name",
                    models.CharField(max_length=100, verbose_name="学校名称"),
                ),
                (
                    "education_level",
                    models.CharField(max_length=50, verbose_name="学历"),
                ),
                (
                    "major",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="专业"
                    ),
                ),
                (
                    "school_experience",
                    models.TextField(blank=True, null=True, verbose_name="在校经历"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "resume",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="education_experiences",
                        to="users.resume",
                        verbose_name="简历",
                    ),
                ),
            ],
            options={
                "verbose_name": "教育经历",
                "verbose_name_plural": "教育经历",
                "ordering": ["-start_date"],
            },
        ),
        migrations.CreateModel(
            name="CustomSection",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=100, verbose_name="标题")),
                ("content", models.TextField(verbose_name="内容")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "resume",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="custom_sections",
                        to="users.resume",
                        verbose_name="简历",
                    ),
                ),
            ],
            options={
                "verbose_name": "自定义部分",
                "verbose_name_plural": "自定义部分",
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="WorkExperience",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("start_date", models.DateField(verbose_name="开始时间")),
                (
                    "end_date",
                    models.DateField(blank=True, null=True, verbose_name="结束时间"),
                ),
                (
                    "company_name",
                    models.CharField(max_length=100, verbose_name="公司名称"),
                ),
                (
                    "department",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="所属部门"
                    ),
                ),
                (
                    "position",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="职位名称"
                    ),
                ),
                ("work_content", models.TextField(verbose_name="工作内容")),
                (
                    "is_internship",
                    models.BooleanField(default=False, verbose_name="是否是实习"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "resume",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="work_experiences",
                        to="users.resume",
                        verbose_name="简历",
                    ),
                ),
            ],
            options={
                "verbose_name": "工作经历",
                "verbose_name_plural": "工作经历",
                "ordering": ["-start_date"],
            },
        ),
    ]
