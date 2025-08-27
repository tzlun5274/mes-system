import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group, Permission
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, SetPasswordForm
from django import forms
from .forms import (
    EmailConfigForm,
    CustomUserCreationForm,
    BackupScheduleForm,
    OperationLogConfigForm,
    UserWorkPermissionForm,
    AutoApprovalSettingsForm
)
from .models import (
    EmailConfig, 
    BackupSchedule, 
    OperationLogConfig,
    UserWorkPermission,
    AutoApprovalSettings,
    CleanupLog
)
from django.core.mail import get_connection, send_mail
from django.http import HttpResponse, FileResponse, JsonResponse
import os
import subprocess
import datetime
import smtplib
from django_celery_beat.models import PeriodicTask, CrontabSchedule, IntervalSchedule
from .tasks import auto_backup_database
import csv
import openpyxl
from django.utils import timezone
from django.urls import get_resolver, reverse_lazy
from django.conf import settings
import shutil
import glob
from django.db.models import Q
from datetime import timedelta
from django.views.generic import UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, DeleteView
from .models import ScheduledTask
from .forms import ScheduledTaskForm
from system.models import AutoApprovalTask

# 設定系統管理模組的日誌記錄器
from django.conf import settings
system_logger = logging.getLogger("system")
system_handler = logging.FileHandler(os.path.join(settings.SYSTEM_LOG_DIR, "system.log"))
system_handler.setFormatter(
    logging.Formatter("%(levelname)s %(asctime)s %(module)s %(message)s")
)
system_logger.addHandler(system_handler)
system_logger.setLevel(logging.INFO)

logger = logging.getLogger("django")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(os.path.join(settings.DJANGO_LOG_DIR, "mes.log"))
formatter = logging.Formatter("%(levelname)s %(asctime)s %(module)s %(message)s")
handler.setFormatter(formatter)
logger.handlers = [handler]

# 定義所有模組及其對應的 OperationLog 模型
MODULE_LOG_MODELS = {
    "equip": "equip.models.EquipOperationLog",
    "material": "material.models.MaterialOperationLog",
    "scheduling": "scheduling.models.SchedulingOperationLog",
    "process": "process.models.ProcessOperationLog",
    "quality": "quality.models.QualityOperationLog",
    "work_order": "workorder.models.WorkOrderOperationLog",
    "kanban": "kanban.models.KanbanOperationLog",
    "erp_integration": "erp_integration.models.ERPIntegrationOperationLog",
    "ai": "ai.models.AIOperationLog",
}


def superuser_required(user):
    return user.is_superuser


def get_module_display_name(module_name):
    try:
        module = __import__(f"{module_name}.urls", fromlist=["module_display_name"])
        return getattr(module, "module_display_name", module_name)
    except ImportError:
        return module_name


def get_all_permissions():
    all_modules = [
        "equip",
        "material",
        "scheduling",
        "process",
        "quality",
        "workorder",
        "kanban",
        "erp_integration",
        "ai",
    ]
    permissions = Permission.objects.filter(content_type__app_label__in=all_modules)
    return permissions


DEFAULT_GROUPS = [
    "設備使用者",
    "物料使用者",
    "排程使用者",
    "製程使用者",
    "品質使用者",
    "報表使用者",
    "看板使用者",
]

GROUP_TO_MODULE_MAP = {
    "設備使用者": "equip",
    "物料使用者": "material",
    "排程使用者": "scheduling",
    "製程使用者": "process",
    "品質使用者": "quality",
    "工單使用者": "workorder",
    
    "看板使用者": "kanban",
}

PERMISSION_NAME_TRANSLATIONS = {
    "Can add equipment": "可以添加設備",
    "Can change equipment": "可以更改設備",
    "Can delete equipment": "可以刪除設備",
    "Can view equipment": "可以查看設備",
    "Can add material": "可以添加物料",
    "Can change material": "可以更改物料",
    "Can delete material": "可以刪除物料",
    "Can view material": "可以查看物料",
    "Can add schedule": "可以添加排程",
    "Can change schedule": "可以更改排程",
    "Can delete schedule": "可以刪除排程",
    "Can view schedule": "可以查看排程",
    "Can add process": "可以添加製程",
    "Can change process": "可以更改製程",
    "Can delete process": "可以刪除製程",
    "Can view process": "可以查看製程",
    "Can add quality": "可以添加品質記錄",
    "Can change quality": "可以更改品質記錄",
    "Can delete quality": "可以刪除品質記錄",
    "Can view quality": "可以查看品質記錄",
    "Can add report": "可以添加報表",
    "Can change report": "可以更改報表",
    "Can delete report": "可以刪除報表",
    "Can view report": "可以查看報表",
    "Can add work_order": "可以添加工單",
    "Can change work_order": "可以更改工單",
    "Can delete work_order": "可以刪除工單",
    "Can view work_order": "可以查看工單",
    "Can add kanban": "可以添加看板",
    "Can change kanban": "可以更改看板",
    "Can delete kanban": "可以刪除看板",
    "Can view kanban": "可以查看看板",
    "Can add erp integration": "可以添加ERP整合記錄",
    "Can change erp integration": "可以更改ERP整合記錄",
    "Can delete erp integration": "可以刪除ERP整合記錄",
    "Can view erp integration": "可以查看ERP整合記錄",
    "Can add ai": "可以添加AI功能",
    "Can change ai": "可以更改AI功能",
    "Can delete ai": "可以刪除AI功能",
    "Can view ai": "可以查看AI功能",
    "Can add group": "可以添加群組",
    "Can change group": "可以更改群組",
    "Can delete group": "可以刪除群組",
    "Can view group": "可以查看群組",
    "Can add permission": "可以添加權限",
    "Can change permission": "可以更改權限",
    "Can delete permission": "可以刪除權限",
    "Can view permission": "可以查看權限",
    "Can add user": "可以添加使用者",
    "Can change user": "可以更改使用者",
    "Can delete user": "可以刪除使用者",
    "Can view user": "可以查看使用者",
    "Can add email config": "可以添加電子郵件配置",
    "Can change email config": "可以更改電子郵件配置",
    "Can delete email config": "可以刪除電子郵件配置",
    "Can view email config": "可以查看電子郵件配置",
    "Can add backup schedule": "可以添加備份計劃",
    "Can change backup schedule": "可以更改備份計劃",
    "Can delete backup schedule": "可以刪除備份計劃",
    "Can view backup schedule": "可以查看備份計劃",
    # 移除主管報工相關權限翻譯，避免混淆
    # 主管職責：監督、審核、管理，不代為報工
    "Can add operatorsupplementreport": "可以添加作業員補登報工記錄",
    "Can change operatorsupplementreport": "可以更改作業員補登報工記錄",
    "Can delete operatorsupplementreport": "可以刪除作業員補登報工記錄",
    "Can view operatorsupplementreport": "可以查看作業員補登報工記錄",
    "Can add smtproductionreport": "可以添加SMT報工記錄",
    "Can change smtproductionreport": "可以更改SMT報工記錄",
    "Can delete smtproductionreport": "可以刪除SMT報工記錄",
    "Can view smtproductionreport": "可以查看SMT報工記錄",
    "Can add smtsupplementreport": "可以添加SMT補報工記錄",
    "Can change smtsupplementreport": "可以更改SMT補報工記錄",
    "Can delete smtsupplementreport": "可以刪除SMT補報工記錄",
    "Can view smtsupplementreport": "可以查看SMT補報工記錄",
    "Can add smtworkreport": "可以添加SMT報工記錄",
    "Can change smtworkreport": "可以更改SMT報工記錄",
    "Can delete smtworkreport": "可以刪除SMT報工記錄",
    "Can view smtworkreport": "可以查看SMT報工記錄",
    "Can add smtworkreportlog": "可以添加SMT報工日誌",
    "Can change smtworkreportlog": "可以更改SMT報工日誌",
    "Can delete smtworkreportlog": "可以刪除SMT報工日誌",
    "Can view smtworkreportlog": "可以查看SMT報工日誌",
    "Can add supplementreport": "可以添加補登報工記錄",
    "Can change supplementreport": "可以更改補登報工記錄",
    "Can delete supplementreport": "可以刪除補登報工記錄",
    "Can view supplementreport": "可以查看補登報工記錄",
    "Can add workreport": "可以添加報工記錄",
    "Can change workreport": "可以更改報工記錄",
    "Can delete workreport": "可以刪除報工記錄",
    "Can view workreport": "可以查看報工記錄",
    "Can add workreportsummary": "可以添加報工摘要",
    "Can change workreportsummary": "可以更改報工摘要",
    "Can delete workreportsummary": "可以刪除報工摘要",
    "Can view workreportsummary": "可以查看報工摘要",
}


class CustomPermissionChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        logger.debug(f"處理權限: name='{obj.name}', codename='{obj.codename}'")
        if obj.name.startswith("可以"):
            logger.debug(f"使用自訂權限名稱: {obj.name}")
            return obj.name
        name_lower = obj.name.lower().strip()
        translations_lower = {
            k.lower().strip(): v for k, v in PERMISSION_NAME_TRANSLATIONS.items()
        }
        translated_name = translations_lower.get(name_lower, obj.name)
        if translated_name == obj.name:
            logger.warning(
                f"未找到權限 '{obj.name}' (codename: {obj.codename}) 的中文翻譯，映射表鍵: {list(translations_lower.keys())}"
            )
            codename_lower = obj.codename.lower().strip()
            translated_name = translations_lower.get(codename_lower, obj.name)
            if translated_name == obj.name:
                logger.warning(f"也未找到 codename '{obj.codename}' 的中文翻譯")
            else:
                logger.debug(
                    f"通過 codename 找到翻譯: '{obj.codename}' 翻譯為: {translated_name}"
                )
        else:
            logger.debug(f"權限 '{obj.name}' 翻譯為: {translated_name}")
        return translated_name


class GroupForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.name in DEFAULT_GROUPS:
            self.fields["name"].disabled = True
        if self.instance and self.instance.id:
            self.fields["permissions"] = CustomPermissionChoiceField(
                queryset=self.instance.permissions.all(),
                widget=forms.CheckboxSelectMultiple,
                required=False,
                label="權限",
                to_field_name="id",
            )
        else:
            self.fields["permissions"] = CustomPermissionChoiceField(
                queryset=get_all_permissions(),
                widget=forms.CheckboxSelectMultiple,
                required=False,
                label="權限",
                to_field_name="id",
            )

    class Meta:
        model = Group
        fields = ["name"]

    def clean_name(self):
        name = self.cleaned_data["name"]
        if (
            self.instance
            and self.instance.name in DEFAULT_GROUPS
            and name != self.instance.name
        ):
            raise forms.ValidationError("預設群組名稱不可更改！")
        return name


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def index(request):
    return render(request, "system/index.html", {})


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def user_list(request):
    users = User.objects.all()
    return render(request, "system/user_list.html", {"users": users})


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def user_add(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data["email"]
            user.save()
            messages.success(request, "用戶新增成功！")
            logger.info(
                f"用戶 {form.cleaned_data['username']} 由 {request.user.username} 新增"
            )
            return redirect("system:user_list")
    else:
        form = CustomUserCreationForm()
    return render(request, "system/user_form.html", {"form": form, "title": "新增用戶"})


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        form = UserChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "用戶編輯成功！")
            logger.info(f"用戶 {user.username} 由 {request.user.username} 編輯")
            return redirect("system:user_list")
    else:
        form = UserChangeForm(instance=user)
    return render(
        request,
        "system/user_form.html",
        {"form": form, "title": "編輯用戶", "user_id": user_id},
    )


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def user_change_password(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        form = SetPasswordForm(user=user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "用戶密碼已成功更改！")
            logger.info(f"用戶 {user.username} 的密碼由 {request.user.username} 更改")
            return redirect("system:user_list")
    else:
        form = SetPasswordForm(user=user)
    return render(
        request,
        "system/user_change_password.html",
        {"form": form, "title": "更改用戶密碼", "user_id": user_id},
    )


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        username = user.username
        user.delete()
        messages.success(request, "用戶刪除成功！")
        logger.info(f"用戶 {username} 由 {request.user.username} 刪除")
        return redirect("system:user_list")
    return redirect("system:user_list")


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def group_list(request):
    groups = Group.objects.all()
    display_groups = []
    for group in groups:
        module_name = GROUP_TO_MODULE_MAP.get(
            group.name, group.name.replace("使用者", "").lower()
        )
        display_name = get_module_display_name(module_name)
        display_groups.append({"id": group.id, "name": display_name})
    return render(request, "system/group_list.html", {"groups": display_groups})


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def group_add(request):
    if request.method == "POST":
        form = GroupForm(request.POST)
        if form.is_clean():
            group = form.save()
            permissions = form.cleaned_data["permissions"]
            group.permissions.set(permissions)
            module_name = GROUP_TO_MODULE_MAP.get(
                group.name, group.name.replace("使用者", "").lower()
            )
            display_name = get_module_display_name(module_name)
            messages.success(request, f"群組 {display_name} 新增成功！")
            logger.info(f"群組 {group.name} 由 {request.user.username} 新增")
            return redirect("system:group_list")
    else:
        form = GroupForm()
    return render(
        request, "system/group_form.html", {"form": form, "title": "新增群組"}
    )


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def group_edit(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.method == "POST":
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            group_name = group.name
            form.save()
            permissions = form.cleaned_data["permissions"]
            group.permissions.set(permissions)
            module_name = GROUP_TO_MODULE_MAP.get(
                group_name, group_name.replace("使用者", "").lower()
            )
            display_name = get_module_display_name(module_name)
            messages.success(request, f"群組 {display_name} 編輯成功！")
            logger.info(f"群組 {group_name} 由 {request.user.username} 編輯")
            return redirect("system:group_list")
    else:
        form = GroupForm(
            instance=group, initial={"permissions": group.permissions.all()}
        )
    return render(
        request, "system/group_form.html", {"form": form, "title": "編輯群組"}
    )


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def group_delete(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.method == "POST":
        group_name = group.name
        module_name = GROUP_TO_MODULE_MAP.get(
            group_name, group_name.replace("使用者", "").lower()
        )
        display_name = get_module_display_name(module_name)
        group.delete()
        messages.success(request, f"群組 {display_name} 刪除成功！")
        logger.info(f"群組 {group_name} 由 {request.user.username} 刪除")
        return redirect("system:group_list")
    return redirect("system:group_list")


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def email_config(request):
    email_config, created = EmailConfig.objects.get_or_create(id=1)
    if request.method == "POST":
        form = EmailConfigForm(request.POST)
        if "send_test_email" in request.POST:
            try:
                admin_user = User.objects.get(username="admin")
                logger.info(
                    f"準備發送測試郵件給 Admin 使用者: {admin_user.username}, 目標郵箱: {admin_user.email}"
                )
                if not admin_user.email:
                    logger.error("Admin 使用者未設置電子郵件地址")
                    messages.error(
                        request, "Admin 使用者未設置電子郵件地址，請先設置！"
                    )
                    return redirect("system:email_config")
                subject = "MES 系統 - 測試郵件"
                message = "這是一封來自 MES 系統的測試郵件。\n\n如果您收到此郵件，表示郵件主機設置正確。"
                from_email = email_config.default_from_email
                recipient_list = [admin_user.email]
                logger.info(
                    f"SMTP 配置: host={email_config.email_host}, port={email_config.email_port}, use_tls={email_config.email_use_tls}, user={email_config.email_host_user}, from_email={from_email}"
                )
                connection = get_connection(
                    backend="django.core.mail.backends.smtp.EmailBackend",
                    host=email_config.email_host,
                    port=email_config.email_port,
                    username=email_config.email_host_user,
                    password=email_config.email_host_password,
                    use_tls=email_config.email_use_tls,
                )
                send_mail(
                    subject,
                    message,
                    from_email,
                    recipient_list,
                    fail_silently=False,
                    connection=connection,
                )
                logger.info(f"測試郵件發送成功至: {admin_user.email}")
                messages.success(request, f"測試郵件已成功發送到 {admin_user.email}！")
            except User.DoesNotExist:
                logger.error("Admin 使用者不存在")
                messages.error(request, "Admin 使用者不存在，請確保已創建！")
            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"SMTP 認證失敗: {str(e)}")
                messages.error(
                    request,
                    f"SMTP 認證失敗，請檢查郵件主機 hesap戶或應用程式密碼：{str(e)}",
                )
            except smtplib.SMTPException as e:
                logger.error(f"SMTP 錯誤: {str(e)}")
                messages.error(request, f"發送測試郵件失敗（SMTP 錯誤）：{str(e)}")
            except Exception as e:
                logger.error(f"發送測試郵件失敗: {str(e)}")
                messages.error(request, f"發送測試郵件失敗：{str(e)}")
            return redirect("system:email_config")

        if form.is_valid():
            email_config.email_host = form.cleaned_data["email_host"]
            email_config.email_port = (
                form.cleaned_data["email_port"]
                if form.cleaned_data["email_port"]
                else 25
            )
            email_config.email_use_tls = form.cleaned_data["email_use_tls"]
            email_config.email_host_user = form.cleaned_data["email_host_user"]
            email_config.email_host_password = form.cleaned_data["email_host_password"]
            email_config.default_from_email = form.cleaned_data["default_from_email"]
            email_config.save()
            logger.info("郵件主機設定已更新")
            messages.success(request, "郵件主機設定已更新！")
            return redirect("system:index")
    else:
        initial_data = {
            "email_host": email_config.email_host,
            "email_port": email_config.email_port,
            "email_use_tls": email_config.email_use_tls,
            "email_host_user": email_config.email_host_user,
            "email_host_password": email_config.email_host_password,
            "default_from_email": email_config.default_from_email,
        }
        form = EmailConfigForm(initial=initial_data)
    return render(
        request, "system/email_config.html", {"form": form, "title": "郵件主機設定"}
    )


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def backup_database(request):
    backup_dir = "/var/www/mes/backups_DB"
    backup_files = []
    try:
        backup_files = [
            {
                "name": f,
                "size": os.path.getsize(os.path.join(backup_dir, f)) // 1024,
                "date": datetime.datetime.fromtimestamp(
                    os.path.getmtime(os.path.join(backup_dir, f))
                ).strftime("%Y-%m-%d %H:%M:%S"),
            }
            for f in os.listdir(backup_dir)
            if os.path.isfile(os.path.join(backup_dir, f)) and f.endswith(".sql")
        ]
        backup_files.sort(key=lambda x: x["date"], reverse=True)
    except Exception as e:
        logger.error(f"無法列出備份文件: {str(e)}")
        messages.error(request, f"無法列出備份文件：{str(e)}")

    if request.method == "POST":
        try:
            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                raise ValueError("環境變數 DATABASE_URL 未設置")
            from urllib.parse import urlparse

            parsed_url = urlparse(database_url)
            db_user = parsed_url.username
            db_password = parsed_url.password
            db_host = parsed_url.hostname
            db_port = parsed_url.port
            db_name = parsed_url.path.lstrip("/")
            os.environ["PGPASSWORD"] = db_password
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{db_name}_{timestamp}.sql"
            backup_path = os.path.join(backup_dir, backup_filename)
            cmd = [
                "pg_dump",
                "-h",
                db_host,
                "-p",
                str(db_port),
                "-U",
                db_user,
                "-F",
                "p",
                "-f",
                backup_path,
                db_name,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"pg_dump 失敗: {result.stderr}")
            del os.environ["PGPASSWORD"]
            logger.info(f"資料庫備份成功: {backup_filename}")
            messages.success(request, f"資料庫備份成功：{backup_filename}")
            backup_files = [
                {
                    "name": f,
                    "size": os.path.getsize(os.path.join(backup_dir, f)) // 1024,
                    "date": datetime.datetime.fromtimestamp(
                        os.path.getmtime(os.path.join(backup_dir, f))
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                }
                for f in os.listdir(backup_dir)
                if os.path.isfile(os.path.join(backup_dir, f)) and f.endswith(".sql")
            ]
            backup_files.sort(key=lambda x: x["date"], reverse=True)
        except Exception as e:
            logger.error(f"資料庫備份失敗: {str(e)}")
            messages.error(request, f"資料庫備份失敗：{str(e)}")
        return redirect("system:backup")
    return render(
        request,
        "system/backup.html",
        {"backup_files": backup_files, "title": "資料庫備份"},
    )


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def download_backup(request, filename):
    backup_dir = "/var/www/mes/backups_DB"
    file_path = os.path.join(backup_dir, filename)
    if not os.path.isfile(file_path) or not filename.endswith(".sql"):
        logger.error(f"備份文件不存在或格式錯誤: {filename}")
        messages.error(request, f"備份文件不存在或格式錯誤：{filename}")
        return redirect("system:backup")
    if not os.path.abspath(file_path).startswith(os.path.abspath(backup_dir)):
        logger.error(f"無權訪問文件: {filename}")
        messages.error(request, f"無權訪問文件：{filename}")
        return redirect("system:backup")
    try:
        response = FileResponse(
            open(file_path, "rb"), as_attachment=True, filename=filename
        )
        logger.info(f"備份文件下載成功: {filename}")
        return response
    except Exception as e:
        logger.error(f"備份文件下載失敗: {str(e)}")
        messages.error(request, f"備份文件下載失敗：{str(e)}")
        return redirect("system:backup")


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def restore_database(request):
    backup_dir = "/var/www/mes/backups_DB"
    
    # 獲取現有備份檔案列表
    try:
        backup_files = [
            {
                "name": f,
                "size": os.path.getsize(os.path.join(backup_dir, f)) // 1024,
                "date": datetime.datetime.fromtimestamp(
                    os.path.getmtime(os.path.join(backup_dir, f))
                ).strftime("%Y-%m-%d %H:%M:%S"),
            }
            for f in os.listdir(backup_dir)
            if os.path.isfile(os.path.join(backup_dir, f)) and f.endswith(".sql")
        ]
        backup_files.sort(key=lambda x: x["date"], reverse=True)
    except Exception as e:
        logger.error(f"無法列出備份文件：{str(e)}")
        backup_files = []
    
    if request.method == "POST":
        # 檢查是否有上傳檔案或選擇現有備份
        sql_file = request.FILES.get("sql_file")
        selected_backup = request.POST.get("selected_backup")
        
        if not sql_file and not selected_backup:
            logger.error("未上傳備份文件或選擇現有備份")
            messages.error(request, "請上傳一個備份文件或選擇現有備份！")
            return redirect("system:restore_database")
        
        # 確定要還原的檔案路徑
        if sql_file:
            if not sql_file.name.endswith(".sql"):
                logger.error(f"上傳文件格式錯誤: {sql_file.name}")
                messages.error(request, f"請上傳 .sql 格式的備份文件！")
                return redirect("system:restore_database")
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            upload_filename = f"restore_upload_{timestamp}_{sql_file.name}"
            upload_path = os.path.join(backup_dir, upload_filename)
            
            # 保存上傳的檔案
            with open(upload_path, "wb+") as destination:
                for chunk in sql_file.chunks():
                    destination.write(chunk)
        else:
            # 使用現有備份檔案
            upload_path = os.path.join(backup_dir, selected_backup)
            if not os.path.exists(upload_path):
                messages.error(request, f"選擇的備份檔案不存在：{selected_backup}")
                return redirect("system:restore_database")
        
        try:
            # 在開始資料庫還原前，先清除當前 session
            logger.info("清除當前 session...")
            try:
                request.session.flush()
            except Exception as session_error:
                logger.warning(f"清除 session 時出現警告: {str(session_error)}")
            
            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                raise ValueError("環境變數 DATABASE_URL 未設置")
            from urllib.parse import urlparse

            parsed_url = urlparse(database_url)
            db_user = parsed_url.username
            db_password = parsed_url.password
            db_host = parsed_url.hostname
            db_port = parsed_url.port
            db_name = parsed_url.path.lstrip("/")
            os.environ["PGPASSWORD"] = db_password
            
            # 步驟1: 先清空資料庫（斷開所有連線並重建）
            logger.info("開始清空資料庫...")
            drop_cmd = [
                "psql",
                "-h", db_host,
                "-p", str(db_port),
                "-U", db_user,
                "-d", "postgres",  # 連接到 postgres 資料庫
                "-c", f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}' AND pid <> pg_backend_pid();"
            ]
            result = subprocess.run(drop_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"斷開資料庫連線時出現警告: {result.stderr}")
            
            drop_db_cmd = [
                "dropdb",
                "-h", db_host,
                "-p", str(db_port),
                "-U", db_user,
                "--if-exists",
                db_name
            ]
            result = subprocess.run(drop_db_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"刪除資料庫時出現警告: {result.stderr}")
            
            # 步驟2: 重新建立資料庫
            logger.info("重新建立資料庫...")
            create_cmd = [
                "createdb",
                "-h", db_host,
                "-p", str(db_port),
                "-U", db_user,
                db_name
            ]
            result = subprocess.run(create_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"建立資料庫失敗: {result.stderr}")
            
            # 步驟3: 還原備份檔案
            logger.info("開始還原備份檔案...")
            restore_cmd = [
                "psql",
                "-h", db_host,
                "-p", str(db_port),
                "-U", db_user,
                "-d", db_name,
                "-f", upload_path,
            ]
            result = subprocess.run(restore_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"psql 恢復失敗: {result.stderr}")
            
            # 步驟4: 直接建立必要的資料表
            logger.info("建立必要的 Django 資料表...")
            
            # 建立 django_session 資料表
            session_table_sql = """
            CREATE TABLE IF NOT EXISTS django_session (
                session_key VARCHAR(40) NOT NULL PRIMARY KEY,
                session_data TEXT NOT NULL,
                expire_date TIMESTAMP WITH TIME ZONE NOT NULL
            );
            """
            
            # 建立 django_migrations 資料表
            migrations_table_sql = """
            CREATE TABLE IF NOT EXISTS django_migrations (
                id BIGSERIAL PRIMARY KEY,
                app VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                applied TIMESTAMP WITH TIME ZONE NOT NULL
            );
            """
            
            try:
                # 執行 SQL 建立資料表
                create_tables_cmd = [
                    "psql",
                    "-h", db_host,
                    "-p", str(db_port),
                    "-U", db_user,
                    "-d", db_name,
                    "-c", session_table_sql + migrations_table_sql
                ]
                result = subprocess.run(create_tables_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info("Django 必要資料表建立成功")
                else:
                    logger.warning(f"建立資料表時出現警告: {result.stderr}")
                    
            except Exception as e:
                logger.warning(f"建立 Django 資料表失敗: {str(e)}")
            
            del os.environ["PGPASSWORD"]
            backup_name = os.path.basename(upload_path)
            logger.info(f"資料庫恢復成功: {backup_name}")
            
            # 清理上傳的檔案
            if 'upload_path' in locals() and sql_file:
                try:
                    os.remove(upload_path)
                except:
                    pass
            
            # 重定向到登入頁面並顯示成功訊息
            return redirect(f"/accounts/login/?restore_success={backup_name}")
            
        except Exception as e:
            logger.error(f"資料庫恢復失敗: {str(e)}")
            
            # 清理上傳的檔案
            if 'upload_path' in locals() and sql_file:
                try:
                    os.remove(upload_path)
                except:
                    pass
            
            # 重定向到登入頁面並顯示錯誤訊息
            return redirect(f"/accounts/login/?restore_error={str(e)}")
    
    return render(request, "system/restore.html", {
        "title": "恢復資料庫",
        "backup_files": backup_files
    })


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def backup_schedule(request):
    schedule, created = BackupSchedule.objects.get_or_create(id=1)
    task_name = "auto-backup-database-task"
    if request.method == "POST":
        form = BackupScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            schedule = form.save()
            try:
                task = PeriodicTask.objects.get(name=task_name)
                if schedule.is_active:
                    backup_time = schedule.backup_time
                    schedule_obj, _ = CrontabSchedule.objects.get_or_create(
                        minute=backup_time.minute,
                        hour=backup_time.hour,
                        day_of_week="*",
                        day_of_month="*",
                        month_of_year="*",
                        timezone="Asia/Taipei",
                    )
                    task.crontab = schedule_obj
                    task.enabled = True
                    task.save()
                    logger.info("自動備份任務已更新並啟用")
                    messages.success(request, "自動備份排程已更新並啟用！")
                else:
                    task.enabled = False
                    task.save()
                    logger.info("自動備份任務已禁用")
                    messages.success(request, "自動備份排程已更新並禁用！")
            except PeriodicTask.DoesNotExist:
                if schedule.is_active:
                    backup_time = schedule.backup_time
                    schedule_obj, _ = CrontabSchedule.objects.get_or_create(
                        minute=backup_time.minute,
                        hour=backup_time.hour,
                        day_of_week="*",
                        day_of_month="*",
                        month_of_year="*",
                        timezone="Asia/Taipei",
                    )
                    PeriodicTask.objects.create(
                        crontab=schedule_obj,
                        name=task_name,
                        task="system.tasks.auto_backup_database",
                        enabled=True,
                    )
                    logger.info("自動備份任務已創建並啟用")
                    messages.success(request, "自動備份排程已創建並啟用！")
                else:
                    logger.info("自動備份排程已更新，但未啟用")
                    messages.success(request, "自動備份排程已更新，但未啟用！")
            return redirect("system:index")
    else:
        form = BackupScheduleForm(instance=schedule)
    try:
        task = PeriodicTask.objects.get(name=task_name)
        task_status = "已啟用" if task.enabled else "未啟用"
        task_time = schedule.backup_time.strftime("%H:%M") if task.enabled else None
    except PeriodicTask.DoesNotExist:
        task_status = "未啟用"
        task_time = None
    return render(
        request,
        "system/backup_schedule.html",
        {
            "form": form,
            "title": "自動備份排程",
            "task_status": task_status,
            "task_time": task_time,
        },
    )


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def export_users(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="users_export.csv"'
    response.write("\ufeff".encode("utf8"))
    writer = csv.writer(response)
    writer.writerow(["username", "email", "last_login"])
    users = User.objects.all()
    for user in users:
        writer.writerow(
            [
                user.username,
                user.email,
                (
                    user.last_login.strftime("%Y-%m-%d %H:%M:%S")
                    if user.last_login
                    else ""
                ),
            ]
        )
    logger.info(f"用戶數據匯出成功，由 {request.user.username} 執行")
    return response


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def import_users(request):
    if request.method == "POST":
        if "csv_file" not in request.FILES:
            logger.error("未上傳文件")
            messages.error(request, "請上傳一個文件！")
            return redirect("system:user_list")
        csv_file = request.FILES["csv_file"]
        if not (csv_file.name.endswith(".csv") or csv_file.name.endswith(".xlsx")):
            logger.error(f"上傳文件格式錯誤: {csv_file.name}")
            messages.error(request, "請上傳 .csv 或 .xlsx 格式的文件！")
            return redirect("system:user_list")
        try:
            created_count = 0
            updated_count = 0
            default_password = "123456"
            if csv_file.name.endswith(".csv"):
                decoded_file = csv_file.read().decode("utf-8-sig")
                csv_reader = csv.DictReader(decoded_file.splitlines())
                for row in csv_reader:
                    username = row.get("username")
                    email = row.get("email", "")
                    password = (
                        str(row.get("password", default_password))
                        if row.get("password") is not None
                        else default_password
                    )
                    if not username:
                        continue
                    user, created = User.objects.get_or_create(username=username)
                    user.email = email
                    if created or password != default_password:
                        user.set_password(password)
                    user.save()
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
            else:
                wb = openpyxl.load_workbook(csv_file)
                ws = wb.active
                headers = [cell.value for cell in ws[1]]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    row_data = dict(zip(headers, row))
                    username = row_data.get("username")
                    email = row_data.get("email", "")
                    password = (
                        str(row_data.get("password", default_password))
                        if row_data.get("password") is not None
                        else default_password
                    )
                    if not username:
                        continue
                    user, created = User.objects.get_or_create(username=username)
                    user.email = email
                    if created or password != default_password:
                        user.set_password(password)
                    user.save()
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
            logger.info(
                f"用戶匯入完成：新增 {created_count} 個，更新 {updated_count} 個"
            )
            messages.success(
                request,
                f"用戶匯入完成：新增 {created_count} 個，更新 {updated_count} 個",
            )
        except Exception as e:
            logger.error(f"用戶匯入失敗: {str(e)}")
            messages.error(request, f"用戶匯入失敗：{str(e)}")
        return redirect("system:user_list")
    return redirect("system:user_list")


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def operation_log_manage(request):
    config, created = OperationLogConfig.objects.get_or_create(id=1)
    if request.method == "POST":
        form = OperationLogConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            logger.info(f"操作紀錄保留天數更新為 {config.retain_days} 天")
            messages.success(
                request, f"操作紀錄保留天數已更新為 {config.retain_days} 天！"
            )
            return redirect("system:operation_log_manage")
    else:
        form = OperationLogConfigForm(instance=config)

    module = request.GET.get("module", "")
    user = request.GET.get("user", "")
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")

    logs = []
    for module_name, model_path in MODULE_LOG_MODELS.items():
        try:
            module_path, class_name = model_path.rsplit(".", 1)
            module = __import__(module_path, fromlist=[class_name])
            log_model = getattr(module, class_name)
            module_logs = log_model.objects.all()
            # 移除無效的 module 篩選條件
            if module_name and module_name != "":
                if module == module_name:
                    continue  # 跳過不符合模組條件的記錄
            if user:
                module_logs = module_logs.filter(user=user)
            if start_date:
                start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                module_logs = module_logs.filter(timestamp__gte=start_date)
            if end_date:
                end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
                end_date = end_date + datetime.timedelta(days=1)  # 包含結束日期當天
                module_logs = module_logs.filter(timestamp__lt=end_date)
            # 添加模組名稱到日誌記錄
            for log in module_logs:
                logs.append(
                    {
                        "module": module_name,
                        "display_module": get_module_display_name(module_name),
                        "timestamp": log.timestamp,
                        "user": log.user,
                        "action": log.action,
                    }
                )
        except ImportError as e:
            logger.error(
                f"無法導入模組 {module_name} 的日誌模型 {model_path}: {str(e)}"
            )
            messages.error(request, f"無法加載模組 {module_name} 的操作紀錄：{str(e)}")
        except AttributeError as e:
            logger.error(f"模組 {module_name} 的日誌模型 {model_path} 無效: {str(e)}")
            messages.error(request, f"模組 {module_name} 的日誌模型無效：{str(e)}")
        except Exception as e:
            logger.error(f"加載模組 {module_name} 的操作紀錄時發生未知錯誤: {str(e)}")
            messages.error(request, f"加載模組 {module_name} 的操作紀錄失敗：{str(e)}")
    # 按時間倒序排序
    logs.sort(key=lambda x: x["timestamp"], reverse=True)

    # 獲取模組選項和使用者列表
    modules = list(MODULE_LOG_MODELS.keys())
    module_choices = [(m, get_module_display_name(m)) for m in modules]
    users = set()
    for module_name, model_path in MODULE_LOG_MODELS.items():
        try:
            module_path, class_name = model_path.rsplit(".", 1)
            module = __import__(module_path, fromlist=[class_name])
            log_model = getattr(module, class_name)
            users.update(log_model.objects.values_list("user", flat=True))
        except Exception as e:
            logger.error(f"無法從模組 {module_name} 獲取使用者列表: {str(e)}")

    default_end_date = timezone.now().date()
    default_start_date = default_end_date - datetime.timedelta(days=30)

    return render(
        request,
        "system/operation_log_manage.html",
        {
            "form": form,
            "logs": logs,
            "module_choices": module_choices,
            "users": users,
            "selected_module": module,
            "selected_user": user,
            "start_date": start_date,
            "end_date": end_date,
            "default_start_date": default_start_date,
            "default_end_date": default_end_date,
            "title": "操作紀錄管理",
        },
    )


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def clean_operation_logs(request):
    config, created = OperationLogConfig.objects.get_or_create(id=1)
    cutoff_date = timezone.now() - datetime.timedelta(days=config.retain_days)
    total_deleted = 0
    for module, model_path in MODULE_LOG_MODELS.items():
        try:
            module_name, class_name = model_path.rsplit(".", 1)
            module = __import__(module_name, fromlist=[class_name])
            log_model = getattr(module, class_name)
            deleted_count, _ = log_model.objects.filter(
                timestamp__lt=cutoff_date
            ).delete()
            total_deleted += deleted_count
            logger.info(
                f"清理模組 {module} 的過期操作紀錄，刪除 {deleted_count} 條記錄"
            )
        except Exception as e:
            logger.error(f"清理模組 {module} 的操作紀錄失敗: {str(e)}")
    logger.info(f"清理過期操作紀錄，刪除 {total_deleted} 條記錄")
    messages.success(request, f"已清理 {total_deleted} 條過期操作紀錄！")
    return redirect("system:operation_log_manage")


@login_required
def change_password(request):
    if request.method == "POST":
        form = SetPasswordForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "您的密碼已成功更改！請重新登入。")
            logger.info(f"用戶 {request.user.username} 更改了自己的密碼")
            return redirect("login")
        else:
            messages.error(request, "請修正以下錯誤：")
    else:
        form = SetPasswordForm(user=request.user)
    return render(
        request, "system/change_password.html", {"form": form, "title": "變更密碼"}
    )


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def environment_management(request):
    """環境管理視圖"""
    # 獲取當前環境信息
    current_env = os.environ.get("DJANGO_ENV", "development")
    current_debug = getattr(settings, "DEBUG", True)

    # 環境配置信息
    environments = {
        "development": {
            "name": "開發環境",
            "description": "用於程式開發和調試，記錄詳細的 DEBUG 日誌",
            "debug": True,
            "log_level": "DEBUG",
            "features": ["詳細調試信息", "終端日誌輸出", "完整錯誤追蹤"],
        },
        "testing": {
            "name": "測試環境",
            "description": "用於功能測試和驗證，記錄 INFO 級別日誌",
            "debug": False,
            "log_level": "INFO",
            "features": ["功能測試", "中等詳細日誌", "效能測試"],
        },
        "production": {
            "name": "生產環境",
            "description": "正式營運環境，只記錄重要日誌，支援郵件通知",
            "debug": False,
            "log_level": "WARNING",
            "features": ["高安全性", "自動日誌輪轉", "錯誤郵件通知", "效能優化"],
        },
    }

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "switch_environment":
            target_env = request.POST.get("environment")

            if target_env in environments:
                try:
                    # 備份現有的 .env 檔案
                    if os.path.exists(".env"):
                        backup_name = (
                            f'.env.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}'
                        )
                        shutil.copy2(".env", backup_name)
                        messages.success(request, f"已備份現有環境設定到 {backup_name}")

                    # 複製目標環境檔案
                    env_file = f"env_{target_env}.txt"
                    if os.path.exists(env_file):
                        shutil.copy2(env_file, ".env")
                        messages.success(
                            request, f'已切換到 {environments[target_env]["name"]}'
                        )

                        # 記錄操作日誌
                        logger.info(
                            f"系統管理員 {request.user.username} 將環境從 {current_env} 切換到 {target_env}"
                        )

                        # 提示重啟服務
                        messages.warning(
                            request, "請重啟 Django 服務以套用新的環境設定"
                        )
                    else:
                        messages.error(request, f"環境檔案 {env_file} 不存在")

                except Exception as e:
                    messages.error(request, f"環境切換失敗: {str(e)}")
                    logger.error(f"環境切換失敗: {str(e)}")
            else:
                messages.error(request, "無效的環境名稱")

    # 獲取日誌檔案信息
    log_dir = getattr(
        settings, "LOG_DIR", os.path.join(os.path.dirname(settings.BASE_DIR), "logs")
    )
    log_files = []

    if os.path.exists(log_dir):
        for file in os.listdir(log_dir):
            if file.endswith(".log"):
                file_path = os.path.join(log_dir, file)
                stat = os.stat(file_path)
                log_files.append(
                    {
                        "name": file,
                        "size": stat.st_size,
                        "modified": datetime.datetime.fromtimestamp(stat.st_mtime),
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    }
                )

    context = {
        "current_env": current_env,
        "current_debug": current_debug,
        "environments": environments,
        "log_files": log_files,
        "log_dir": log_dir,
    }

    return render(request, "system/environment_management.html", context)


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def view_log_file(request, filename):
    """查看日誌檔案"""
    import os
    from django.conf import settings
    from django.http import HttpResponse

    log_dir = getattr(
        settings, "LOG_DIR", os.path.join(os.path.dirname(settings.BASE_DIR), "logs")
    )
    file_path = os.path.join(log_dir, filename)

    if not os.path.exists(file_path):
        messages.error(request, f"日誌檔案 {filename} 不存在")
        return redirect("system:environment_management")

    # 檢查檔案大小，如果太大只顯示最後部分
    file_size = os.path.getsize(file_path)
    max_size = 1024 * 1024  # 1MB

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if file_size > max_size:
                # 檔案太大，只讀取最後部分
                f.seek(-max_size, 2)
                content = f.read()
                content = f"... (檔案太大，只顯示最後 {max_size//1024}KB)\n" + content
            else:
                content = f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, "r", encoding="big5") as f:
                if file_size > max_size:
                    f.seek(-max_size, 2)
                    content = f.read()
                    content = (
                        f"... (檔案太大，只顯示最後 {max_size//1024}KB)\n" + content
                    )
                else:
                    content = f.read()
        except:
            content = "無法讀取檔案內容"

    context = {
        "filename": filename,
        "content": content,
        "file_size": file_size,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
    }

    return render(request, "system/view_log.html", context)


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def download_log_file(request, filename):
    """下載日誌檔案"""
    import os
    from django.conf import settings
    from django.http import FileResponse

    log_dir = getattr(
        settings, "LOG_DIR", os.path.join(os.path.dirname(settings.BASE_DIR), "logs")
    )
    file_path = os.path.join(log_dir, filename)

    if not os.path.exists(file_path):
        messages.error(request, f"日誌檔案 {filename} 不存在")
        return redirect("system:environment_management")

    try:
        response = FileResponse(open(file_path, "rb"))
        response["Content-Type"] = "text/plain"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        messages.error(request, f"下載失敗: {str(e)}")
        return redirect("system:environment_management")


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def clean_logs(request):
    """清理日誌檔案"""
    if request.method == "POST":
        days = int(request.POST.get("days", 30))
        dry_run = request.POST.get("dry_run") == "on"

        log_dir = getattr(
            settings,
            "LOG_DIR",
            os.path.join(os.path.dirname(settings.BASE_DIR), "logs"),
        )

        if not os.path.exists(log_dir):
            messages.error(request, "日誌目錄不存在")
            return redirect("system:environment_management")

        cutoff_date = datetime.now() - timedelta(days=days)
        log_files = glob.glob(os.path.join(log_dir, "*.log*"))

        deleted_count = 0
        deleted_size = 0

        for log_file in log_files:
            stat = os.stat(log_file)
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime)

            if mtime < cutoff_date:
                if dry_run:
                    messages.info(
                        request,
                        f'將刪除: {os.path.basename(log_file)} ({mtime.strftime("%Y-%m-%d")})',
                    )
                else:
                    try:
                        size = os.path.getsize(log_file)
                        os.remove(log_file)
                        deleted_count += 1
                        deleted_size += size
                        messages.success(
                            request, f"已刪除: {os.path.basename(log_file)}"
                        )
                    except Exception as e:
                        messages.error(
                            request,
                            f"刪除失敗: {os.path.basename(log_file)} - {str(e)}",
                        )

        if dry_run:
            messages.info(
                request,
                f"模擬完成，將刪除 {len([f for f in log_files if datetime.datetime.fromtimestamp(os.stat(f).st_mtime) < cutoff_date])} 個檔案",
            )
        else:
            messages.success(
                request,
                f"清理完成，刪除了 {deleted_count} 個檔案，釋放 {deleted_size / (1024*1024):.1f} MB 空間",
            )
            logger.info(
                f"系統管理員 {request.user.username} 清理了 {deleted_count} 個日誌檔案"
            )

    return redirect("system:environment_management")


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def permission_list(request):
    """權限管理列表頁面"""
    # 取得所有模組的權限
    all_modules = [
        "equip",
        "material",
        "scheduling",
        "process",
        "quality",
        "workorder",

        "kanban",
        "erp_integration",
        "ai",
    ]

    # 按模組分組權限
    permissions_by_module = {}
    for module in all_modules:
        module_permissions = Permission.objects.filter(content_type__app_label=module)
        if module_permissions.exists():
            display_name = get_module_display_name(module)
            permissions_by_module[display_name] = []
            for perm in module_permissions:
                # 翻譯權限名稱
                translated_name = PERMISSION_NAME_TRANSLATIONS.get(perm.name, perm.name)
                permissions_by_module[display_name].append(
                    {
                        "id": perm.id,
                        "name": translated_name,
                        "codename": perm.codename,
                        "content_type": perm.content_type.model,
                        "app_label": perm.content_type.app_label,
                    }
                )

    return render(
        request,
        "system/permission_list.html",
        {"permissions_by_module": permissions_by_module},
    )


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def permission_detail(request, permission_id):
    """權限詳情頁面"""
    permission = get_object_or_404(Permission, id=permission_id)

    # 取得擁有此權限的群組
    groups_with_permission = Group.objects.filter(permissions=permission)

    # 取得擁有此權限的用戶
    users_with_permission = User.objects.filter(
        Q(user_permissions=permission) | Q(groups__permissions=permission)
    ).distinct()

    # 翻譯權限名稱
    translated_name = PERMISSION_NAME_TRANSLATIONS.get(permission.name, permission.name)

    return render(
        request,
        "system/permission_detail.html",
        {
            "permission": permission,
            "translated_name": translated_name,
            "groups_with_permission": groups_with_permission,
            "users_with_permission": users_with_permission,
        },
    )


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def permission_assign(request):
    """權限分配頁面"""
    if request.method == "POST":
        permission_id = request.POST.get("permission_id")
        group_id = request.POST.get("group_id")
        user_id = request.POST.get("user_id")
        action = request.POST.get("action")  # 'assign' 或 'remove'

        try:
            permission = Permission.objects.get(id=permission_id)
            translated_name = PERMISSION_NAME_TRANSLATIONS.get(
                permission.name, permission.name
            )

            if group_id:
                group = Group.objects.get(id=group_id)
                if action == "assign":
                    group.permissions.add(permission)
                    messages.success(
                        request,
                        f"已將權限「{translated_name}」分配給群組「{group.name}」",
                    )
                    logger.info(
                        f"權限 {permission.name} 分配給群組 {group.name} 由 {request.user.username} 操作"
                    )
                else:
                    group.permissions.remove(permission)
                    messages.success(
                        request,
                        f"已從群組「{group.name}」移除權限「{translated_name}」",
                    )
                    logger.info(
                        f"權限 {permission.name} 從群組 {group.name} 移除由 {request.user.username} 操作"
                    )

            elif user_id:
                user = User.objects.get(id=user_id)
                if action == "assign":
                    user.user_permissions.add(permission)
                    messages.success(
                        request,
                        f"已將權限「{translated_name}」分配給用戶「{user.username}」",
                    )
                    logger.info(
                        f"權限 {permission.name} 分配給用戶 {user.username} 由 {request.user.username} 操作"
                    )
                else:
                    user.user_permissions.remove(permission)
                    messages.success(
                        request,
                        f"已從用戶「{user.username}」移除權限「{translated_name}」",
                    )
                    logger.info(
                        f"權限 {permission.name} 從用戶 {user.username} 移除由 {request.user.username} 操作"
                    )

        except (Permission.DoesNotExist, Group.DoesNotExist, User.DoesNotExist):
            messages.error(request, "指定的權限、群組或用戶不存在")
        except Exception as e:
            messages.error(request, f"操作失敗：{str(e)}")

    # 取得所有權限、群組和用戶供選擇
    all_permissions = get_all_permissions()
    groups = Group.objects.all()
    users = User.objects.filter(is_active=True)

    # 為權限名稱添加翻譯
    for perm in all_permissions:
        perm.translated_name = PERMISSION_NAME_TRANSLATIONS.get(perm.name, perm.name)

    return render(
        request,
        "system/permission_assign.html",
        {"permissions": all_permissions, "groups": groups, "users": users},
    )


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def user_work_permission_list(request):
    """
    使用者工作權限列表
    """
    permissions = UserWorkPermission.objects.select_related('user').order_by('user__username', 'permission_type')
    
    context = {
        'permissions': permissions,
        'page_title': '使用者工作權限管理',
    }
    
    return render(request, 'system/user_work_permission_list.html', context)


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def user_work_permission_add(request):
    """
    新增使用者工作權限
    """
    if request.method == 'POST':
        form = UserWorkPermissionForm(request.POST)
        if form.is_valid():
            permission = form.save(commit=False)
            permission.created_by = request.user
            permission.save()
            messages.success(request, f'使用者 {permission.user.username} 的工作權限設定已成功建立！')
            return redirect('system:user_work_permission_list')
    else:
        form = UserWorkPermissionForm()
    
    context = {
        'form': form,
        'page_title': '新增使用者工作權限',
        'is_add': True,
    }
    
    return render(request, 'system/user_work_permission_form.html', context)


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def user_work_permission_edit(request, permission_id):
    """
    編輯使用者工作權限
    """
    permission = get_object_or_404(UserWorkPermission, id=permission_id)
    
    if request.method == 'POST':
        form = UserWorkPermissionForm(request.POST, instance=permission)
        if form.is_valid():
            form.save()
            messages.success(request, f'使用者 {permission.user.username} 的工作權限設定已成功更新！')
            return redirect('system:user_work_permission_list')
    else:
        form = UserWorkPermissionForm(instance=permission)
    
    context = {
        'form': form,
        'permission': permission,
        'page_title': '編輯使用者工作權限',
        'is_edit': True,
    }
    
    return render(request, 'system/user_work_permission_form.html', context)


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def user_work_permission_delete(request, permission_id):
    """
    刪除使用者工作權限
    """
    permission = get_object_or_404(UserWorkPermission, id=permission_id)
    
    if request.method == 'POST':
        username = permission.user.username
        permission.delete()
        messages.success(request, f'使用者 {username} 的工作權限設定已成功刪除！')
        return redirect('system:user_work_permission_list')
    
    context = {
        'permission': permission,
        'page_title': '刪除使用者工作權限',
    }
    
    return render(request, 'system/user_work_permission_confirm_delete.html', context)


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def user_work_permission_detail(request, permission_id):
    """
    查看使用者工作權限詳情
    """
    permission = get_object_or_404(UserWorkPermission, id=permission_id)
    
    context = {
        'permission': permission,
        'page_title': '使用者工作權限詳情',
    }
    
    return render(request, 'system/user_work_permission_detail.html', context)


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def workorder_settings(request):
    """
    工單管理設定頁面
    管理工單系統相關設定，包含審核流程、定時任務和完工判斷等
    """
    from workorder.models import SystemConfig
    
    if request.method == "POST":
        # 處理表單提交
        auto_approval = request.POST.get('auto_approval') == 'on'
        notification_enabled = request.POST.get('notification_enabled') == 'on'
        audit_log_enabled = request.POST.get('audit_log_enabled') == 'on'
        max_file_size = request.POST.get('max_file_size', 10)
        session_timeout = request.POST.get('session_timeout', 30)
        
        # 自動審核設定
        auto_approve_work_hours = request.POST.get('auto_approve_work_hours') == 'on'
        max_work_hours = request.POST.get('max_work_hours', 12.0)
        auto_approve_defect_rate = request.POST.get('auto_approve_defect_rate') == 'on'
        max_defect_rate = request.POST.get('max_defect_rate', 5.0)
        auto_approve_overtime = request.POST.get('auto_approve_overtime') == 'on'
        max_overtime_hours = request.POST.get('max_overtime_hours', 4.0)
        exclude_operators = request.POST.get('exclude_operators', '')
        exclude_processes = request.POST.get('exclude_processes', '')
        auto_approval_notification_enabled = request.POST.get('auto_approval_notification_enabled') == 'on'
        auto_approval_notification_recipients = request.POST.get('auto_approval_notification_recipients', '')
        
        # 定時任務設定
        auto_allocation_enabled = request.POST.get('auto_allocation_enabled') == 'on'
        auto_allocation_interval = int(request.POST.get('auto_allocation_interval', 30))
        
        # 處理多個自動審核定時任務
        from system.models import ScheduledTask
        
        # 取得所有自動審核定時任務
        auto_approval_tasks = ScheduledTask.objects.filter(task_type='auto_approve')
        
        # 處理每個任務的更新
        for task in auto_approval_tasks:
            task_name = request.POST.get(f'task_name_{task.id}')
            task_interval = request.POST.get(f'task_interval_{task.id}')
            task_enabled = request.POST.get(f'task_enabled_{task.id}') == 'on'
            
            if task_name and task_interval:
                task.name = task_name
                task.interval_minutes = int(task_interval)
                task.is_enabled = task_enabled
                task.save()
        
        # 完工判斷設定
        completion_check_enabled = request.POST.get('completion_check_enabled') == 'on'
        completion_check_interval = int(request.POST.get('completion_check_interval', 30))
        packaging_process_name = request.POST.get('packaging_process_name', '出貨包裝')
        data_transfer_enabled = request.POST.get('data_transfer_enabled') == 'on'
        transfer_batch_size = int(request.POST.get('transfer_batch_size', 50))
        transfer_retention_days = int(request.POST.get('transfer_retention_days', 365))
        
        # 更新系統設定
        SystemConfig.objects.update_or_create(
            key="auto_approval",
            defaults={"value": str(auto_approval)}
        )
        SystemConfig.objects.update_or_create(
            key="notification_enabled",
            defaults={"value": str(notification_enabled)}
        )
        SystemConfig.objects.update_or_create(
            key="audit_log_enabled",
            defaults={"value": str(audit_log_enabled)}
        )
        SystemConfig.objects.update_or_create(
            key="max_file_size",
            defaults={"value": str(max_file_size)}
        )
        SystemConfig.objects.update_or_create(
            key="session_timeout",
            defaults={"value": str(session_timeout)}
        )
        
        # 儲存自動審核設定
        SystemConfig.objects.update_or_create(
            key="auto_approve_work_hours",
            defaults={"value": str(auto_approve_work_hours)}
        )
        SystemConfig.objects.update_or_create(
            key="max_work_hours",
            defaults={"value": str(max_work_hours)}
        )
        SystemConfig.objects.update_or_create(
            key="auto_approve_defect_rate",
            defaults={"value": str(auto_approve_defect_rate)}
        )
        SystemConfig.objects.update_or_create(
            key="max_defect_rate",
            defaults={"value": str(max_defect_rate)}
        )
        SystemConfig.objects.update_or_create(
            key="auto_approve_overtime",
            defaults={"value": str(auto_approve_overtime)}
        )
        SystemConfig.objects.update_or_create(
            key="max_overtime_hours",
            defaults={"value": str(max_overtime_hours)}
        )
        SystemConfig.objects.update_or_create(
            key="exclude_operators",
            defaults={"value": exclude_operators}
        )
        SystemConfig.objects.update_or_create(
            key="exclude_processes",
            defaults={"value": exclude_processes}
        )
        SystemConfig.objects.update_or_create(
            key="auto_approval_notification_enabled",
            defaults={"value": str(auto_approval_notification_enabled)}
        )
        SystemConfig.objects.update_or_create(
            key="auto_approval_notification_recipients",
            defaults={"value": auto_approval_notification_recipients}
        )
        
        # 更新完工判斷設定
        SystemConfig.objects.update_or_create(
            key="completion_check_enabled",
            defaults={"value": str(completion_check_enabled)}
        )
        SystemConfig.objects.update_or_create(
            key="completion_check_interval",
            defaults={"value": str(completion_check_interval)}
        )
        SystemConfig.objects.update_or_create(
            key="packaging_process_name",
            defaults={"value": packaging_process_name}
        )
        SystemConfig.objects.update_or_create(
            key="data_transfer_enabled",
            defaults={"value": str(data_transfer_enabled)}
        )
        SystemConfig.objects.update_or_create(
            key="transfer_batch_size",
            defaults={"value": str(transfer_batch_size)}
        )
        SystemConfig.objects.update_or_create(
            key="transfer_retention_days",
            defaults={"value": str(transfer_retention_days)}
        )
        
        # 更新定時任務設定
        try:
            # 自動分配定時任務
            auto_allocation_task = PeriodicTask.objects.get(name='自動分配任務')
            auto_allocation_task.enabled = auto_allocation_enabled
            if auto_allocation_interval != auto_allocation_task.interval.every:
                interval_schedule, _ = IntervalSchedule.objects.get_or_create(
                    every=auto_allocation_interval,
                    period=IntervalSchedule.MINUTES,
                )
                auto_allocation_task.interval = interval_schedule
            auto_allocation_task.save()
            
            # 自動審核定時任務
            auto_approval_task = PeriodicTask.objects.get(name='auto_approve_work_reports')
            auto_approval_task.enabled = auto_approval_task_enabled
            if auto_approval_task_interval != auto_approval_task.interval.every:
                interval_schedule, _ = IntervalSchedule.objects.get_or_create(
                    every=auto_approval_task_interval,
                    period=IntervalSchedule.MINUTES,
                )
                auto_approval_task.interval = interval_schedule
            auto_approval_task.save()
            
        except PeriodicTask.DoesNotExist as e:
            messages.warning(request, f"部分定時任務未找到：{str(e)}")
        
        messages.success(request, "工單管理設定已成功更新！")
        return redirect('system:workorder_settings')
    
    # 取得現有設定
    try:
        auto_approval = SystemConfig.objects.get(key="auto_approval").value == "True"
    except SystemConfig.DoesNotExist:
        auto_approval = False
        
    try:
        notification_enabled = SystemConfig.objects.get(key="notification_enabled").value == "True"
    except SystemConfig.DoesNotExist:
        notification_enabled = True
        
    try:
        audit_log_enabled = SystemConfig.objects.get(key="audit_log_enabled").value == "True"
    except SystemConfig.DoesNotExist:
        audit_log_enabled = True
        
    try:
        max_file_size = int(SystemConfig.objects.get(key="max_file_size").value)
    except (SystemConfig.DoesNotExist, ValueError):
        max_file_size = 10
        
    try:
        session_timeout = int(SystemConfig.objects.get(key="session_timeout").value)
    except (SystemConfig.DoesNotExist, ValueError):
        session_timeout = 30
    
    # 取得自動審核設定
    try:
        auto_approve_work_hours = SystemConfig.objects.get(key="auto_approve_work_hours").value == "True"
    except SystemConfig.DoesNotExist:
        auto_approve_work_hours = True
        
    try:
        max_work_hours = float(SystemConfig.objects.get(key="max_work_hours").value)
    except (SystemConfig.DoesNotExist, ValueError):
        max_work_hours = 12.0
        
    try:
        auto_approve_defect_rate = SystemConfig.objects.get(key="auto_approve_defect_rate").value == "True"
    except SystemConfig.DoesNotExist:
        auto_approve_defect_rate = True
        
    try:
        max_defect_rate = float(SystemConfig.objects.get(key="max_defect_rate").value)
    except (SystemConfig.DoesNotExist, ValueError):
        max_defect_rate = 5.0
        
    try:
        auto_approve_overtime = SystemConfig.objects.get(key="auto_approve_overtime").value == "True"
    except SystemConfig.DoesNotExist:
        auto_approve_overtime = False
        
    try:
        max_overtime_hours = float(SystemConfig.objects.get(key="max_overtime_hours").value)
    except (SystemConfig.DoesNotExist, ValueError):
        max_overtime_hours = 4.0
        
    try:
        exclude_operators_text = SystemConfig.objects.get(key="exclude_operators").value
    except SystemConfig.DoesNotExist:
        exclude_operators_text = ""
        
    try:
        exclude_processes_text = SystemConfig.objects.get(key="exclude_processes").value
    except SystemConfig.DoesNotExist:
        exclude_processes_text = ""
        
    try:
        auto_approval_notification_enabled = SystemConfig.objects.get(key="auto_approval_notification_enabled").value == "True"
    except SystemConfig.DoesNotExist:
        auto_approval_notification_enabled = True
        
    try:
        auto_approval_notification_recipients_text = SystemConfig.objects.get(key="auto_approval_notification_recipients").value
    except SystemConfig.DoesNotExist:
        auto_approval_notification_recipients_text = ""
    
    # 取得完工判斷設定
    try:
        completion_check_enabled = SystemConfig.objects.get(key="completion_check_enabled").value == "True"
    except SystemConfig.DoesNotExist:
        completion_check_enabled = True
        
    try:
        completion_check_interval = int(SystemConfig.objects.get(key="completion_check_interval").value)
    except (SystemConfig.DoesNotExist, ValueError):
        completion_check_interval = 30
        
    try:
        packaging_process_name = SystemConfig.objects.get(key="packaging_process_name").value
    except SystemConfig.DoesNotExist:
        packaging_process_name = "出貨包裝"
        
    try:
        data_transfer_enabled = SystemConfig.objects.get(key="data_transfer_enabled").value == "True"
    except SystemConfig.DoesNotExist:
        data_transfer_enabled = True
        
    try:
        transfer_batch_size = int(SystemConfig.objects.get(key="transfer_batch_size").value)
    except (SystemConfig.DoesNotExist, ValueError):
        transfer_batch_size = 50
        
    try:
        transfer_retention_days = int(SystemConfig.objects.get(key="transfer_retention_days").value)
    except (SystemConfig.DoesNotExist, ValueError):
        transfer_retention_days = 365
    
    # 取得定時任務狀態
    try:
        auto_allocation_task = PeriodicTask.objects.get(name='自動分配任務')
        auto_allocation_task.interval_minutes = auto_allocation_task.interval.every
    except PeriodicTask.DoesNotExist:
        auto_allocation_task = type('obj', (object,), {
            'enabled': False,
            'interval_minutes': 30,
            'last_run': None
        })
    
    # 取得自動審核定時任務（使用 ScheduledTask 模型）
    from system.models import ScheduledTask
    auto_approval_tasks = ScheduledTask.objects.filter(task_type='auto_approve').order_by('created_at')
    
    # 如果沒有自動審核定時任務，建立一個預設的
    if not auto_approval_tasks.exists():
        default_task = ScheduledTask.objects.create(
            name='預設自動審核',
            task_type='auto_approve',
            task_function='system.tasks.auto_approve_work_reports',
            interval_minutes=30,
            is_enabled=True,
            description='預設的自動審核定時任務'
        )
        auto_approval_tasks = ScheduledTask.objects.filter(task_type='auto_approve').order_by('created_at')
    
    context = {
        'auto_approval': auto_approval,
        'notification_enabled': notification_enabled,
        'audit_log_enabled': audit_log_enabled,
        'max_file_size': max_file_size,
        'session_timeout': session_timeout,
        'auto_allocation_task': auto_allocation_task,
        'auto_approval_tasks': auto_approval_tasks,
        'completion_check_enabled': completion_check_enabled,
        'completion_check_interval': completion_check_interval,
        'packaging_process_name': packaging_process_name,
        'data_transfer_enabled': data_transfer_enabled,
        'transfer_batch_size': transfer_batch_size,
        'transfer_retention_days': transfer_retention_days,
        # 自動審核設定
        'auto_approve_work_hours': auto_approve_work_hours,
        'max_work_hours': max_work_hours,
        'auto_approve_defect_rate': auto_approve_defect_rate,
        'max_defect_rate': max_defect_rate,
        'auto_approve_overtime': auto_approve_overtime,
        'max_overtime_hours': max_overtime_hours,
        'exclude_operators_text': exclude_operators_text,
        'exclude_processes_text': exclude_processes_text,
        'auto_approval_notification_enabled': auto_approval_notification_enabled,
        'auto_approval_notification_recipients_text': auto_approval_notification_recipients_text,
    }
    
    return render(request, 'system/workorder_settings.html', context)


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def execute_auto_approval(request):
    """
    手動執行自動審核 API
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支援 POST 請求'})
    
    try:
        from system.tasks import auto_approve_work_reports
        
        result = auto_approve_work_reports()
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': f"自動審核執行完成：{result['message']}"
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f"自動審核執行失敗：{result.get('error', '未知錯誤')}"
            })
            
    except Exception as e:
        logger.error(f"手動執行自動審核失敗: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f"執行失敗：{str(e)}"
        })


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def execute_auto_allocation(request):
    """
    手動執行自動分配 API
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支援 POST 請求'})
    
    try:
        from workorder.services.auto_allocation_service import AutoAllocationService
        
        service = AutoAllocationService()
        result = service.allocate_all_pending_workorders()
        
        if result.get('success', False):
            message = f"自動分配完成！處理 {result.get('total_allocated_workorders', 0)} 個工單，分配 {result.get('total_allocated_quantity', 0)} 件給 {result.get('total_allocated_reports', 0)} 筆紀錄"
            
            return JsonResponse({
                'success': True,
                'message': message
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result.get('message', '未知錯誤')
            })
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"手動執行自動分配失敗: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'執行失敗: {str(e)}'
        })


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def execute_completion_check(request):
    """
    手動執行完工檢查 API
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支援 POST 請求'})
    
    try:
        from workorder.services.completion_service import FillWorkCompletionService
        
        result = FillWorkCompletionService.check_all_workorders_completion()
        
        if 'error' not in result:
            return JsonResponse({
                'success': True,
                'message': f"完工檢查完成！{result.get('message', '檢查完成')}"
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result['error']
            })
            
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        error_details = traceback.format_exc()
        logger.error(f"手動執行完工檢查失敗: {str(e)}\n詳細錯誤:\n{error_details}")
        return JsonResponse({
            'success': False,
            'message': f'執行失敗: {str(e)}'
        })


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def execute_data_transfer(request):
    """
    手動執行資料轉移 API
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支援 POST 請求'})
    
    try:
        from workorder.services.completion_service import FillWorkCompletionService
        
        # 執行資料轉移
        result = FillWorkCompletionService.transfer_completed_workorders()
        
        if 'error' not in result:
            return JsonResponse({
                'success': True,
                'message': f"資料轉移完成！{result.get('message', '轉移完成')}"
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result['error']
            })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"手動執行資料轉移失敗: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'執行失敗: {str(e)}'
        })


# 完工判斷功能已整合到現有的 FillWorkCompletionService 中
# 手動執行功能可以通過現有的管理命令實現


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def enable_auto_completion(request):
    """
    啟用自動完工功能 API
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支援 POST 請求'})
    
    try:
        from workorder.services.completion_service import FillWorkCompletionService
        
        # 啟用自動完工功能
        success = FillWorkCompletionService.enable_auto_completion()
        
        if success:
            return JsonResponse({
                'success': True,
                'message': '自動完工功能已啟用！填報記錄提交時會自動檢查完工條件'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '啟用自動完工功能失敗'
            })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"啟用自動完工功能失敗: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'啟用失敗: {str(e)}'
        })


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def disable_auto_completion(request):
    """
    停用自動完工功能 API
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支援 POST 請求'})
    
    try:
        from workorder.services.completion_service import FillWorkCompletionService
        
        # 停用自動完工功能
        success = FillWorkCompletionService.disable_auto_completion()
        
        if success:
            return JsonResponse({
                'success': True,
                'message': '自動完工功能已停用'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '停用自動完工功能失敗'
            })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"停用自動完工功能失敗: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'停用失敗: {str(e)}'
        })


@login_required
def auto_approval_settings(request):
    """自動審核設定"""
    # 取得或建立自動審核設定
    settings, created = AutoApprovalSettings.objects.get_or_create(
        id=1,
        defaults={
            'is_enabled': False,
            'auto_approve_work_hours': True,
            'max_work_hours': 12.0,
            'auto_approve_defect_rate': True,
            'max_defect_rate': 5.0,
            'auto_approve_overtime': False,
            'max_overtime_hours': 4.0,
            'exclude_operators': [],
            'exclude_processes': [],
            'notification_enabled': True,
            'notification_recipients': []
        }
    )
    
    if request.method == 'POST':
        form = AutoApprovalSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, '自動審核設定已成功儲存！')
            return redirect('system:auto_approval_settings')
    else:
        # 將列表轉換為文字格式顯示
        initial_data = {
            'exclude_operators': '\n'.join(settings.exclude_operators) if settings.exclude_operators else '',
            'exclude_processes': '\n'.join(settings.exclude_processes) if settings.exclude_processes else '',
            'notification_recipients': '\n'.join(settings.notification_recipients) if settings.notification_recipients else ''
        }
        form = AutoApprovalSettingsForm(instance=settings, initial=initial_data)
    
    # 取得統計資料
    from workorder.models import FillWorkRecord
    total_pending = FillWorkRecord.objects.filter(approval_status='pending').count()
    total_approved = FillWorkRecord.objects.filter(approval_status='approved').count()
    
    context = {
        'form': form,
        'settings': settings,
        'total_pending': total_pending,
        'total_approved': total_approved,
        'conditions_summary': settings.get_approval_conditions_summary()
    }
    
    return render(request, 'system/auto_approval_settings.html', context)


@login_required
def test_switches(request):
    """測試開關功能"""
    from workorder.models import SystemConfig
    
    # 取得設定值
    try:
        auto_approval = SystemConfig.objects.get(key="auto_approval").value == "True"
    except SystemConfig.DoesNotExist:
        auto_approval = False
        
    try:
        notification_enabled = SystemConfig.objects.get(key="notification_enabled").value == "True"
    except SystemConfig.DoesNotExist:
        notification_enabled = True
        
    try:
        audit_log_enabled = SystemConfig.objects.get(key="audit_log_enabled").value == "True"
    except SystemConfig.DoesNotExist:
        audit_log_enabled = True
    
    context = {
        'auto_approval': auto_approval,
        'notification_enabled': notification_enabled,
        'audit_log_enabled': audit_log_enabled,
    }
    
    return render(request, 'system/test_switches.html', context)


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def report_cleanup_settings(request):
    """報表清理設定頁面"""
    import os
    from django.conf import settings
    from reporting.models import ReportExecutionLog
    
    # 取得統計資料
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    file_count = 0
    total_size = 0
    
    if os.path.exists(reports_dir):
        for filename in os.listdir(reports_dir):
            file_path = os.path.join(reports_dir, filename)
            if os.path.isfile(file_path):
                file_count += 1
                total_size += os.path.getsize(file_path)
    
    total_size_mb = total_size / (1024 * 1024)
    log_count = ReportExecutionLog.objects.count()
    
    # 取得保留天數設定
    file_retention_days = getattr(settings, 'REPORT_FILE_RETENTION_DAYS', 7)
    log_retention_days = getattr(settings, 'REPORT_LOG_RETENTION_DAYS', 30)
    
    # 取得清理歷史記錄
    cleanup_logs = CleanupLog.objects.order_by('-execution_time')[:20]
    
    context = {
        'file_count': file_count,
        'total_size_mb': total_size_mb,
        'log_count': log_count,
        'file_retention_days': file_retention_days,
        'log_retention_days': log_retention_days,
        'cleanup_logs': cleanup_logs,
    }
    
    return render(request, 'system/report_cleanup_settings.html', context)


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def update_cleanup_settings(request):
    """更新清理設定"""
    if request.method == 'POST':
        try:
            file_retention_days = int(request.POST.get('file_retention_days', 7))
            log_retention_days = int(request.POST.get('log_retention_days', 30))
            
            # 驗證輸入
            if file_retention_days < 1 or file_retention_days > 365:
                messages.error(request, '報表檔案保留天數必須在1-365天之間')
                return redirect('system:report_cleanup_settings')
            
            if log_retention_days < 1 or log_retention_days > 365:
                messages.error(request, '執行日誌保留天數必須在1-365天之間')
                return redirect('system:report_cleanup_settings')
            
            # 更新設定檔（這裡需要重啟服務才能生效）
            # 實際應用中可能需要使用資料庫儲存設定
            messages.success(request, f'清理設定已更新：檔案保留{file_retention_days}天，日誌保留{log_retention_days}天')
            
            # 記錄操作日誌
            CleanupLog.objects.create(
                action='更新清理設定',
                status='success',
                details=f'檔案保留天數：{file_retention_days}天，日誌保留天數：{log_retention_days}天',
                user=request.user
            )
            
        except ValueError:
            messages.error(request, '請輸入有效的數字')
        except Exception as e:
            messages.error(request, f'更新設定失敗：{str(e)}')
    
    return redirect('system:report_cleanup_settings')


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def execute_cleanup(request):
    """執行清理操作"""
    if request.method == 'POST':
        import json
        from reporting.tasks import cleanup_report_files, cleanup_report_execution_logs, generate_system_cleanup_report
        
        try:
            data = json.loads(request.body)
            cleanup_type = data.get('cleanup_type')
            
            if cleanup_type == 'files':
                cleanup_report_files()
                action = '清理報表檔案'
            elif cleanup_type == 'logs':
                cleanup_report_execution_logs()
                action = '清理執行日誌'
            elif cleanup_type == 'report':
                generate_system_cleanup_report()
                action = '生成清理報告'
            else:
                return JsonResponse({'success': False, 'error': '無效的清理類型'})
            
            # 記錄操作日誌
            CleanupLog.objects.create(
                action=action,
                status='success',
                details=f'手動執行{action}操作',
                user=request.user
            )
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            # 記錄錯誤日誌
            CleanupLog.objects.create(
                action=f'執行清理操作失敗',
                status='failed',
                details=f'錯誤：{str(e)}',
                user=request.user
            )
            
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': '無效的請求方法'})


class ScheduledTaskListView(LoginRequiredMixin, ListView):
    """定時任務清單"""
    model = ScheduledTask
    template_name = 'system/scheduled_task_list.html'
    context_object_name = 'tasks'
    paginate_by = 20

    def get_queryset(self):
        return ScheduledTask.objects.all().order_by('-created_at')


class ScheduledTaskCreateView(LoginRequiredMixin, CreateView):
    """創建定時任務"""
    model = ScheduledTask
    form_class = ScheduledTaskForm
    template_name = 'system/scheduled_task_form.html'
    success_url = reverse_lazy('system:scheduled_task_list')

    def form_valid(self, form):
        # 根據任務類型設定預設的任務函數
        task_type = form.cleaned_data['task_type']
        if task_type == 'auto_approve':
            form.instance.task_function = 'system.tasks.auto_approve_work_reports'
        elif task_type == 'workorder_analysis':
            form.instance.task_function = 'reporting.tasks.auto_analyze_completed_workorders'
        elif task_type == 'data_backup':
            form.instance.task_function = 'system.tasks.auto_backup_database'
        elif task_type == 'report_generation':
            form.instance.task_function = 'reporting.tasks.generate_daily_reports'
        elif task_type == 'data_cleanup':
            form.instance.task_function = 'system.tasks.cleanup_old_data'
        
        response = super().form_valid(form)
        
        # 創建或更新 Celery Beat 定時任務
        self.create_celery_task(form.instance)
        
        messages.success(self.request, f'定時任務 "{form.instance.name}" 已創建')
        return response

    def create_celery_task(self, scheduled_task):
        """創建 Celery Beat 定時任務"""
        try:
            from django_celery_beat.models import PeriodicTask, IntervalSchedule
            
            # 創建或取得間隔排程
            interval_schedule, created = IntervalSchedule.objects.get_or_create(
                every=scheduled_task.interval_minutes,
                period=IntervalSchedule.MINUTES,
            )
            
            # 創建或更新定時任務
            task, created = PeriodicTask.objects.get_or_create(
                name=f"scheduled_task_{scheduled_task.id}",
                defaults={
                    'task': scheduled_task.task_function,
                    'interval': interval_schedule,
                    'enabled': scheduled_task.is_enabled,
                    'description': scheduled_task.description
                }
            )
            
            if not created:
                task.task = scheduled_task.task_function
                task.interval = interval_schedule
                task.enabled = scheduled_task.is_enabled
                task.description = scheduled_task.description
                task.save()
                
        except Exception as e:
            messages.error(self.request, f'創建 Celery 定時任務失敗: {str(e)}')


class ScheduledTaskUpdateView(LoginRequiredMixin, UpdateView):
    """更新定時任務"""
    model = ScheduledTask
    form_class = ScheduledTaskForm
    template_name = 'system/scheduled_task_form.html'
    success_url = reverse_lazy('system:scheduled_task_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # 更新 Celery Beat 定時任務
        self.update_celery_task(form.instance)
        
        messages.success(self.request, f'定時任務 "{form.instance.name}" 已更新')
        return response

    def update_celery_task(self, scheduled_task):
        """更新 Celery Beat 定時任務"""
        try:
            from django_celery_beat.models import PeriodicTask, CrontabSchedule
            
            # 解析 Cron 表達式
            cron_parts = scheduled_task.cron_expression.split()
            if len(cron_parts) != 5:
                raise ValueError("Cron 表達式格式錯誤")
            
            minute, hour, day_of_month, month_of_year, day_of_week = cron_parts
            
            # 創建或取得 Crontab 排程
            crontab, created = CrontabSchedule.objects.get_or_create(
                minute=minute,
                hour=hour,
                day_of_month=day_of_month,
                month_of_year=month_of_year,
                day_of_week=day_of_week,
            )
            
            # 更新定時任務
            task = PeriodicTask.objects.filter(name=f"scheduled_task_{scheduled_task.id}").first()
            if task:
                task.task = scheduled_task.task_function
                task.crontab = crontab
                task.enabled = scheduled_task.is_enabled
                task.description = scheduled_task.description
                task.save()
            else:
                # 如果不存在，創建新的
                PeriodicTask.objects.create(
                    name=f"scheduled_task_{scheduled_task.id}",
                    task=scheduled_task.task_function,
                    crontab=crontab,
                    enabled=scheduled_task.is_enabled,
                    description=scheduled_task.description
                )
                
        except Exception as e:
            messages.error(self.request, f'更新 Celery 定時任務失敗: {str(e)}')


class ScheduledTaskDeleteView(LoginRequiredMixin, DeleteView):
    """刪除定時任務"""
    model = ScheduledTask
    template_name = 'system/scheduled_task_confirm_delete.html'
    success_url = reverse_lazy('system:scheduled_task_list')

    def delete(self, request, *args, **kwargs):
        scheduled_task = self.get_object()
        
        # 刪除 Celery Beat 定時任務
        try:
            from django_celery_beat.models import PeriodicTask
            task = PeriodicTask.objects.filter(name=f"scheduled_task_{scheduled_task.id}").first()
            if task:
                task.delete()
        except Exception as e:
            messages.error(request, f'刪除 Celery 定時任務失敗: {str(e)}')
        
        messages.success(request, f'定時任務 "{scheduled_task.name}" 已刪除')
        return super().delete(request, *args, **kwargs)


@login_required
def toggle_scheduled_task(request, pk):
    """切換定時任務啟用狀態"""
    try:
        task = ScheduledTask.objects.get(pk=pk)
        task.is_enabled = not task.is_enabled
        task.save()
        
        # 更新 Celery Beat 定時任務狀態
        from django_celery_beat.models import PeriodicTask
        celery_task = PeriodicTask.objects.filter(name=f"scheduled_task_{task.id}").first()
        if celery_task:
            celery_task.enabled = task.is_enabled
            celery_task.save()
        
        status = '啟用' if task.is_enabled else '停用'
        return JsonResponse({
            'success': True, 
            'message': f'定時任務已{status}',
            'is_enabled': task.is_enabled
        })
        
    except ScheduledTask.DoesNotExist:
        return JsonResponse({'success': False, 'error': '定時任務不存在'})


@login_required
def test_cron_expression(request):
    """測試 Cron 表達式"""
    if request.method == 'POST':
        cron_expression = request.POST.get('cron_expression', '')
        
        try:
            from croniter import croniter
            from datetime import datetime, timedelta
            
            cron = croniter(cron_expression)
            
            # 計算接下來5次的執行時間
            next_runs = []
            current_time = datetime.now()
            
            for i in range(5):
                next_run = cron.get_next(datetime)
                next_runs.append(next_run.strftime('%Y-%m-%d %H:%M:%S'))
            
            return JsonResponse({
                'success': True,
                'description': cron.get_description(locale='zh_TW'),
                'next_runs': next_runs
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Cron 表達式錯誤: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': '無效的請求方法'})


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def add_auto_approval_task(request):
    """
    新增自動審核定時任務 API
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支援 POST 請求'})
    
    try:
        from system.models import ScheduledTask
        
        name = request.POST.get('name', '新自動審核任務')
        interval_minutes = int(request.POST.get('interval_minutes', 30))
        
        if interval_minutes < 5 or interval_minutes > 1440:
            return JsonResponse({
                'success': False,
                'message': '執行間隔必須在 5-1440 分鐘之間'
            })
        
        # 建立新任務
        new_task = ScheduledTask.objects.create(
            name=name,
            task_type='auto_approve',
            task_function='system.tasks.auto_approve_work_reports',
            interval_minutes=interval_minutes,
            is_enabled=True,
            description=f'自動審核定時任務 - {name}'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'成功新增自動審核定時任務：{name}',
            'task_id': new_task.id
        })
        
    except Exception as e:
        logger.error(f"新增自動審核定時任務失敗: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'新增失敗：{str(e)}'
        })


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def delete_auto_approval_task(request):
    """
    刪除自動審核定時任務 API
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支援 POST 請求'})
    
    try:
        from system.models import ScheduledTask
        
        task_id = request.POST.get('task_id')
        if not task_id:
            return JsonResponse({
                'success': False,
                'message': '缺少任務 ID'
            })
        
        # 檢查是否是最後一個任務
        total_tasks = ScheduledTask.objects.filter(task_type='auto_approve').count()
        if total_tasks <= 1:
            return JsonResponse({
                'success': False,
                'message': '至少需要保留一個自動審核定時任務'
            })
        
        # 刪除任務
        task = ScheduledTask.objects.get(id=task_id, task_type='auto_approve')
        task_name = task.name
        task.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'成功刪除自動審核定時任務：{task_name}'
        })
        
    except ScheduledTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '找不到指定的任務'
        })
    except Exception as e:
        logger.error(f"刪除自動審核定時任務失敗: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'刪除失敗：{str(e)}'
        })


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def execute_specific_auto_approval_task(request):
    """
    執行指定的自動審核定時任務 API
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支援 POST 請求'})
    
    try:
        from system.models import ScheduledTask
        from system.tasks import auto_approve_work_reports
        from django.utils import timezone
        
        task_id = request.POST.get('task_id')
        if not task_id:
            return JsonResponse({
                'success': False,
                'message': '缺少任務 ID'
            })
        
        # 取得任務
        task = ScheduledTask.objects.get(id=task_id, task_type='auto_approve')
        
        # 執行自動審核
        result = auto_approve_work_reports()
        
        # 更新任務執行記錄
        task.last_run_at = timezone.now()
        task.execution_count += 1
        
        if result['success']:
            task.success_count += 1
            task.last_error_message = ''
        else:
            task.error_count += 1
            task.last_error_message = result.get('error', '未知錯誤')
        
        task.save()
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': f"任務 {task.name} 執行完成：{result['message']}"
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f"任務 {task.name} 執行失敗：{result.get('error', '未知錯誤')}"
            })
            
    except ScheduledTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '找不到指定的任務'
        })
    except Exception as e:
        logger.error(f"執行指定自動審核定時任務失敗: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'執行失敗：{str(e)}'
        })


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def execute_all_auto_approval_tasks(request):
    """
    執行所有自動審核定時任務 API
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支援 POST 請求'})
    
    try:
        from system.models import ScheduledTask
        from system.tasks import auto_approve_work_reports
        from django.utils import timezone
        
        # 取得所有啟用的自動審核定時任務
        enabled_tasks = ScheduledTask.objects.filter(
            task_type='auto_approve',
            is_enabled=True
        )
        
        if not enabled_tasks.exists():
            return JsonResponse({
                'success': False,
                'message': '沒有啟用的自動審核定時任務'
            })
        
        # 執行自動審核
        result = auto_approve_work_reports()
        
        # 更新所有任務的執行記錄
        for task in enabled_tasks:
            task.last_run_at = timezone.now()
            task.execution_count += 1
            
            if result['success']:
                task.success_count += 1
                task.last_error_message = ''
            else:
                task.error_count += 1
                task.last_error_message = result.get('error', '未知錯誤')
            
            task.save()
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': f"所有自動審核定時任務執行完成：{result['message']}"
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f"自動審核定時任務執行失敗：{result.get('error', '未知錯誤')}"
            })
            
    except Exception as e:
        logger.error(f"執行所有自動審核定時任務失敗: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'執行失敗：{str(e)}'
        })


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def auto_approval_tasks(request):
    """
    自動審核定時任務管理頁面
    管理多個自動審核定時任務
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            # 建立新的定時任務
            name = request.POST.get('name')
            interval_minutes = request.POST.get('interval_minutes')
            description = request.POST.get('description', '')
            
            if not name or not interval_minutes:
                messages.error(request, "任務名稱和執行間隔為必填欄位")
                return redirect('system:auto_approval_tasks')
            
            try:
                interval_minutes = int(interval_minutes)
                if interval_minutes < 1 or interval_minutes > 1440:
                    messages.error(request, "執行間隔必須在1-1440分鐘之間")
                    return redirect('system:auto_approval_tasks')
                
                # 檢查任務名稱是否重複
                if AutoApprovalTask.objects.filter(name=name).exists():
                    messages.error(request, f"任務名稱 '{name}' 已存在")
                    return redirect('system:auto_approval_tasks')
                
                # 建立新任務
                task = AutoApprovalTask.objects.create(
                    name=name,
                    interval_minutes=interval_minutes,
                    description=description,
                    created_by=request.user
                )
                
                messages.success(request, f"定時任務 '{name}' 建立成功")
                
            except ValueError:
                messages.error(request, "執行間隔必須是有效的數字")
            except Exception as e:
                messages.error(request, f"建立任務失敗：{str(e)}")
                
        elif action == 'update':
            # 更新定時任務
            task_id = request.POST.get('task_id')
            name = request.POST.get('name')
            interval_minutes = request.POST.get('interval_minutes')
            description = request.POST.get('description', '')
            is_enabled = request.POST.get('is_enabled') == 'on'
            
            try:
                task = AutoApprovalTask.objects.get(id=task_id)
                
                # 檢查名稱是否重複（排除自己）
                if AutoApprovalTask.objects.filter(name=name).exclude(id=task_id).exists():
                    messages.error(request, f"任務名稱 '{name}' 已存在")
                    return redirect('system:auto_approval_tasks')
                
                task.name = name
                task.interval_minutes = int(interval_minutes)
                task.description = description
                task.is_enabled = is_enabled
                task.updated_by = request.user
                task.save()
                
                messages.success(request, f"定時任務 '{name}' 更新成功")
                
            except AutoApprovalTask.DoesNotExist:
                messages.error(request, "找不到指定的定時任務")
            except ValueError:
                messages.error(request, "執行間隔必須是有效的數字")
            except Exception as e:
                messages.error(request, f"更新任務失敗：{str(e)}")
                
        elif action == 'delete':
            # 刪除定時任務
            task_id = request.POST.get('task_id')
            
            try:
                task = AutoApprovalTask.objects.get(id=task_id)
                task_name = task.name
                task.delete()
                messages.success(request, f"定時任務 '{task_name}' 刪除成功")
                
            except AutoApprovalTask.DoesNotExist:
                messages.error(request, "找不到指定的定時任務")
            except Exception as e:
                messages.error(request, f"刪除任務失敗：{str(e)}")
                
        elif action == 'toggle':
            # 切換任務啟用狀態
            task_id = request.POST.get('task_id')
            
            try:
                task = AutoApprovalTask.objects.get(id=task_id)
                task.is_enabled = not task.is_enabled
                task.updated_by = request.user
                task.save()
                
                status = "啟用" if task.is_enabled else "停用"
                messages.success(request, f"定時任務 '{task.name}' 已{status}")
                
            except AutoApprovalTask.DoesNotExist:
                messages.error(request, "找不到指定的定時任務")
            except Exception as e:
                messages.error(request, f"切換狀態失敗：{str(e)}")
                
        elif action == 'execute':
            # 手動執行定時任務
            task_id = request.POST.get('task_id')
            
            try:
                task = AutoApprovalTask.objects.get(id=task_id)
                
                # 執行自動審核任務
                from system.tasks import auto_approve_work_reports
                result = auto_approve_work_reports.delay()
                
                # 更新任務執行記錄
                task.execution_count += 1
                task.last_run_at = timezone.now()
                task.updated_by = request.user
                task.save()
                
                messages.success(request, f"定時任務 '{task.name}' 手動執行成功")
                
            except AutoApprovalTask.DoesNotExist:
                messages.error(request, "找不到指定的定時任務")
            except Exception as e:
                messages.error(request, f"執行任務失敗：{str(e)}")
        
        return redirect('system:auto_approval_tasks')
    
    # 取得所有定時任務
    tasks = AutoApprovalTask.objects.all().order_by('-created_at')
    
    context = {
        'tasks': tasks,
        'page_title': '自動審核定時任務管理',
        'breadcrumb': [
            {'name': '系統管理', 'url': 'system:index'},
            {'name': '自動審核定時任務管理', 'url': 'system:auto_approval_tasks'},
        ]
    }
    
    return render(request, 'system/auto_approval_tasks.html', context)

@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def auto_approval_task_detail(request, task_id):
    """
    自動審核定時任務詳情頁面
    """
    try:
        task = AutoApprovalTask.objects.get(id=task_id)
    except AutoApprovalTask.DoesNotExist:
        messages.error(request, "找不到指定的定時任務")
        return redirect('system:auto_approval_tasks')
    
    if request.method == 'POST':
        # 更新任務
        name = request.POST.get('name')
        interval_minutes = request.POST.get('interval_minutes')
        description = request.POST.get('description', '')
        is_enabled = request.POST.get('is_enabled') == 'on'
        
        try:
            # 檢查名稱是否重複
            if AutoApprovalTask.objects.filter(name=name).exclude(id=task_id).exists():
                messages.error(request, f"任務名稱 '{name}' 已存在")
            else:
                task.name = name
                task.interval_minutes = int(interval_minutes)
                task.description = description
                task.is_enabled = is_enabled
                task.updated_by = request.user
                task.save()
                
                messages.success(request, f"定時任務 '{name}' 更新成功")
                return redirect('system:auto_approval_tasks')
                
        except ValueError:
            messages.error(request, "執行間隔必須是有效的數字")
        except Exception as e:
            messages.error(request, f"更新任務失敗：{str(e)}")
    
    context = {
        'task': task,
        'page_title': f'編輯定時任務 - {task.name}',
        'breadcrumb': [
            {'name': '系統管理', 'url': 'system:index'},
            {'name': '自動審核定時任務管理', 'url': 'system:auto_approval_tasks'},
            {'name': f'編輯 - {task.name}', 'url': 'system:auto_approval_task_detail', 'args': [task_id]},
        ]
    }
    
    return render(request, 'system/auto_approval_task_detail.html', context)


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def report_settings(request):
    """
    報表設定頁面
    """
    context = {
        'page_title': '報表設定',
        'breadcrumb': [
            {'name': '系統管理', 'url': 'system:index'},
            {'name': '報表設定', 'url': 'system:report_settings'},
        ]
    }
    
    return render(request, 'system/report_settings.html', context)


@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def manual_sync_reports(request):
    """
    手動同步報表頁面
    """
    context = {
        'page_title': '手動同步報表',
        'breadcrumb': [
            {'name': '系統管理', 'url': 'system:index'},
            {'name': '報表設定', 'url': 'system:report_settings'},
            {'name': '手動同步報表', 'url': 'system:manual_sync_reports'},
        ]
    }
    
    return render(request, 'system/manual_sync_reports.html', context)






