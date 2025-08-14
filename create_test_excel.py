#!/usr/bin/env python3
"""
建立測試用的工單Excel檔案
模擬從正航系統匯出的製令簡要表
"""

import pandas as pd
import os

def create_test_excel():
    """建立測試用的Excel檔案"""
    
    # 測試資料
    test_data = {
        '公司名稱': [
            '中儀科技',
            '耀儀科技',
            '耀儀科技',
            '耀儀科技',
            '耀儀科技',
            '中儀科技',
            '耀儀科技',
            '中儀科技',
            '中儀科技',
            '中儀科技'
        ],
        '公司代號': [
            '02',
            '10',
            '10',
            '10',
            '10',
            '02',
            '10',
            '02',
            '02',
            '02'
        ],
        '製令單號': [
            '331-25808001',
            '331-25721001', 
            '331-25730004',
            '330-25205001',
            'RD樣品',
            '331-25807001',
            '331-25728001',
            '331-25722003',
            '331-25724001',
            '331-25729001'
        ],
        '產品編號': [
            'PFP-SSP-SKP1SP026V2PO-500',
            'PFP-CCT006CB0061E-500',
            'PFP-CCTBRADY3S1PV1R0-500',
            'PFP-CCTNP8016-812',
            'PFP-EDAC2S1PDMRVO-500',
            'PFP-CCTSKP6SP001V1P2-501',
            'PFP-CCTOTCTS17-500',
            'PFP-CCTSYN180428NTHSX1-801',
            'PFP-CCTNP8016-812',
            'PFP-CCTCT180428HF-800'
        ],
        '產品名稱': [
            'SSP產品A',
            'CCT產品B',
            'CCT產品C',
            'CCT產品D',
            'RD樣品產品',
            'SSP產品E',
            'CCT產品F',
            'CCT產品G',
            'CCT產品H',
            'CCT產品I'
        ],
        '生產數量': [
            100,
            200,
            150,
            80,
            50,
            120,
            180,
            90,
            110,
            160
        ],
        '預計開工日': [
            '2025-08-15',
            '2025-08-16',
            '2025-08-17',
            '2025-08-18',
            '2025-08-19',
            '2025-08-20',
            '2025-08-21',
            '2025-08-22',
            '2025-08-23',
            '2025-08-24'
        ],
        '預計完工日': [
            '2025-08-20',
            '2025-08-21',
            '2025-08-22',
            '2025-08-23',
            '2025-08-24',
            '2025-08-25',
            '2025-08-26',
            '2025-08-27',
            '2025-08-28',
            '2025-08-29'
        ],
        '製令狀態': [
            '待生產',
            '生產中',
            '待生產',
            '已完成',
            '待生產',
            '生產中',
            '待生產',
            '已完成',
            '待生產',
            '生產中'
        ],
        '備註': [
            '正常製令',
            '急件',
            '正常製令',
            '已完成',
            '樣品',
            '正常製令',
            '急件',
            '已完成',
            '正常製令',
            '急件'
        ]
    }
    
    # 建立DataFrame
    df = pd.DataFrame(test_data)
    
    # 建立Excel檔案
    filename = 'test_workorder_import.xlsx'
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='製令簡要表', index=False)
        
        # 取得工作表
        worksheet = writer.sheets['製令簡要表']
        
        # 設定欄寬
        column_widths = {
            'A': 15,  # 公司名稱
            'B': 12,  # 公司代號
            'C': 15,  # 製令單號
            'D': 35,  # 產品編號
            'E': 20,  # 產品名稱
            'F': 12,  # 生產數量
            'G': 12,  # 預計開工日
            'H': 12,  # 預計完工日
            'I': 12,  # 製令狀態
            'J': 20,  # 備註
        }
        
        for col, width in column_widths.items():
            worksheet.column_dimensions[col].width = width
    
    print(f"測試Excel檔案已建立: {filename}")
    print(f"檔案大小: {os.path.getsize(filename)} bytes")
    print(f"包含 {len(df)} 筆記錄")
    
    # 顯示前幾筆資料
    print("\n前5筆資料:")
    print(df.head().to_string(index=False))
    
    return filename

if __name__ == "__main__":
    create_test_excel() 