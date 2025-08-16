"""
工單Excel匯入處理模組
負責處理從正航系統匯出的製令簡要表匯入工單功能
"""

import pandas as pd
import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.db import transaction
from datetime import datetime
from io import BytesIO
import re

from ..models import WorkOrder
from erp_integration.models import CompanyConfig
from ..workorder_erp.models import PrdMKOrdMain, CompanyOrder

logger = logging.getLogger(__name__)

def import_user_required(user):
    """
    檢查用戶是否為超級用戶或具有匯入權限
    """
    return user.is_superuser or user.groups.filter(name="報表使用者").exists()

@login_required
@user_passes_test(import_user_required, login_url='/login/')
def workorder_import_page(request):
    """
    工單Excel匯入頁面
    顯示匯入介面和欄位格式說明
    """
    return render(request, 'workorder/import/workorder_import.html')

@csrf_exempt
@login_required
@user_passes_test(import_user_required, login_url='/login/')
def workorder_import_file(request):
    """
    工單Excel檔案匯入處理
    
    支援的欄位格式（正航製令簡要表）：
    公司名稱	公司代號	製令單號	產品編號	產品名稱	生產數量	預計開工日	預計完工日	製令狀態	備註
    
    必填欄位：公司名稱/公司代號、製令單號、產品編號、生產數量
    選填欄位：產品名稱、預計開工日、預計完工日、製令狀態、備註
    """
    
    # 檢查權限
    if not import_user_required(request.user):
        return JsonResponse({
            'success': False,
            'message': '您沒有權限執行此操作。請聯繫管理員取得匯入權限。'
        })
    
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': '只支援 POST 請求'
        })
    
    try:
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return JsonResponse({
                'success': False,
                'message': '沒有選擇檔案'
            })
        
        # 檢查檔案格式
        file_name = uploaded_file.name.lower()
        if not (file_name.endswith('.xlsx') or file_name.endswith('.csv')):
            return JsonResponse({
                'success': False,
                'message': '只支援 Excel (.xlsx) 或 CSV 格式檔案'
            })
        
        # 讀取檔案內容
        try:
            if file_name.endswith('.xlsx'):
                df = pd.read_excel(uploaded_file)
            else:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
        except Exception as e:
            logger.error(f"檔案讀取失敗: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'檔案讀取失敗: {str(e)}'
            })
        
        # 檢查必要欄位
        required_columns = ['製令單號', '產品編號', '生產數量']
        
        # 檢查公司識別欄位（公司名稱或公司代號至少要有其中一個）
        company_columns = ['公司名稱', '公司代號']
        has_company_column = any(col in df.columns for col in company_columns)
        
        if not has_company_column:
            return JsonResponse({
                'success': False,
                'message': f'缺少公司識別欄位，請包含「公司名稱」或「公司代號」其中一個欄位'
            })
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return JsonResponse({
                'success': False,
                'message': f'缺少必要欄位: {", ".join(missing_columns)}'
            })
        
        # 處理匯入資料
        result = process_workorder_import(df, request.user)
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"工單匯入處理失敗: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'匯入處理失敗: {str(e)}'
        })

def process_workorder_import(df, user):
    """
    處理工單匯入資料
    """
    
    # 統計資訊
    total_records = len(df)
    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0
    errors = []
    
    # 取得公司配置
    company_configs = {config.company_name: config.company_code 
                      for config in CompanyConfig.objects.all()}
    
    try:
        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    # 提取資料
                    order_number = str(row['製令單號']).strip()
                    product_code = str(row['產品編號']).strip()
                    quantity = row['生產數量']
                    
                    # 檢查必要欄位
                    if not order_number or not product_code or pd.isna(quantity):
                        error_count += 1
                        errors.append({
                            'row': index + 2,  # Excel行號從2開始
                            'error': '缺少必要欄位：製令單號、產品編號或生產數量'
                        })
                        continue
                    
                    # 查找公司代號
                    company_code = None
                    
                    # 方法1: 從Excel欄位直接取得公司代號
                    if '公司代號' in df.columns:
                        company_code = str(row['公司代號']).strip()
                        if not company_code or company_code == 'nan':
                            company_code = None
                    
                    # 方法2: 從公司名稱查找公司代號
                    if not company_code and '公司名稱' in df.columns:
                        company_name = str(row['公司名稱']).strip()
                        if company_name and company_name != 'nan':
                            company_config = CompanyConfig.objects.filter(
                                company_name__icontains=company_name
                            ).first()
                            if company_config:
                                company_code = company_config.company_code
                    
                    # 方法3: 從製令單號推測公司代號（備用方法）
                    if not company_code:
                        if order_number.startswith('331-'):
                            company_code = '02'  # 中儀科技
                        elif order_number.startswith('330-'):
                            company_code = '10'  # 耀儀科技
                        elif order_number == 'RD樣品':
                            company_code = '10'  # RD樣品通常屬於耀儀科技
                    
                    # 方法4: 從製令資料查找
                    if not company_code:
                        mkord_main = PrdMKOrdMain.objects.filter(
                            MKOrdNO=order_number,
                            ProductID=product_code
                        ).first()
                        
                        if mkord_main:
                            company_order = CompanyOrder.objects.filter(
                                mkordno=order_number,
                                product_id=product_code
                            ).first()
                            
                            if company_order:
                                company_code = company_order.company_code
                    
                    # 如果還是找不到公司代號，使用預設值
                    if not company_code:
                        company_code = '02'  # 預設為中儀科技
                    
                    # 處理數量欄位
                    try:
                        quantity = int(float(quantity))
                        if quantity <= 0:
                            raise ValueError("生產數量必須大於0")
                    except (ValueError, TypeError):
                        error_count += 1
                        errors.append({
                            'row': index + 2,
                            'error': f'生產數量格式錯誤: {quantity}'
                        })
                        continue
                    

                    
                    # 檢查工單是否已存在
                    existing_workorder = WorkOrder.objects.filter(
                        company_code=company_code,
                        order_number=order_number,
                        product_code=product_code
                    ).first()
                    
                    if existing_workorder:
                        # 略過已存在的工單
                        skipped_count += 1
                        logger.info(f"略過已存在的工單: {existing_workorder}")
                    else:
                        # 創建新工單
                        new_workorder = WorkOrder.objects.create(
                            company_code=company_code,
                            order_number=order_number,
                            product_code=product_code,
                            quantity=quantity,
                            status='pending',
                            order_source='erp'  # 從ERP匯入的工單
                        )
                        created_count += 1
                        logger.info(f"創建工單: {new_workorder}")
                    
                except Exception as e:
                    error_count += 1
                    errors.append({
                        'row': index + 2,
                        'error': str(e)
                    })
                    logger.error(f"處理第{index + 2}行時發生錯誤: {e}")
        
        # 記錄匯入結果
        logger.info(f"工單匯入完成 - 總記錄: {total_records}, 創建: {created_count}, "
                   f"略過: {skipped_count}, 錯誤: {error_count}")
        
        return {
            'success': True,
            'message': f'匯入完成！創建 {created_count} 個工單，略過 {skipped_count} 個重複工單，'
                      f'處理 {error_count} 個錯誤記錄。',
            'data': {
                'total_records': total_records,
                'created_count': created_count,
                'updated_count': 0,  # 不再有更新，統一略過
                'skipped_count': skipped_count,
                'error_count': error_count,
                'errors': errors[:10]  # 只返回前10個錯誤
            }
        }
        
    except Exception as e:
        logger.error(f"工單匯入事務失敗: {str(e)}")
        return {
            'success': False,
            'message': f'匯入事務失敗: {str(e)}',
            'data': {
                'total_records': total_records,
                'created_count': 0,
                'updated_count': 0,
                'skipped_count': 0,
                'error_count': total_records,
                'errors': [{'row': 1, 'error': str(e)}]
            }
        }

@login_required
@user_passes_test(import_user_required, login_url='/login/')
def download_workorder_template(request):
    """
    下載工單匯入範本
    """
    import io
    from django.http import HttpResponse
    
    # 建立範本資料
    template_data = {
        '公司名稱': ['中儀科技', '耀儀科技', '耀儀科技'],
        '公司代號': ['02', '10', '10'],
        '製令單號': ['331-25808001', '331-25721001', 'RD樣品'],
        '產品編號': ['PFP-SSP-SKP1SP026V2PO-500', 'PFP-CCT006CB0061E-500', 'PFP-EDAC2S1PDMRVO-500'],
        '產品名稱': ['SSP產品', 'CCT產品', 'RD樣品產品'],
        '生產數量': [100, 200, 50],
        '預計開工日': ['2025-08-15', '2025-08-16', '2025-08-17'],
        '預計完工日': ['2025-08-20', '2025-08-21', '2025-08-22'],
        '製令狀態': ['待生產', '生產中', '已完成'],
        '備註': ['正常製令', '急件', '樣品']
    }
    
    # 建立DataFrame
    df = pd.DataFrame(template_data)
    
    # 建立Excel檔案
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='工單匯入範本', index=False)
        
        # 取得工作表
        worksheet = writer.sheets['工單匯入範本']
        
        # 設定欄寬
        column_widths = {
            'A': 15,  # 公司名稱
            'B': 12,  # 公司代號
            'C': 15,  # 製令單號
            'D': 30,  # 產品編號
            'E': 20,  # 產品名稱
            'F': 12,  # 生產數量
            'G': 12,  # 預計開工日
            'H': 12,  # 預計完工日
            'I': 12,  # 製令狀態
            'J': 20,  # 備註
        }
        
        for col, width in column_widths.items():
            worksheet.column_dimensions[col].width = width
    
    output.seek(0)
    
    # 建立HTTP回應
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="工單匯入範本.xlsx"'
    
    return response 