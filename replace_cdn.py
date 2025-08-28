#!/usr/bin/env python3
"""
批量替換 CDN 為本地資源的腳本
"""
import os
import re

def replace_cdn_in_file(file_path):
    """替換單個檔案中的 CDN 連結"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 替換 Bootstrap CSS
        content = re.sub(
            r'https://cdn\.jsdelivr\.net/npm/bootstrap@[^/]+/dist/css/bootstrap\.min\.css',
            '{% static \'bootstrap/css/bootstrap.min.css\' %}',
            content
        )
        
        # 替換 Bootstrap JS
        content = re.sub(
            r'https://cdn\.jsdelivr\.net/npm/bootstrap@[^/]+/dist/js/bootstrap\.bundle\.min\.js',
            '{% static \'bootstrap/js/bootstrap.bundle.min.js\' %}',
            content
        )
        
        # 替換 Font Awesome
        content = re.sub(
            r'https://cdnjs\.cloudflare\.com/ajax/libs/font-awesome/[^/]+/css/all\.min\.css',
            '{% static \'fontawesome/css/all.min.css\' %}',
            content
        )
        
        # 替換 Chart.js
        content = re.sub(
            r'https://cdn\.jsdelivr\.net/npm/chart\.js(?:@[^/]+)?',
            '{% static \'js/chart.min.js\' %}',
            content
        )
        
        # 如果內容有變更，寫回檔案
        if content != original_content:
            # 確保檔案開頭有 {% load static %}
            if '{% load static %}' not in content and '{% static' in content:
                content = '{% load static %}\n' + content
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ 已更新: {file_path}")
            return True
        else:
            print(f"⏭️  無需更新: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ 處理失敗 {file_path}: {str(e)}")
        return False

def main():
    """主函數"""
    print("=== 批量替換 CDN 為本地資源 ===")
    
    # 需要處理的目錄
    directories = [
        'templates',
        'material/templates',
        'scheduling/templates',
        'system/templates',
        'equip/templates',
        'reporting/templates',
        'process/templates',
        'workorder/templates',
        'static/docs',
        'staticfiles/docs'
    ]
    
    total_files = 0
    updated_files = 0
    
    for directory in directories:
        if not os.path.exists(directory):
            continue
            
        print(f"\n📁 處理目錄: {directory}")
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.html'):
                    file_path = os.path.join(root, file)
                    total_files += 1
                    
                    if replace_cdn_in_file(file_path):
                        updated_files += 1
    
    print(f"\n🎉 處理完成！")
    print(f"總檔案數: {total_files}")
    print(f"更新檔案數: {updated_files}")
    print(f"跳過檔案數: {total_files - updated_files}")

if __name__ == '__main__':
    main()
