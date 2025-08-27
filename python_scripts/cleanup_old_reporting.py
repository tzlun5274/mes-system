#!/usr/bin/env python3
"""
清理舊報工記錄模組引用的腳本
"""

import os
import re

def clean_file(file_path):
    """清理檔案中的舊報工記錄模組引用"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 要移除的 import 語句模式
        patterns_to_remove = [
            r'from workorder\.workorder_reporting\.models import.*\n',
            r'from \.workorder_reporting\.models import.*\n',
            r'from workorder\.workorder_reporting\.models import.*',
            r'from \.workorder_reporting\.models import.*',
            r', BackupOperatorSupplementReport.*\n',
            r', BackupSMTSupplementReport.*\n',
            r', BackupSMTRealtimeReport.*\n',
            r'BackupOperatorSupplementReport.*\n',
            r'BackupSMTSupplementReport.*\n',
            r'BackupSMTRealtimeReport.*\n',
        ]
        
        # 移除模式
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '', content)
        
        # 移除空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ 已清理: {file_path}")
        
    except Exception as e:
        print(f"✗ 清理失敗: {file_path} - {e}")

def main():
    """主函數"""
    print("=== 開始清理舊報工記錄模組引用 ===")
    
    # 要清理的檔案列表
    files_to_clean = [
        'workorder/models.py',
        'workorder/admin.py',
        'workorder/views_main.py',
        'workorder/views/workorder_views.py',
        'workorder/views/report_views.py',
        'workorder/supervisor/signals.py',
        'workorder/supervisor/views.py',
        'workorder/supervisor/services.py',
        'workorder/services.py',
        'workorder/services/completion_service.py',
        'workorder/services/statistics_service.py',
        'workorder/services/process_update_service.py',
        'workorder/services/production_sync_service.py',
        'workorder/views_import.py',
        'workorder/management/commands/debug_sync_production_reports.py',
        'workorder/management/commands/從相同工單補充產品編號.py',
        'workorder/management/commands/clear_workorder_status_only.py',
        'workorder/management/commands/處理重複工單記錄.py',
        'workorder/management/commands/填報紀錄複製到生產中.py',
    ]
    
    for file_path in files_to_clean:
        if os.path.exists(file_path):
            clean_file(file_path)
        else:
            print(f"- 檔案不存在: {file_path}")
    
    print("=== 清理完成 ===")

if __name__ == "__main__":
    main() 