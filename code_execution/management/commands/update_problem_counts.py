from django.core.management.base import BaseCommand
from code_execution.models import ProblemBank

class Command(BaseCommand):
    help = '更新题库的题目数量统计'

    def handle(self, *args, **options):
        self.stdout.write('开始更新题库题目数量统计...')
        
        updated_count = 0
        for bank in ProblemBank.objects.all():
            real_count = bank.real_problem_count
            if bank.problem_count != real_count:
                bank.problem_count = real_count
                bank.save()
                updated_count += 1
                self.stdout.write(f'更新题库 "{bank.title}": {real_count} 题')
        
        self.stdout.write(self.style.SUCCESS(f'题库题目数量统计更新完成，共更新了 {updated_count} 个题库'))
