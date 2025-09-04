import os
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django import forms
from django.core.mail import get_connection, send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.views import View
# from system.models import EmailConfig  # 暫時註解，重新創建中
import logging
import smtplib

# 設置日誌，統一寫入設定檔指定的日誌目錄
from django.conf import settings
logger = logging.getLogger("mes_setup")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(os.path.join(settings.LOG_BASE_DIR, "setup_project.log"))
formatter = logging.Formatter("%(levelname)s %(asctime)s %(module)s %(message)s")
handler.setFormatter(formatter)
logger.handlers = [handler]


# 首頁視圖
@login_required
def home(request):
    logger.info("訪問首頁視圖")
    return render(request, "home.html", {})


# 自定義密碼重置表單，驗證郵箱是否存在
class CustomPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data["email"]
        logger.info(f"驗證郵箱: {email}")
        if not User.objects.filter(email__iexact=email).exists():
            logger.error(f"郵箱 {email} 未註冊")
            raise forms.ValidationError(
                "此電子郵件地址未註冊，請確認您的電子郵件地址是否正確。"
            )
        logger.info(f"郵箱 {email} 驗證通過")
        return email


# 測試 SMTP 連線的函數
def test_smtp_connection(email_config):
    try:
        logger.info(
            f"測試 SMTP 連線: host={email_config.email_host}, port={email_config.email_port}"
        )
        server = smtplib.SMTP(
            email_config.email_host, email_config.email_port, timeout=5
        )
        if email_config.email_use_tls:
            server.starttls()
        if email_config.email_host_user and email_config.email_host_password:
            server.login(email_config.email_host_user, email_config.email_host_password)
        server.quit()
        logger.info("SMTP 連線測試成功")
        return True
    except Exception as e:
        logger.error(f"SMTP 連線測試失敗: {str(e)}")
        return False


# 自定義密碼重置視圖，直接使用 send_mail 發送郵件
class CustomPasswordResetView(View):
    form_class = CustomPasswordResetForm
    template_name = "registration/password_reset_form.html"

    def get(self, request, *args, **kwargs):
        logger.info("訪問密碼重置頁面 (GET 方法)")
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        logger.info("提交密碼重置請求 (POST 方法)")
        form = self.form_class(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            logger.info(f"準備發送密碼重置郵件至: {email}")

            # 從資料庫中抓取 EmailConfig
            try:
                email_config = EmailConfig.objects.get(id=1)
            except EmailConfig.DoesNotExist:
                logger.error("EmailConfig 未找到，無法發送密碼重置郵件")
                form.add_error(None, "郵件主機設定未找到，請聯繫管理員")
                return render(request, self.template_name, {"form": form})

            # 檢查必要欄位
            if not email_config.email_host or not email_config.email_port:
                logger.error("EmailConfig 設定錯誤: 主機或端口為空")
                form.add_error(None, "郵件主機設定無效（主機或端口為空），請聯繫管理員")
                return render(request, self.template_name, {"form": form})

            # 記錄從資料庫加載的設定
            logger.info(
                f"從 EmailConfig 加載郵件設定: host={email_config.email_host}, port={email_config.email_port}, use_tls={email_config.email_use_tls}, user={email_config.email_host_user}, from_email={email_config.default_from_email}"
            )

            # 測試 SMTP 連線
            if not test_smtp_connection(email_config):
                logger.error("無法連接到 SMTP 伺服器，無法發送密碼重置郵件")
                form.add_error(None, "無法連接到郵件伺服器，請聯繫管理員")
                return render(request, self.template_name, {"form": form})

            # 設置 SMTP 配置
            connection = get_connection(
                backend="django.core.mail.backends.smtp.EmailBackend",
                host=email_config.email_host,
                port=email_config.email_port,
                username=email_config.email_host_user,
                password=email_config.email_host_password,
                use_tls=email_config.email_use_tls,
            )

            # 獲取用戶並生成重設密碼的鏈接
            try:
                user = User.objects.get(email__iexact=email)
                subject = "MES 系統 - 密碼重置請求"
                # 生成重設密碼的令牌和鏈接
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_url = request.build_absolute_uri(
                    reverse(
                        "password_reset_confirm", kwargs={"uidb64": uid, "token": token}
                    )
                )
                message = (
                    f"您好 {user.get_username()}，\n\n"
                    f"您收到此郵件是因為您（或某人）請求重設 MES 系統的密碼。\n\n"
                    f"請點擊以下鏈接以設置新密碼：\n"
                    f"{reset_url}\n\n"
                    f"如果您沒有發起此請求，可以忽略此郵件，您的密碼將不會被更改。\n\n"
                    f"感謝您使用 MES 系統！\n\n"
                    f"MES 系統團隊"
                )
                from_email = email_config.default_from_email
                recipient_list = [email]

                # 使用 send_mail 發送郵件，與步驟 24 的方式一致
                send_mail(
                    subject,
                    message,
                    from_email,
                    recipient_list,
                    fail_silently=False,
                    connection=connection,
                )
                logger.info(f"密碼重置郵件發送成功至: {email}")

                # 跳轉到成功頁面
                return redirect("password_reset_done")
            except User.DoesNotExist:
                logger.error(f"用戶未找到: {email}")
                form.add_error(None, "用戶未找到，請確認電子郵件地址")
                return render(request, self.template_name, {"form": form})
            except Exception as e:
                logger.error(f"密碼重置郵件發送失敗: {email}, 錯誤: {str(e)}")
                # 備用方案：記錄郵件內容，供管理員手動處理
                with open(os.path.join(settings.LOG_BASE_DIR, "failed_emails.log"), "a") as f:
                    f.write(f"[{email}] 密碼重置郵件發送失敗: {str(e)}\n")
                form.add_error(None, "無法發送密碼重置郵件，請聯繫管理員")
                return render(request, self.template_name, {"form": form})
        logger.info("表單無效，返回密碼重置頁面")
        return render(request, self.template_name, {"form": form})

# 資料庫錯誤頁面視圖
def database_error(request):
    """
    顯示資料庫連線錯誤頁面
    """
    logger.error("顯示資料庫連線錯誤頁面")
    return render(request, "system/database_error.html", {
        "title": "資料庫連線錯誤"
    })
