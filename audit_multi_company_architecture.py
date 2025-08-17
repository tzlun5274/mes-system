#!/usr/bin/env python3
"""
多公司架構審計腳本
檢查系統是否真正按照多公司唯一識別性設計
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from workorder.models import WorkOrder, WorkOrderProductionDetail
from workorder.fill_work.models import FillWork
from workorder.workorder_dispatch.models import WorkOrderDispatch
from erp_integration.models import CompanyConfig
from django.db.models import Count, Q

def audit_multi_company_architecture():
    """審計多公司架構設計"""
    print("=== 多公司架構審計報告 ===")
    print("檢查系統是否真正按照多公司唯一識別性設計")
    print("=" * 60)
    
    # 1. 檢查公司配置
    print("\n1. 公司配置檢查:")
    companies = CompanyConfig.objects.all()
    print(f"   配置的公司數量: {companies.count()}")
    
    for company in companies:
        print(f"   - 公司代號: {company.company_code}, 公司名稱: {company.company_name}")
    
    # 2. 檢查工單的唯一識別性
    print("\n2. 工單唯一識別性檢查:")
    
    # 檢查重複的工單號碼
    duplicate_orders = WorkOrder.objects.values('order_number').annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    if duplicate_orders.exists():
        print(f"   ⚠ 發現 {duplicate_orders.count()} 個重複的工單號碼:")
        
        for dup in duplicate_orders:
            order_number = dup['order_number']
            workorders = WorkOrder.objects.filter(order_number=order_number)
            
            print(f"\n   工單號碼: {order_number}")
            for wo in workorders:
                print(f"     - ID: {wo.id}, 公司: {wo.company_code}, 產品: {wo.product_code}, 狀態: {wo.status}")
                
                # 檢查是否有唯一識別衝突
                if workorders.count() > 1:
                    print(f"       ⚠ 違反唯一識別原則：相同工單號碼存在多筆記錄")
    else:
        print("   ✓ 工單號碼沒有重複")
    
    # 3. 檢查多公司唯一識別組合
    print("\n3. 多公司唯一識別組合檢查:")
    
    # 檢查公司代號+工單號碼+產品編號的組合
    duplicate_combinations = WorkOrder.objects.values(
        'company_code', 'order_number', 'product_code'
    ).annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    if duplicate_combinations.exists():
        print(f"   ⚠ 發現 {duplicate_combinations.count()} 個重複的唯一識別組合:")
        
        for dup in duplicate_combinations:
            workorders = WorkOrder.objects.filter(
                company_code=dup['company_code'],
                order_number=dup['order_number'],
                product_code=dup['product_code']
            )
            
            print(f"\n   組合: 公司={dup['company_code']}, 工單={dup['order_number']}, 產品={dup['product_code']}")
            for wo in workorders:
                print(f"     - ID: {wo.id}, 狀態: {wo.status}")
    else:
        print("   ✓ 多公司唯一識別組合沒有重複")
    
    # 4. 檢查填報記錄的公司隔離
    print("\n4. 填報記錄公司隔離檢查:")
    
    # 檢查填報記錄是否正確按公司分離
    fillwork_companies = FillWork.objects.values('company_name').distinct()
    print(f"   填報記錄涉及的公司: {[fw['company_name'] for fw in fillwork_companies]}")
    
    # 檢查是否有跨公司的資料污染
    for company in companies:
        company_fillwork = FillWork.objects.filter(company_name=company.company_name)
        other_company_fillwork = FillWork.objects.exclude(company_name=company.company_name)
        
        # 檢查是否有相同工單號碼但不同公司的記錄
        company_orders = set(company_fillwork.values_list('workorder', flat=True))
        other_orders = set(other_company_fillwork.values_list('workorder', flat=True))
        common_orders = company_orders.intersection(other_orders)
        
        if common_orders:
            print(f"   ⚠ 公司 {company.company_name} 發現跨公司資料污染:")
            for order in common_orders:
                print(f"     工單號碼 {order} 存在於多個公司")
        else:
            print(f"   ✓ 公司 {company.company_name} 資料隔離正常")
    
    # 5. 檢查生產記錄的公司隔離
    print("\n5. 生產記錄公司隔離檢查:")
    
    # 檢查生產記錄是否正確關聯到工單
    production_without_workorder = WorkOrderProductionDetail.objects.filter(
        workorder_production__workorder__isnull=True
    )
    
    if production_without_workorder.exists():
        print(f"   ⚠ 發現 {production_without_workorder.count()} 筆生產記錄沒有關聯工單")
    else:
        print("   ✓ 所有生產記錄都正確關聯到工單")
    
    # 6. 檢查資料一致性問題
    print("\n6. 資料一致性檢查:")
    
    # 檢查生產記錄和填報記錄的狀態一致性
    inconsistent_records = []
    
    for wo in WorkOrder.objects.all():
        # 檢查該工單的生產記錄
        production_records = WorkOrderProductionDetail.objects.filter(
            workorder_production__workorder=wo
        )
        
        for prod in production_records:
            if prod.report_source == 'fill_work':
                # 查找對應的填報記錄
                fillwork_record = FillWork.objects.filter(
                    workorder=wo.order_number,
                    product_id=wo.product_code,
                    process__name=prod.process_name,
                    work_quantity=prod.work_quantity
                ).first()
                
                if fillwork_record:
                    if prod.approval_status != fillwork_record.approval_status:
                        inconsistent_records.append({
                            'workorder': wo.order_number,
                            'process': prod.process_name,
                            'production_status': prod.approval_status,
                            'fillwork_status': fillwork_record.approval_status,
                            'production_id': prod.id,
                            'fillwork_id': fillwork_record.id
                        })
    
    if inconsistent_records:
        print(f"   ⚠ 發現 {len(inconsistent_records)} 筆狀態不一致的記錄:")
        for record in inconsistent_records:
            print(f"     工單 {record['workorder']} 工序 {record['process']}:")
            print(f"       生產記錄狀態: {record['production_status']} (ID: {record['production_id']})")
            print(f"       填報記錄狀態: {record['fillwork_status']} (ID: {record['fillwork_id']})")
    else:
        print("   ✓ 生產記錄和填報記錄狀態一致")
    
    # 7. 檢查唯一識別邏輯的應用
    print("\n7. 唯一識別邏輯應用檢查:")
    
    # 檢查關鍵查詢是否都使用了完整的三元組識別
    test_workorder = WorkOrder.objects.first()
    if test_workorder:
        print(f"   測試工單: {test_workorder.order_number}")
        
        # 檢查各種查詢方式
        queries_to_test = [
            {
                'name': '只用工單號碼查詢',
                'query': WorkOrder.objects.filter(order_number=test_workorder.order_number)
            },
            {
                'name': '用工單號碼+公司代號查詢',
                'query': WorkOrder.objects.filter(
                    order_number=test_workorder.order_number,
                    company_code=test_workorder.company_code
                )
            },
            {
                'name': '用完整三元組查詢',
                'query': WorkOrder.objects.filter(
                    order_number=test_workorder.order_number,
                    company_code=test_workorder.company_code,
                    product_code=test_workorder.product_code
                )
            }
        ]
        
        for test in queries_to_test:
            count = test['query'].count()
            print(f"     {test['name']}: {count} 筆記錄")
            if count > 1 and '完整三元組' not in test['name']:
                print(f"       ⚠ 可能違反唯一識別原則")
    
    # 8. 總結報告
    print("\n" + "=" * 60)
    print("審計總結:")
    
    issues_found = []
    if duplicate_orders.exists():
        issues_found.append("工單號碼重複")
    if duplicate_combinations.exists():
        issues_found.append("唯一識別組合重複")
    if inconsistent_records:
        issues_found.append("資料狀態不一致")
    
    if issues_found:
        print(f"   ⚠ 發現 {len(issues_found)} 個架構問題:")
        for issue in issues_found:
            print(f"     - {issue}")
        print("\n   建議:")
        print("     1. 立即修正資料不一致問題")
        print("     2. 加強唯一識別約束")
        print("     3. 完善多公司隔離機制")
        print("     4. 建立資料一致性檢查機制")
    else:
        print("   ✓ 多公司架構設計符合規範")

if __name__ == "__main__":
    audit_multi_company_architecture() 