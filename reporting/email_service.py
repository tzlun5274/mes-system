"""
郵件發送服務
只負責郵件發送相關的邏輯
"""

import logging
import os
from django.core.mail import EmailMessage, get_connection
from django.conf import settings
from system.models import EmailConfig

logger = logging.getLogger(__name__)


class EmailService:
    """郵件發送服務 - 只負責郵件發送"""
    
    def __init__(self):
        self.email_config = None
        self._load_email_config()
    
    def _load_email_config(self):
        """載入郵件設定"""
        try:
            self.email_config = EmailConfig.objects.first()
            if not self.email_config:
                logger.warning("未找到郵件設定")
        except Exception as e:
            logger.error(f"載入郵件設定失敗: {str(e)}")
    
    def send_report_email(self, schedule, result):
        """發送報表郵件"""
        try:
            if not self.email_config:
                logger.error("未找到郵件設定，無法發送郵件")
                return False
            
            # 設定郵件連線
            connection = get_connection(
                host=self.email_config.email_host,
                port=self.email_config.email_port,
                username=self.email_config.email_host_user,
                password=self.email_config.email_host_password,
                use_tls=self.email_config.email_use_tls,
            )
            
            from_email = self.email_config.default_from_email or settings.DEFAULT_FROM_EMAIL
            
            # 建立郵件
            subject = f"自動報表 - {schedule.name}"
            body = self._generate_email_body(schedule, result)
            
            # 取得收件人列表
            recipients = self._parse_recipients(schedule.email_recipients)
            if not recipients:
                logger.warning(f"排程 {schedule.name} 沒有設定收件人")
                return False
            
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=from_email,
                to=recipients,
                connection=connection
            )
            email.content_subtype = "html"  # 設定為 HTML 格式
            
            # 附加檔案
            self._attach_files_to_email(email, schedule, result)
            
            # 發送郵件
            email.send()
            logger.info(f"報表郵件已發送: {schedule.name} -> {recipients}")
            return True
            
        except Exception as e:
            logger.error(f"發送報表郵件失敗: {str(e)}")
            return False
    
    def _generate_email_body(self, schedule, result):
        """生成郵件內容"""
        if schedule.report_type == 'data_sync':
            return self._generate_data_sync_email_body(schedule, result)
        else:
            return self._generate_report_email_body(schedule, result)
    
    def _generate_data_sync_email_body(self, schedule, result):
        """生成資料同步郵件內容"""
        return f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .content {{ background-color: #ffffff; padding: 20px; border: 1px solid #dee2e6; border-radius: 5px; }}
                .footer {{ margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; font-size: 12px; color: #6c757d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>自動報表系統</h2>
                </div>
                <div class="content">
                    <h3>填報與現場記錄資料同步完成</h3>
                    <p>排程名稱：{schedule.name}</p>
                    <p>執行時間：{result.get('executed_at', '')}</p>
                    <p>同步結果：{result.get('message', '')}</p>
                </div>
                <div class="footer">
                    <p>此郵件由 MES 系統自動發送</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_report_email_body(self, schedule, result):
        """生成報表郵件內容"""
        return f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .content {{ background-color: #ffffff; padding: 20px; border: 1px solid #dee2e6; border-radius: 5px; }}
                .footer {{ margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; font-size: 12px; color: #6c757d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>自動報表系統</h2>
                </div>
                <div class="content">
                    <h3>報表生成完成</h3>
                    <p>排程名稱：{schedule.name}</p>
                    <p>報表類型：{schedule.get_report_type_display()}</p>
                    <p>檔案名稱：{result.get('filename', '')}</p>
                    <p>生成時間：{result.get('message', '')}</p>
                    <p>請查看附件中的報表檔案。</p>
                </div>
                <div class="footer">
                    <p>此郵件由 MES 系統自動發送</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _parse_recipients(self, recipients_str):
        """解析收件人字串"""
        if not recipients_str:
            return []
        
        # 支援多種分隔符號：逗號、分號、換行
        import re
        recipients = re.split(r'[,;\n]', recipients_str)
        return [email.strip() for email in recipients if email.strip()]
    
    def _attach_files_to_email(self, email, schedule, result):
        """附加檔案到郵件"""
        try:
            # 根據檔案格式附加對應的檔案
            if schedule.file_format == 'both':
                # 同時附加 HTML 和 Excel 檔案
                if result.get('html_path') and os.path.exists(result['html_path']):
                    self._attach_single_file(email, result['html_path'], 'text/html')
                if result.get('excel_path') and os.path.exists(result['excel_path']):
                    self._attach_single_file(email, result['excel_path'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            elif schedule.file_format == 'excel':
                # 只附加 Excel 檔案
                if result.get('file_path') and os.path.exists(result['file_path']):
                    self._attach_single_file(email, result['file_path'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            else:
                # 預設附加 HTML 檔案
                if result.get('file_path') and os.path.exists(result['file_path']):
                    self._attach_single_file(email, result['file_path'], 'text/html')
                    
        except Exception as e:
            logger.error(f"附加檔案失敗: {str(e)}")
    
    def _attach_single_file(self, email, file_path, mime_type):
        """附加單一檔案 - 使用 Outlook 專用編碼"""
        try:
            # 取得檔案名稱
            filename = os.path.basename(file_path)
            
            # 使用 Outlook 專用編碼
            from email.mime.base import MIMEBase
            from email import encoders
            from email.header import Header
            
            with open(file_path, 'rb') as f:
                if filename.endswith('.html'):
                    # HTML 檔案
                    attachment = MIMEBase('text', 'html')
                elif filename.endswith('.xlsx'):
                    # Excel 檔案
                    attachment = MIMEBase('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                elif filename.endswith('.xls'):
                    # Excel 檔案 (舊版)
                    attachment = MIMEBase('application', 'vnd.ms-excel')
                else:
                    # 其他檔案
                    attachment = MIMEBase('application', 'octet-stream')
                
                attachment.set_payload(f.read())
                encoders.encode_base64(attachment)
                
                # Outlook 專用編碼 - 使用 email.header.Header 確保中文檔案名稱正確顯示
                encoded_filename = Header(filename, 'utf-8').encode()
                attachment.add_header('Content-Disposition', 'attachment', filename=encoded_filename)
                email.attach(attachment)
            
            logger.info(f"已附加檔案: {filename}")
        except Exception as e:
            logger.error(f"附加檔案 {file_path} 失敗: {str(e)}")
    
    def test_email_connection(self):
        """測試郵件連線"""
        try:
            if not self.email_config:
                return False, "未找到郵件設定"
            
            connection = get_connection(
                host=self.email_config.email_host,
                port=self.email_config.email_port,
                username=self.email_config.email_host_user,
                password=self.email_config.email_host_password,
                use_tls=self.email_config.email_use_tls,
            )
            
            # 測試連線
            connection.open()
            connection.close()
            
            return True, "郵件連線測試成功"
            
        except Exception as e:
            return False, f"郵件連線測試失敗: {str(e)}"
