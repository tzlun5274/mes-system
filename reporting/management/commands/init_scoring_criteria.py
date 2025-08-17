"""
初始化評分標準的管理命令
"""

from django.core.management.base import BaseCommand
from reporting.models import ScoringCriteria


class Command(BaseCommand):
    help = '初始化評分標準資料'

    def handle(self, *args, **options):
        self.stdout.write('開始初始化評分標準...')
        
        # 清除現有資料
        ScoringCriteria.objects.all().delete()
        
        # 建立預設評分標準
        criteria_data = [
            {
                'name': '完工率',
                'criteria_type': 'production',
                'description': '工單完工數量與計劃數量的比率',
                'max_score': 100.00,
                'weight': 40.00,
                'formula_type': 'percentage',
                'formula_expression': 'completed_quantity / planned_quantity * 100',
                'excellent_threshold': 95.00,
                'good_threshold': 85.00,
                'pass_threshold': 70.00,
            },
            {
                'name': '效率率',
                'criteria_type': 'production',
                'description': '實際工作時數與標準工作時數的比率',
                'max_score': 100.00,
                'weight': 40.00,
                'formula_type': 'percentage',
                'formula_expression': 'standard_hours / actual_hours * 100',
                'excellent_threshold': 95.00,
                'good_threshold': 85.00,
                'pass_threshold': 70.00,
            },
            {
                'name': '每小時產出',
                'criteria_type': 'production',
                'description': '每小時生產的產品數量',
                'max_score': 100.00,
                'weight': 20.00,
                'formula_type': 'custom',
                'formula_expression': 'min(hourly_output * 10, 100)',
                'excellent_threshold': 90.00,
                'good_threshold': 80.00,
                'pass_threshold': 70.00,
            },
            {
                'name': '不良率',
                'criteria_type': 'quality',
                'description': '不良品數量與總生產數量的比率',
                'max_score': 100.00,
                'weight': 100.00,
                'formula_type': 'percentage',
                'formula_expression': '(1 - defect_quantity / total_quantity) * 100',
                'excellent_threshold': 95.00,
                'good_threshold': 90.00,
                'pass_threshold': 85.00,
            },
            {
                'name': '準時完工率',
                'criteria_type': 'delivery',
                'description': '準時完工的工單數量與總工單數量的比率',
                'max_score': 100.00,
                'weight': 100.00,
                'formula_type': 'percentage',
                'formula_expression': 'on_time_orders / total_orders * 100',
                'excellent_threshold': 95.00,
                'good_threshold': 90.00,
                'pass_threshold': 80.00,
            },
            {
                'name': '設備利用率',
                'criteria_type': 'equipment',
                'description': '設備實際使用時數與可用時數的比率',
                'max_score': 100.00,
                'weight': 100.00,
                'formula_type': 'percentage',
                'formula_expression': 'actual_hours / available_hours * 100',
                'excellent_threshold': 90.00,
                'good_threshold': 80.00,
                'pass_threshold': 70.00,
            },
            {
                'name': '加班時數比例',
                'criteria_type': 'cost',
                'description': '加班時數與總工作時數的比率',
                'max_score': 100.00,
                'weight': 100.00,
                'formula_type': 'percentage',
                'formula_expression': '(1 - overtime_hours / total_hours) * 100',
                'excellent_threshold': 90.00,
                'good_threshold': 80.00,
                'pass_threshold': 70.00,
            },
            {
                'name': '安全事件數',
                'criteria_type': 'safety',
                'description': '安全事件發生次數',
                'max_score': 100.00,
                'weight': 100.00,
                'formula_type': 'count',
                'formula_expression': 'max(100 - safety_incidents * 10, 0)',
                'excellent_threshold': 95.00,
                'good_threshold': 85.00,
                'pass_threshold': 70.00,
            },
            {
                'name': '人員效率',
                'criteria_type': 'personnel',
                'description': '人員實際工作時數與標準工作時數的比率',
                'max_score': 100.00,
                'weight': 100.00,
                'formula_type': 'percentage',
                'formula_expression': 'actual_hours / standard_hours * 100',
                'excellent_threshold': 95.00,
                'good_threshold': 85.00,
                'pass_threshold': 70.00,
            },
        ]
        
        created_count = 0
        for data in criteria_data:
            criteria, created = ScoringCriteria.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                created_count += 1
                self.stdout.write(f'建立評分標準: {data["name"]}')
        
        self.stdout.write(
            self.style.SUCCESS(f'成功初始化 {created_count} 個評分標準')
        ) 