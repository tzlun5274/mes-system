# 導入必要的 Python 模組，用於處理資料庫連線、Django 視圖、日誌記錄等功能
import json
import os
import pymssql  # 用於連接到 MSSQL 資料庫
import logging  # 用於記錄日誌
import subprocess  # 用於執行外部命令（如 psql）
import psycopg2  # 用於連接到 PostgreSQL 資料庫
import traceback  # 用於捕獲異常的詳細堆疊資訊
from django.shortcuts import render, redirect, get_object_or_404  # Django 視圖相關函數
from django.contrib.auth.decorators import (
    login_required,
    user_passes_test,
)  # 用於權限控制
from django.contrib import messages  # 用於顯示消息提示
from django.utils import timezone  # 用於處理時間
from django.db import transaction  # 用於資料庫事務管理
from celery import shared_task  # 用於異步任務
from .models import ERPConfig, CompanyConfig, ERPIntegrationOperationLog  # 導入模型
from django_celery_beat.models import CrontabSchedule, PeriodicTask  # 導入定時任務模型
from django.http import JsonResponse

# 設定ERP整合模組的日誌記錄器
erp_logger = logging.getLogger("erp_integration")
erp_handler = logging.FileHandler("/var/log/mes/erp_integration.log")
erp_handler.setFormatter(
    logging.Formatter("%(levelname)s %(asctime)s %(module)s %(message)s")
)
erp_logger.addHandler(erp_handler)
erp_logger.setLevel(logging.INFO)

# 設置專屬的日誌記錄器，只記錄錯誤和操作日誌
logging.basicConfig(
    level=logging.ERROR,  # 只記錄錯誤等級以上的日誌
    format="%(levelname)s %(asctime)s %(module)s %(message)s",
    handlers=[
        logging.FileHandler("/var/log/mes/django/erp_integration.log"),
    ],
)
logger = logging.getLogger("erp_integration")

# 設置 JSON 配置文件路徑
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLES_CONFIG_PATH = os.path.join(BASE_DIR, "erp_integration", "config", "tables.json")

# 從 .env 嵌入的 PostgreSQL 資料庫參數
DATABASE_USER = "mes_user"
DATABASE_PASSWORD = "mes_password"
DATABASE_HOST = "localhost"
DATABASE_PORT = "5432"

# MSSQL 到 PostgreSQL 的資料型態映射，確保一致性
MSSQL_TO_PGSQL_TYPE_MAPPING = {
    "binary": "BYTEA",
    "varbinary": "BYTEA",
    "bit": "BOOLEAN",
    "char": "CHAR",
    "nchar": "CHAR",
    "varchar": "VARCHAR",
    "nvarchar": "VARCHAR",
    "text": "TEXT",
    "ntext": "TEXT",
    "int": "INTEGER",
    "bigint": "BIGINT",
    "smallint": "SMALLINT",
    "tinyint": "SMALLINT",
    "float": "DOUBLE PRECISION",
    "real": "REAL",
    "decimal": "NUMERIC",
    "numeric": "NUMERIC",
    "money": "NUMERIC(19,4)",
    "smallmoney": "NUMERIC(10,4)",
    "datetime": "TIMESTAMP",
    "datetime2": "TIMESTAMP",
    "smalldatetime": "TIMESTAMP",
    "date": "DATE",
    "time": "TIME",
    "uniqueidentifier": "UUID",
    "image": "BYTEA",
}


# 定義函數，從 JSON 配置文件中讀取允許同步的資料表清單
def load_allowed_tables():
    try:
        with open(TABLES_CONFIG_PATH, "r") as f:
            config = json.load(f)
            allowed_tables = config.get("allowed_tables", [])
            return sorted(allowed_tables)
    except FileNotFoundError:
        logger.error(f"找不到配置文件：{TABLES_CONFIG_PATH}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"解析 JSON 文件失敗：{e}")
        return []


# 定義權限檢查函數，限制只有超級用戶可以訪問
def superuser_required(user):
    return user.is_superuser


# 定義全量同步函數
def full_sync_data(
    company, config, cursor_mssql, cursor_postgres, conn_postgres, sync_tables, user_id
):
    failed_tables = []
    failed_rows = []

    for table in sync_tables:
        try:
            # 獲取 MSSQL 資料表的欄位資訊
            cursor_mssql.execute(
                """
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = %s
            """,
                (table,),
            )
            columns = cursor_mssql.fetchall()
            column_names = [col["COLUMN_NAME"] for col in columns]

            if not column_names:
                logger.warning(f"資料表 {table} 沒有欄位，跳過同步")
                continue

            # 驗證欄位數量
            expected_columns = len(column_names)
            logger.debug(f"表 {table} 應有 {expected_columns} 個欄位：{column_names}")

            # 檢查 PostgreSQL 表是否存在
            cursor_postgres.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """,
                (table,),
            )
            table_exists = cursor_postgres.fetchone()[0]
            logger.debug(f"檢查表 {table} 是否存在：{table_exists}")

            if table_exists:
                cursor_postgres.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
                logger.info(f"刪除現有 PostgreSQL 表 {table}")
                conn_postgres.commit()

            # 創建 PostgreSQL 表，保留 MSSQL 型態、長度和精度
            create_table_query = f'CREATE TABLE "{table}" ('
            create_table_query += '"row_id" SERIAL PRIMARY KEY, '
            for col in columns:
                col_name = col["COLUMN_NAME"]
                data_type = col["DATA_TYPE"].lower()
                pg_type = MSSQL_TO_PGSQL_TYPE_MAPPING.get(data_type, "TEXT")
                if data_type in ("varchar", "nvarchar", "char", "nchar"):
                    length = col["CHARACTER_MAXIMUM_LENGTH"]
                    if length and length > 0:
                        pg_type = f"{pg_type}({length})"
                        logger.debug(f"設置字符長度：{table}.{col_name} -> {pg_type}")
                    elif length == -1:
                        pg_type = "TEXT"
                        logger.debug(f"設置為 TEXT：{table}.{col_name}")
                elif data_type in ("numeric", "decimal"):
                    precision = col["NUMERIC_PRECISION"]
                    scale = col["NUMERIC_SCALE"]
                    if precision and scale is not None:
                        pg_type = f"NUMERIC({precision},{scale})"
                        logger.debug(f"設置數值精度：{table}.{col_name} -> {pg_type}")
                create_table_query += f'"{col_name}" {pg_type}, '
            create_table_query += '"updated_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            create_table_query += ");"
            cursor_postgres.execute(create_table_query)
            conn_postgres.commit()
            logger.info(f"在 PostgreSQL 中創建表 {table}")

            # 驗證 PostgreSQL 表結構
            cursor_postgres.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
            """,
                (table,),
            )
            pg_columns = [row[0] for row in cursor_postgres.fetchall()]
            missing_columns = [col for col in column_names if col not in pg_columns]
            extra_columns = [
                col
                for col in pg_columns
                if col not in column_names and col not in ["row_id", "updated_at"]
            ]
            if missing_columns:
                logger.error(f"表 {table} 缺少欄位：{missing_columns}")
                raise Exception(f"表 {table} 缺少欄位：{missing_columns}")
            if extra_columns:
                logger.error(f"表 {table} 多餘欄位：{extra_columns}")
                raise Exception(f"表 {table} 多餘欄位：{extra_columns}")

            # 同步數據
            cursor_mssql.execute(f"SELECT * FROM {table}")
            rows = cursor_mssql.fetchall()
            logger.info(f"從 MSSQL 獲取表 {table} 的數據，總計 {len(rows)} 筆記錄")

            successful_rows = 0
            for row in rows:
                try:
                    columns_list = column_names + ["updated_at"]
                    values = []
                    for col in column_names:
                        value = row[col]
                        col_data_type = next(
                            (
                                c["DATA_TYPE"].lower()
                                for c in columns
                                if c["COLUMN_NAME"] == col
                            ),
                            "text",
                        )
                        if value is None:
                            values.append(None)
                        elif isinstance(value, bytes):
                            if col_data_type in ("varbinary", "binary", "image"):
                                values.append(value)
                            else:
                                try:
                                    value = value.decode(
                                        "utf-16-le", errors="replace"
                                    ).replace("\x00", "")
                                except UnicodeDecodeError:
                                    value = value.decode(
                                        "cp950", errors="replace"
                                    ).replace("\x00", "")
                                values.append(value)
                        elif isinstance(value, str):
                            values.append(value.replace("\x00", ""))
                        else:
                            values.append(value)
                    values.append(timezone.now())

                    placeholders = ", ".join(["%s"] * len(columns_list))
                    insert_query = f"""
                        INSERT INTO "{table}" ({', '.join([f'"{col}"' for col in columns_list])})
                        VALUES ({placeholders})
                        RETURNING "row_id";
                    """
                    cursor_postgres.execute(insert_query, values)
                    if cursor_postgres.fetchone():
                        successful_rows += 1
                except Exception as e:
                    logger.warning(f"表 {table} 的某一行同步失敗：{str(e)}")
                    failed_rows.append(f"表 {table} 行數據：{row}")
                    conn_postgres.rollback()
                    cursor_postgres = conn_postgres.cursor()
                    continue

            conn_postgres.commit()
            logger.info(f"成功同步資料表 {table}，{successful_rows} 筆記錄")

        except Exception as e:
            failed_tables.append(table)
            logger.error(f"同步資料表 {table} 失敗：{str(e)}")
            ERPIntegrationOperationLog.objects.create(
                user=user_id,
                action=f"同步資料表 {table} 失敗：{str(e)[:900]}",
                timestamp=timezone.now(),
            )
            conn_postgres.rollback()
            continue

    return failed_tables, failed_rows


# 定義首頁視圖，僅允許登入的超級用戶訪問
@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def index(request):
    config = ERPConfig.objects.first()
    companies = CompanyConfig.objects.all()
    return render(
        request,
        "erp_integration/index.html",
        {
            "config": config,
            "companies": companies,
        },
    )


from django_celery_beat.models import CrontabSchedule, PeriodicTask  # 導入定時任務模型


# 定義 ERP 連線設定視圖，用於配置 MSSQL 連線參數
@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def config(request):
    config, created = ERPConfig.objects.get_or_create(id=1)
    companies = CompanyConfig.objects.all()

    if request.method == "POST":
        config.server = request.POST.get("server", "")
        config.username = request.POST.get("username", "")
        config.password = request.POST.get("password", "")
        config.save()

        if "test_connection" in request.POST:
            test_company_code = request.POST.get("test_company_code", "")
            if not test_company_code:
                messages.error(request, "請選擇一個公司進行連線測試！")
                return redirect("erp_integration:config")

            company = get_object_or_404(CompanyConfig, company_code=test_company_code)
            if not company.mssql_database:
                messages.error(
                    request, f"公司 {company.company_name} 未設定 MSSQL 資料庫名稱！"
                )
                return redirect("erp_integration:config")

            try:
                conn = pymssql.connect(
                    server=config.server,
                    user=config.username,
                    password=config.password,
                    database=company.mssql_database,
                    timeout=30,
                    tds_version="7.0",
                )
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                conn.close()
                messages.success(
                    request, f"連線測試成功（資料庫：{company.mssql_database}）！"
                )
                ERPIntegrationOperationLog.objects.create(
                    user=request.user.username,
                    action=f"連線測試成功（資料庫：{company.mssql_database}）",
                    timestamp=timezone.now(),
                )
            except Exception as e:
                error_msg = str(e) if str(e) else "未知錯誤"
                messages.error(
                    request,
                    f"連線測試失敗：{error_msg}\n連線參數：服務器={config.server}, 使用者={config.username}, 資料庫={company.mssql_database}",
                )
                ERPIntegrationOperationLog.objects.create(
                    user=request.user.username,
                    action=f"連線測試失敗（資料庫：{company.mssql_database}）：{error_msg[:900]}\n連線參數：服務器={config.server}, 使用者={config.username}, 資料庫={company.mssql_database}",
                    timestamp=timezone.now(),
                )
                logger.error(f"連線失敗詳細日誌：{error_msg}")
            return redirect("erp_integration:config")

        messages.success(request, "ERP 連線設定已更新！")
        ERPIntegrationOperationLog.objects.create(
            user=request.user.username,
            action="更新 ERP 連線設定",
            timestamp=timezone.now(),
        )
        return redirect("erp_integration:index")

    ERPIntegrationOperationLog.objects.create(
        user=request.user.username, action="查看 ERP 連線設定", timestamp=timezone.now()
    )
    return render(
        request,
        "erp_integration/config.html",
        {"config": config, "companies": companies},
    )


# 定義全量同步函數
def full_sync_data(
    company, config, cursor_mssql, cursor_postgres, conn_postgres, sync_tables, user_id
):
    failed_tables = []
    failed_rows = []

    for table in sync_tables:
        try:
            cursor_mssql.execute(
                """
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = %s
            """,
                (table,),
            )
            columns = cursor_mssql.fetchall()
            column_names = [col["COLUMN_NAME"] for col in columns]

            if not column_names:
                logger.warning(f"資料表 {table} 沒有欄位，跳過同步")
                continue

            # 驗證欄位數量
            expected_columns = len(column_names)
            logger.debug(f"表 {table} 應有 {expected_columns} 個欄位：{column_names}")

            cursor_postgres.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """,
                (table,),
            )
            table_exists = cursor_postgres.fetchone()[0]
            logger.debug(f"檢查表 {table} 是否存在：{table_exists}")

            if table_exists:
                cursor_postgres.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
                logger.info(f"刪除現有 PostgreSQL 表 {table}")
                conn_postgres.commit()

            create_table_query = f'CREATE TABLE "{table}" ('
            create_table_query += '"row_id" SERIAL PRIMARY KEY, '
            for col in columns:
                col_name = col["COLUMN_NAME"]
                data_type = col["DATA_TYPE"].lower()
                pg_type = MSSQL_TO_PGSQL_TYPE_MAPPING.get(data_type, "TEXT")
                if data_type in ("varchar", "nvarchar", "char", "nchar"):
                    length = col["CHARACTER_MAXIMUM_LENGTH"]
                    if length and length > 0:
                        pg_type = f"{pg_type}({length})"
                        logger.debug(f"設置字符長度：{table}.{col_name} -> {pg_type}")
                    elif length == -1:
                        pg_type = "TEXT"
                        logger.debug(f"設置為 TEXT：{table}.{col_name}")
                elif data_type in ("numeric", "decimal", "money", "smallmoney"):
                    precision = col["NUMERIC_PRECISION"]
                    scale = col["NUMERIC_SCALE"]
                    if precision and scale is not None:
                        pg_type = f"NUMERIC({precision},{scale})"
                        logger.debug(f"設置數值精度：{table}.{col_name} -> {pg_type}")
                create_table_query += f'"{col_name}" {pg_type}, '
            create_table_query += '"updated_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            create_table_query += ");"
            cursor_postgres.execute(create_table_query)
            conn_postgres.commit()
            logger.info(f"在 PostgreSQL 中創建表 {table}")

            # 驗證 PostgreSQL 表結構
            cursor_postgres.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
            """,
                (table,),
            )
            pg_columns = [row[0] for row in cursor_postgres.fetchall()]
            missing_columns = [col for col in column_names if col not in pg_columns]
            extra_columns = [
                col
                for col in pg_columns
                if col not in column_names and col not in ["row_id", "updated_at"]
            ]
            if missing_columns:
                logger.error(f"表 {table} 缺少欄位：{missing_columns}")
                raise Exception(f"表 {table} 缺少欄位：{missing_columns}")
            if extra_columns:
                logger.error(f"表 {table} 多餘欄位：{extra_columns}")
                raise Exception(f"表 {table} 多餘欄位：{extra_columns}")

            cursor_mssql.execute(f"SELECT * FROM {table}")
            rows = cursor_mssql.fetchall()
            logger.info(f"從 MSSQL 獲取表 {table} 的數據，總計 {len(rows)} 筆記錄")

            successful_rows = 0
            for row in rows:
                try:
                    columns_list = column_names + ["updated_at"]
                    values = []
                    for col in column_names:
                        value = row[col]
                        col_data_type = next(
                            (
                                c["DATA_TYPE"].lower()
                                for c in columns
                                if c["COLUMN_NAME"] == col
                            ),
                            "text",
                        )
                        if value is None:
                            values.append(None)
                        elif isinstance(value, bytes):
                            if col_data_type in ("varbinary", "binary", "image"):
                                values.append(value)
                            else:
                                try:
                                    value = value.decode(
                                        "utf-16-le", errors="replace"
                                    ).replace("\x00", "")
                                except UnicodeDecodeError:
                                    value = value.decode(
                                        "cp950", errors="replace"
                                    ).replace("\x00", "")
                                values.append(value)
                        elif isinstance(value, str):
                            values.append(value.replace("\x00", ""))
                        else:
                            values.append(value)
                    values.append(timezone.now())

                    placeholders = ", ".join(["%s"] * len(columns_list))
                    insert_query = f"""
                        INSERT INTO "{table}" ({', '.join([f'"{col}"' for col in columns_list])})
                        VALUES ({placeholders})
                        RETURNING "row_id";
                    """
                    cursor_postgres.execute(insert_query, values)
                    if cursor_postgres.fetchone():
                        successful_rows += 1
                except Exception as e:
                    logger.warning(f"表 {table} 的某一行同步失敗：{str(e)}")
                    failed_rows.append(f"表 {table} 行數據：{row}")
                    conn_postgres.rollback()
                    cursor_postgres = conn_postgres.cursor()
                    continue

            conn_postgres.commit()
            logger.info(f"成功同步資料表 {table}，{successful_rows} 筆記錄")

        except Exception as e:
            failed_tables.append(table)
            logger.error(f"同步資料表 {table} 失敗：{str(e)}")
            ERPIntegrationOperationLog.objects.create(
                user=user_id,
                action=f"同步資料表 {table} 失敗：{str(e)[:900]}",
                timestamp=timezone.now(),
            )
            conn_postgres.rollback()
            continue

    return failed_tables, failed_rows


# 定義公司設定視圖，用於管理公司設定和執行資料同步
@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def company_config(request):
    companies = CompanyConfig.objects.all()

    if request.method == "POST":
        if "sync_data" in request.POST or "full_sync_data" in request.POST:
            company_id = request.POST.get("company_id")
            company = get_object_or_404(CompanyConfig, id=company_id)
            config = ERPConfig.objects.first()

            if not config:
                messages.error(request, "ERP 連線設定不存在！請先完成設定。")
                return redirect("erp_integration:config")

            if not config.server or not config.username or not config.password:
                messages.error(
                    request,
                    "ERP 連線設定不完整（缺少服務器、使用者名稱或密碼）！請先完成設定。",
                )
                return redirect("erp_integration:company_config")

            if not company.mssql_database or not company.mes_database:
                messages.error(
                    request,
                    f"公司 {company.company_name} 的 MSSQL 或 MES 資料庫名稱未設置！",
                )
                return redirect("erp_integration:company_config")

            sync_tables = company.sync_tables.split(",") if company.sync_tables else []
            all_table_names = load_allowed_tables()

            if not sync_tables:
                messages.warning(
                    request, f"公司 {company.company_name} 未設置需要同步的資料表！"
                )
                return redirect("erp_integration:company_config")

            sync_tables = sorted(
                [table for table in sync_tables if table in all_table_names]
            )
            if not sync_tables:
                messages.warning(
                    request, f"公司 {company.company_name} 的同步資料表無效！"
                )
                return redirect("erp_integration:company_config")

            full_sync = "full_sync_data" in request.POST
            sync_data_task.delay(company_id, full_sync, request.user.username)
            sync_type = "全量同步" if full_sync else "增量同步"
            messages.success(
                request,
                f"已提交 {sync_type} 任務，同步正在後台執行，請稍後查看操作日誌！",
            )
            return redirect("erp_integration:company_config")

        if "update_sync_interval" in request.POST:
            company_id = request.POST.get("company_id")
            company = get_object_or_404(CompanyConfig, id=company_id)
            sync_interval_minutes = request.POST.get("sync_interval_minutes", "0")

            try:
                sync_interval_minutes = int(sync_interval_minutes)
                if sync_interval_minutes < 0:
                    raise ValueError("同步間隔不能為負數")
            except ValueError:
                messages.error(
                    request,
                    f"無效的同步間隔：{sync_interval_minutes}，請輸入非負整數！",
                )
                return redirect("erp_integration:company_config")

            company.sync_interval_minutes = sync_interval_minutes
            company.save(update_fields=["sync_interval_minutes"])

            task_name = f"sync_company_{company_id}"
            if sync_interval_minutes > 0:
                schedule, _ = CrontabSchedule.objects.get_or_create(
                    minute=f"*/{sync_interval_minutes}",
                    hour="*",
                    day_of_week="*",
                    day_of_month="*",
                    month_of_year="*",
                )
                periodic_task, created = PeriodicTask.objects.get_or_create(
                    name=task_name,
                    defaults={
                        "crontab": schedule,
                        "task": "erp_integration.views.sync_data_task",
                        "args": json.dumps([company_id, False, "system"]),
                        "enabled": True,
                    },
                )
                if not created:
                    periodic_task.crontab = schedule
                    periodic_task.enabled = True
                    periodic_task.save()
                logger.info(
                    f"為公司 {company.company_name} 創建/更新定時任務，每 {sync_interval_minutes} 分鐘執行一次增量同步"
                )
                messages.success(
                    request,
                    f"已為公司 {company.company_name} 設定每 {sync_interval_minutes} 分鐘自動增量同步！",
                )
            else:
                try:
                    periodic_task = PeriodicTask.objects.get(name=task_name)
                    periodic_task.enabled = False
                    periodic_task.delete()
                    logger.info(f"已禁用公司 {company.company_name} 的定時同步任務")
                    messages.success(
                        request, f"已禁用公司 {company.company_name} 的自動增量同步！"
                    )
                except PeriodicTask.DoesNotExist:
                    logger.info(f"公司 {company.company_name} 無定時同步任務")
                    messages.info(
                        request, f"公司 {company.company_name} 未設定自動增量同步！"
                    )

            ERPIntegrationOperationLog.objects.create(
                user=request.user.username,
                action=f"更新公司 {company.company_name} 同步間隔為 {sync_interval_minutes} 分鐘",
                timestamp=timezone.now(),
            )
            return redirect("erp_integration:company_config")

        if "delete" in request.POST:
            company_id = request.POST.get("company_id")
            company = get_object_or_404(CompanyConfig, id=company_id)
            company_name = company.company_name

            task_name = f"sync_company_{company_id}"
            try:
                periodic_task = PeriodicTask.objects.get(name=task_name)
                periodic_task.enabled = False
                periodic_task.delete()
                logger.info(f"已刪除公司 {company_name} 的定時同步任務")
            except PeriodicTask.DoesNotExist:
                logger.info(f"公司 {company_name} 無定時同步任務")

            company.delete()
            messages.success(request, f"公司 {company_name} 已刪除！")
            ERPIntegrationOperationLog.objects.create(
                user=request.user.username,
                action=f"刪除公司：{company_name}",
                timestamp=timezone.now(),
            )
            return redirect("erp_integration:company_config")

    return render(
        request,
        "erp_integration/company_config.html",
        {
            "companies": companies,
        },
    )


# 定義異步任務，用於執行資料同步（入口函數）
@shared_task
def sync_data_task(company_id, full_sync, user_id):
    try:
        company = CompanyConfig.objects.get(id=company_id)
    except CompanyConfig.DoesNotExist:
        error_msg = f"公司設定 ID {company_id} 不存在，無法執行同步"
        logger.error(error_msg)
        ERPIntegrationOperationLog.objects.create(
            user=user_id, action=error_msg, timestamp=timezone.now()
        )
        return
    config = ERPConfig.objects.first()
    if not config:
        error_msg = "ERP 連線設定不存在，無法執行同步"
        logger.error(error_msg)
        ERPIntegrationOperationLog.objects.create(
            user=user_id, action=error_msg, timestamp=timezone.now()
        )
        return

    conn_mssql = None
    conn_postgres = None
    try:
        conn_mssql = pymssql.connect(
            server=config.server,
            user=config.username,
            password=config.password,
            database=company.mssql_database,
            timeout=30,
            tds_version="7.0",
        )
        cursor_mssql = conn_mssql.cursor(as_dict=True)

        conn_postgres = psycopg2.connect(
            dbname=company.mes_database,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            host=DATABASE_HOST,
            port=DATABASE_PORT,
        )
        conn_postgres.autocommit = False
        cursor_postgres = conn_postgres.cursor()

        sync_tables = company.sync_tables.split(",") if company.sync_tables else []
        all_table_names = load_allowed_tables()

        if not sync_tables:
            logger.warning(f"公司 {company.company_name} 未設置需要同步的資料表！")
            return

        sync_tables = sorted(
            [table for table in sync_tables if table in all_table_names]
        )
        if not sync_tables:
            logger.warning(f"公司 {company.company_name} 的同步資料表無效！")
            return

        cursor_mssql.execute(
            "SELECT CHANGE_TRACKING_CURRENT_VERSION() AS CurrentVersion"
        )
        current_version = cursor_mssql.fetchone()["CurrentVersion"]
        if current_version is None:
            logger.warning(
                f"資料庫 {company.mssql_database} 未啟用變更追蹤，無法進行增量同步"
            )
            return

        if full_sync:
            company.last_sync_version = 0
            company.save(update_fields=["last_sync_version"])
            logger.info(
                f"執行全量同步，重置公司 {company.company_name} 的 last_sync_version 為 0"
            )
            failed_tables, failed_rows = full_sync_data(
                company,
                config,
                cursor_mssql,
                cursor_postgres,
                conn_postgres,
                sync_tables,
                user_id,
            )
        else:
            last_version = company.last_sync_version or 0
            if last_version >= current_version:
                logger.info(
                    f"公司 {company.company_name} 無新變更（當前版本 {current_version} <= 上次同步版本 {last_version}），跳過同步"
                )
                return

            logger.info(
                f"公司 {company.company_name} 有新變更（從版本 {last_version} 到 {current_version}），開始增量同步"
            )
            failed_tables, failed_rows = incremental_sync_data(
                company,
                config,
                cursor_mssql,
                cursor_postgres,
                conn_postgres,
                sync_tables,
                user_id,
                last_version,
                current_version,
            )

        company.last_sync_version = current_version
        company.last_sync_time = timezone.now()
        company.save(update_fields=["last_sync_version", "last_sync_time"])
        logger.info(
            f"更新公司 {company.company_name} 的 last_sync_version 為 {current_version}"
        )

        sync_type = "全量同步" if full_sync else "增量同步"
        if failed_tables:
            ERPIntegrationOperationLog.objects.create(
                user=user_id,
                action=f"公司 {company.company_name} 資料{sync_type}部分成功，失敗資料表：{','.join(failed_tables)}\n失敗行：{'; '.join(failed_rows)[:900]}",
                timestamp=timezone.now(),
            )
        else:
            ERPIntegrationOperationLog.objects.create(
                user=user_id,
                action=f"公司 {company.company_name} 資料{sync_type}成功，同步資料表：{', '.join(sync_tables)}",
                timestamp=timezone.now(),
            )

    except Exception as e:
        error_msg = str(e) if str(e) else "未知錯誤"
        ERPIntegrationOperationLog.objects.create(
            user=user_id,
            action=f"資料同步失敗：{error_msg[:900]}",
            timestamp=timezone.now(),
        )
        logger.error(
            f"資料同步失敗詳細日誌：{error_msg}\n堆疊資訊：{traceback.format_exc()}"
        )

    finally:
        if conn_mssql:
            conn_mssql.close()
        if conn_postgres:
            conn_postgres.close()


# 定義變更追蹤同步函數
def incremental_sync_data(
    company,
    config,
    cursor_mssql,
    cursor_postgres,
    conn_postgres,
    sync_tables,
    user_id,
    last_version,
    current_version,
):
    failed_tables = []
    failed_rows = []

    # 明確指定每張表的主鍵欄位（根據 MSSQL 表結構）
    table_primary_keys = {
        "TraBillMain": ["Flag", "BillNo"],
        "TraBillSub": ["Flag", "BillNo", "RowNo"],
        "comCustomer": ["Flag", "ID"],
        "ordBillMain": ["Flag", "BillNO"],
        "ordBillSub": ["Flag", "BillNO", "RowNO"],
        "impPurchaseMain": ["Flag", "PurchaseNo"],
        "impPurchaseMergeSub": ["PurchaseNo", "RowNo"],
        "impPurchaseSub": ["Flag", "PurchaseNo", "RowNo"],
        "prdMKOrdMain": ["Flag", "MKOrdNO"],
        "prdMkOrdMats": ["MkOrdNO", "RowNO"],
        "stkBorrowSub": ["Flag", "BorrowNO", "RowNo"],
        "stkYearMonthQty": ["ProdID", "WareID", "YearMonth"],
        "comProduct": ["ProdID"],
    }

    for table in sync_tables:
        try:
            # 獲取 MSSQL 資料表的欄位資訊
            cursor_mssql.execute(
                """
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = %s
            """,
                (table,),
            )
            columns = cursor_mssql.fetchall()
            column_names = [col["COLUMN_NAME"] for col in columns]

            if not column_names:
                logger.warning(f"資料表 {table} 沒有欄位，跳過同步")
                continue

            # 驗證欄位數量
            expected_columns = len(column_names)
            logger.debug(f"表 {table} 應有 {expected_columns} 個欄位：{column_names}")

            # 使用硬編碼的主鍵欄位
            assumed_primary_keys = table_primary_keys.get(table, [])
            if not assumed_primary_keys:
                common_pk_names = [
                    "ID",
                    "Code",
                    "Key",
                    "BillNO",
                    "RowNO",
                    "Flag",
                    "Seq",
                    "Number",
                    "WareID",
                    "YearMonth",
                ]
                for col in column_names:
                    if col.upper() in [name.upper() for name in common_pk_names]:
                        assumed_primary_keys.append(col)
                if not assumed_primary_keys:
                    assumed_primary_keys = (
                        column_names[:3] if len(column_names) >= 3 else column_names
                    )

            if not assumed_primary_keys:
                logger.warning(
                    f"資料表 {table} 沒有足夠的欄位來假設主鍵，將直接插入數據"
                )
            else:
                logger.info(f"使用資料表 {table} 的主鍵欄位：{assumed_primary_keys}")

            # 檢查 PostgreSQL 中是否已存在該表
            cursor_postgres.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """,
                (table,),
            )
            table_exists = cursor_postgres.fetchone()[0]
            logger.debug(f"檢查表 {table} 是否存在：{table_exists}")

            if not table_exists:
                create_table_query = f'CREATE TABLE "{table}" ('
                create_table_query += '"row_id" SERIAL PRIMARY KEY, '
                for col in columns:
                    col_name = col["COLUMN_NAME"]
                    data_type = col["DATA_TYPE"].lower()
                    pg_type = MSSQL_TO_PGSQL_TYPE_MAPPING.get(data_type, "TEXT")
                    if data_type in ("varchar", "nvarchar", "char", "nchar"):
                        length = col["CHARACTER_MAXIMUM_LENGTH"]
                        if length and length > 0:
                            pg_type = f"{pg_type}({length})"
                            logger.debug(
                                f"設置字符長度：{table}.{col_name} -> {pg_type}"
                            )
                        elif length == -1:
                            pg_type = "TEXT"
                            logger.debug(f"設置為 TEXT：{table}.{col_name}")
                    elif data_type in ("numeric", "decimal", "money", "smallmoney"):
                        precision = col["NUMERIC_PRECISION"]
                        scale = col["NUMERIC_SCALE"]
                        if precision and scale is not None:
                            pg_type = f"NUMERIC({precision},{scale})"
                            logger.debug(
                                f"設置數值精度：{table}.{col_name} -> {pg_type}"
                            )
                    create_table_query += f'"{col_name}" {pg_type}, '
                create_table_query += '"updated_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
                create_table_query += ");"
                cursor_postgres.execute(create_table_query)
                conn_postgres.commit()
                logger.info(f"在 PostgreSQL 中創建表 {table}")
            else:
                cursor_postgres.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = %s 
                        AND column_name = 'row_id'
                    );
                """,
                    (table,),
                )
                has_row_id = cursor_postgres.fetchone()[0]
                if not has_row_id:
                    cursor_postgres.execute(
                        f'ALTER TABLE "{table}" ADD COLUMN "row_id" SERIAL PRIMARY KEY;'
                    )
                    logger.info(f"為表 {table} 添加 row_id 欄位")
                    conn_postgres.commit()

                cursor_postgres.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = %s 
                        AND column_name = 'updated_at'
                    );
                """,
                    (table,),
                )
                has_updated_at = cursor_postgres.fetchone()[0]
                if not has_updated_at:
                    cursor_postgres.execute(
                        f'ALTER TABLE "{table}" ADD COLUMN "updated_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP;'
                    )
                    logger.info(f"為表 {table} 添加 updated_at 欄位")
                    conn_postgres.commit()

            # 驗證 PostgreSQL 表結構
            cursor_postgres.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
            """,
                (table,),
            )
            pg_columns = [row[0] for row in cursor_postgres.fetchall()]
            missing_columns = [col for col in column_names if col not in pg_columns]
            extra_columns = [
                col
                for col in pg_columns
                if col not in column_names and col not in ["row_id", "updated_at"]
            ]
            if missing_columns:
                logger.error(f"表 {table} 缺少欄位：{missing_columns}")
                raise Exception(f"表 {table} 缺少欄位：{missing_columns}")
            if extra_columns:
                logger.error(f"表 {table} 多餘欄位：{extra_columns}")
                raise Exception(f"表 {table} 多餘欄位：{extra_columns}")

            # 增量同步：使用 MSSQL 變更追蹤
            if assumed_primary_keys:
                valid_primary_keys = []
                for pk in assumed_primary_keys:
                    if pk in column_names:
                        valid_primary_keys.append(pk)
                    else:
                        logger.warning(
                            f"欄位 {pk} 在表 {table} 中不存在，跳過該主鍵欄位"
                        )
                if not valid_primary_keys:
                    logger.warning(f"表 {table} 無有效主鍵欄位，將直接插入數據")
                    valid_primary_keys = column_names[:1]

                join_conditions = " AND ".join(
                    [f"t.[{pk}] = ct.[{pk}]" for pk in valid_primary_keys]
                )
                query = f"""
                    SELECT t.*
                    FROM CHANGETABLE(CHANGES {table}, {last_version}) AS ct
                    JOIN {table} t
                    ON {join_conditions}
                """
            else:
                query = f"""
                    SELECT t.*
                    FROM CHANGETABLE(CHANGES {table}, {last_version}) AS ct
                    JOIN {table} t
                    ON 1=1
                """
            cursor_mssql.execute(query)
            rows = cursor_mssql.fetchall()
            logger.info(
                f"從 MSSQL 獲取表 {table} 的增量數據，總計 {len(rows)} 筆記錄（從版本 {last_version} 到 {current_version}）"
            )

            successful_rows = 0
            total_rows_processed = 0
            for row in rows:
                total_rows_processed += 1
                try:
                    columns_list = column_names + ["updated_at"]
                    values = []
                    for col in column_names:
                        value = row[col]
                        col_data_type = next(
                            (
                                c["DATA_TYPE"].lower()
                                for c in columns
                                if c["COLUMN_NAME"] == col
                            ),
                            "text",
                        )
                        if value is None:
                            values.append(None)
                        elif isinstance(value, bytes):
                            if col_data_type in ("varbinary", "binary", "image"):
                                values.append(value)
                            else:
                                try:
                                    value = value.decode(
                                        "utf-16-le", errors="replace"
                                    ).replace("\x00", "")
                                except UnicodeDecodeError:
                                    value = value.decode(
                                        "cp950", errors="replace"
                                    ).replace("\x00", "")
                                values.append(value)
                        elif isinstance(value, str):
                            values.append(value.replace("\x00", ""))
                        else:
                            values.append(value)
                    values.append(timezone.now())

                    if assumed_primary_keys:
                        check_conditions = " AND ".join(
                            [f'"{pk}" = %s' for pk in valid_primary_keys]
                        )
                        check_values = [row[pk] for pk in valid_primary_keys]
                        cursor_postgres.execute(
                            f'SELECT "row_id" FROM "{table}" WHERE {check_conditions}',
                            check_values,
                        )
                        exists = cursor_postgres.fetchone()

                        if exists:
                            set_clause = ", ".join(
                                [f'"{col}" = %s' for col in column_names]
                            )
                            cursor_postgres.execute(
                                f"""
                                UPDATE "{table}"
                                SET {set_clause}, "updated_at" = %s
                                WHERE {check_conditions}
                                """,
                                values[:-1] + [timezone.now()] + check_values,
                            )
                            successful_rows += 1
                        else:
                            placeholders = ", ".join(["%s"] * len(columns_list))
                            insert_query = f"""
                                INSERT INTO "{table}" ({', '.join([f'"{col}"' for col in columns_list])})
                                VALUES ({placeholders})
                                RETURNING "row_id";
                            """
                            cursor_postgres.execute(insert_query, values)
                            if cursor_postgres.fetchone():
                                successful_rows += 1
                    else:
                        placeholders = ", ".join(["%s"] * len(columns_list))
                        insert_query = f"""
                            INSERT INTO "{table}" ({', '.join([f'"{col}"' for col in columns_list])})
                            VALUES ({placeholders})
                            RETURNING "row_id";
                        """
                        cursor_postgres.execute(insert_query, values)
                        if cursor_postgres.fetchone():
                            successful_rows += 1

                except Exception as e:
                    logger.warning(f"表 {table} 的某一行同步失敗：{str(e)}")
                    failed_rows.append(f"表 {table} 行數據：{row}")
                    conn_postgres.rollback()
                    cursor_postgres = conn_postgres.cursor()
                    continue

            conn_postgres.commit()
            logger.info(f"成功同步資料表 {table}，{successful_rows} 筆記錄")

        except Exception as e:
            failed_tables.append(table)
            logger.error(f"同步資料表 {table} 失敗：{str(e)}")
            ERPIntegrationOperationLog.objects.create(
                user=user_id,
                action=f"同步資料表 {table} 失敗：{str(e)[:900]}",
                timestamp=timezone.now(),
            )
            conn_postgres.rollback()
            continue

    return failed_tables, failed_rows


# 定義公司詳情視圖，用於新增或編輯公司設定
@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def company_detail(request, company_id=None):
    # 從 tables.json 文件載入允許同步的資料表清單，用於表單中的多選選項
    all_table_names = load_allowed_tables()

    # 根據是否提供 company_id 決定是新增還是編輯公司
    if company_id:
        # 如果有 company_id，則獲取現有公司資料，否則返回 404 錯誤
        company = get_object_or_404(CompanyConfig, id=company_id)
        logger.info(f"編輯公司資料：ID={company_id}, 公司名稱={company.company_name}")
    else:
        # 如果沒有 company_id，則創建一個新的公司物件（用於新增公司）
        company = CompanyConfig()
        logger.info("新增公司資料")

    # 預處理 sync_tables 欄位，將其從逗號分隔的字符串轉為列表，以便在模板中顯示已選中的資料表
    sync_tables_list = company.sync_tables.split(",") if company.sync_tables else []

    # 處理表單提交（POST 請求）
    if request.method == "POST":
        # 記錄表單提交的數據，方便日誌調試
        logger.info(f"表單提交數據：{request.POST}")

        # 從表單中獲取各欄位值，並去除首尾空白
        company.company_name = request.POST.get("company_name", "").strip()
        company.company_code = request.POST.get("company_code", "").strip()
        company.mssql_database = request.POST.get("mssql_database", "").strip()
        company.mes_database = request.POST.get("mes_database", "").strip()
        company.notes = request.POST.get("notes", "").strip()

        # 處理多選的 sync_tables 欄位，將選中的資料表名稱用逗號分隔存儲
        sync_tables = request.POST.getlist("sync_tables")
        company.sync_tables = ",".join(sync_tables) if sync_tables else ""
        logger.info(f"處理後的 sync_tables：{company.sync_tables}")

        # 檢查必填欄位是否為空，若為空則顯示錯誤訊息並重新渲染表單
        if not company.company_name:
            messages.error(request, "公司名稱為必填欄位！")
            return render(
                request,
                "erp_integration/company_detail.html",
                {
                    "company": company,
                    "all_table_names": all_table_names,
                    "sync_tables_list": sync_tables_list,
                },
            )
        if not company.company_code:
            messages.error(request, "公司編號為必填欄位！")
            return render(
                request,
                "erp_integration/company_detail.html",
                {
                    "company": company,
                    "all_table_names": all_table_names,
                    "sync_tables_list": sync_tables_list,
                },
            )
        if not company.mssql_database:
            messages.error(request, "MSSQL 資料庫名稱為必填欄位！")
            logger.warning(f"MSSQL 資料庫名稱為空，提交的表單數據：{request.POST}")
            return render(
                request,
                "erp_integration/company_detail.html",
                {
                    "company": company,
                    "all_table_names": all_table_names,
                    "sync_tables_list": sync_tables_list,
                },
            )
        if not company.mes_database:
            messages.error(request, "MES 資料庫名稱為必填欄位！")
            logger.warning(f"MES 資料庫名稱為空，提交的表單數據：{request.POST}")
            return render(
                request,
                "erp_integration/company_detail.html",
                {
                    "company": company,
                    "all_table_names": all_table_names,
                    "sync_tables_list": sync_tables_list,
                },
            )

        # 檢查並創建 PostgreSQL 資料庫（mes_database），如果尚未存在
        env = os.environ.copy()  # 複製環境變數
        env["PGPASSWORD"] = DATABASE_PASSWORD  # 設置環境變數以避免 psql 提示輸入密碼

        # 檢查 MES 資料庫名稱是否為有效的標識符（僅允許字母、數字和下劃線）
        if not company.mes_database.isidentifier():
            messages.error(request, "MES 資料庫名稱無效，僅允許字母、數字和下劃線！")
            return render(
                request,
                "erp_integration/company_detail.html",
                {
                    "company": company,
                    "all_table_names": all_table_names,
                    "sync_tables_list": sync_tables_list,
                },
            )

        # 檢查 PostgreSQL 中是否已存在該資料庫（考慮大小寫敏感和非敏感的情況）
        check_db_cmd = (
            f"psql -U {DATABASE_USER} -h {DATABASE_HOST} -p {DATABASE_PORT} -d postgres -t -A -c "
            f"\"SELECT datname FROM pg_database WHERE datname = '{company.mes_database.lower()}' OR datname = '{company.mes_database}';\""
        )
        result = subprocess.run(
            check_db_cmd, shell=True, capture_output=True, text=True, env=env
        )
        db_exists = bool(result.stdout.strip())  # 檢查是否存在資料庫

        # 如果資料庫不存在，則創建新資料庫並設置權限
        if not db_exists:
            try:
                # 創建資料庫的命令
                create_db_cmd = (
                    f"psql -U {DATABASE_USER} -h {DATABASE_HOST} -p {DATABASE_PORT} -d postgres "
                    f"-c 'CREATE DATABASE \"{company.mes_database}\";'"
                )
                result = subprocess.run(
                    create_db_cmd, shell=True, capture_output=True, text=True, env=env
                )
                if result.returncode != 0:
                    # 如果創建失敗，記錄錯誤並顯示訊息
                    error_msg = (
                        f"無法創建資料庫 {company.mes_database}：{result.stderr}"
                    )
                    messages.error(request, error_msg)
                    logger.error(error_msg)
                    ERPIntegrationOperationLog.objects.create(
                        user=request.user.username,
                        action=f"創建資料庫失敗：{error_msg[:900]}",
                        timestamp=timezone.now(),
                    )
                    return render(
                        request,
                        "erp_integration/company_detail.html",
                        {
                            "company": company,
                            "all_table_names": all_table_names,
                            "sync_tables_list": sync_tables_list,
                        },
                    )

                # 授予資料庫權限給指定用戶
                grant_cmd = (
                    f"psql -U {DATABASE_USER} -h {DATABASE_HOST} -p {DATABASE_PORT} -d postgres "
                    f"-c 'GRANT ALL PRIVILEGES ON DATABASE \"{company.mes_database}\" TO {DATABASE_USER};'"
                )
                grant_result = subprocess.run(
                    grant_cmd, shell=True, capture_output=True, text=True, env=env
                )
                if grant_result.returncode != 0:
                    # 如果設置權限失敗，記錄錯誤並顯示訊息
                    error_msg = f"無法設置資料庫權限 {company.mes_database}：{grant_result.stderr}"
                    messages.error(request, error_msg)
                    logger.error(error_msg)
                    ERPIntegrationOperationLog.objects.create(
                        user=request.user.username,
                        action=f"設置資料庫權限失敗：{error_msg[:900]}",
                        timestamp=timezone.now(),
                    )
                    return render(
                        request,
                        "erp_integration/company_detail.html",
                        {
                            "company": company,
                            "all_table_names": all_table_names,
                            "sync_tables_list": sync_tables_list,
                        },
                    )

                # 資料庫創建成功，顯示成功訊息並記錄操作日誌
                messages.info(
                    request, f"已成功創建 PostgreSQL 資料庫：{company.mes_database}"
                )
                ERPIntegrationOperationLog.objects.create(
                    user=request.user.username,
                    action=f"成功創建 PostgreSQL 資料庫：{company.mes_database}",
                    timestamp=timezone.now(),
                )
                logger.info(f"成功創建 PostgreSQL 資料庫：{company.mes_database}")

            except Exception as e:
                # 捕獲創建資料庫過程中可能發生的異常
                error_msg = f"創建資料庫 {company.mes_database} 時發生錯誤：{str(e)}"
                messages.error(request, error_msg)
                logger.error(error_msg)
                ERPIntegrationOperationLog.objects.create(
                    user=request.user.username,
                    action=f"創建資料庫失敗：{error_msg[:900]}",
                    timestamp=timezone.now(),
                )
                return render(
                    request,
                    "erp_integration/company_detail.html",
                    {
                        "company": company,
                        "all_table_names": all_table_names,
                        "sync_tables_list": sync_tables_list,
                    },
                )

        # 保存公司資料到資料庫
        try:
            with transaction.atomic():  # 使用事務確保資料一致性
                company.save()
                logger.info(
                    f"用戶 {request.user.username} 成功保存公司資料：{company.company_name} (ID: {company.id})"
                )
        except Exception as e:
            # 如果保存失敗，記錄錯誤並顯示訊息
            error_msg = str(e)
            logger.error(f"保存公司資料失敗：{error_msg}")
            messages.error(request, f"保存公司資料失敗：{error_msg}")
            ERPIntegrationOperationLog.objects.create(
                user=request.user.username,
                action=f"保存公司資料失敗：{error_msg[:900]}",
                timestamp=timezone.now(),
            )
            return render(
                request,
                "erp_integration/company_detail.html",
                {
                    "company": company,
                    "all_table_names": all_table_names,
                    "sync_tables_list": sync_tables_list,
                },
            )

        # 驗證 MSSQL 資料庫連線是否有效
        config = ERPConfig.objects.first()
        if not config:
            messages.error(request, "請先配置 ERP 連線設定！")
            return redirect("erp_integration:config")

        if config.server and company.mssql_database:
            try:
                # 嘗試連接到 MSSQL 資料庫以驗證連線
                conn = pymssql.connect(
                    server=config.server,
                    user=config.username,
                    password=config.password,
                    database=company.mssql_database,
                    timeout=30,
                    tds_version="7.0",
                )
                cursor = conn.cursor()
                cursor.execute("SELECT 1")  # 簡單查詢以測試連線
                cursor.close()
                conn.close()
                messages.success(request, "公司資料已保存！")
            except Exception as e:
                # 如果連線失敗，記錄錯誤並顯示訊息
                error_msg = str(e) if str(e) else "未知錯誤"
                messages.error(
                    request,
                    f"MSSQL 資料庫驗證失敗：{error_msg}\n連線參數：服務器={config.server}, 使用者={config.username}, 資料庫={company.mssql_database}",
                )
                ERPIntegrationOperationLog.objects.create(
                    user=request.user.username,
                    action=f"MSSQL 資料庫驗證失敗（資料庫：{company.mssql_database}）：{error_msg[:900]}\n連線參數：服務器={config.server}, 使用者={config.username}, 資料庫={company.mssql_database}",
                    timestamp=timezone.now(),
                )
                logger.error(f"資料庫驗證失敗詳細日誌：{error_msg}")
                return render(
                    request,
                    "erp_integration/company_detail.html",
                    {
                        "company": company,
                        "all_table_names": all_table_names,
                        "sync_tables_list": sync_tables_list,
                    },
                )
        else:
            # 如果 ERP 連線設定不完整，提示用戶先完成設定
            messages.error(request, "請先配置完整的 ERP 連線設定（服務器地址）！")
            return redirect("erp_integration:config")

        # 保存成功後記錄操作日誌並重定向到公司設定頁面
        ERPIntegrationOperationLog.objects.create(
            user=request.user.username,
            action=f"更新公司資料 - {company.company_name}",
            timestamp=timezone.now(),
        )
        return redirect("erp_integration:company_config")

    # 記錄查看公司詳情的操作日誌
    ERPIntegrationOperationLog.objects.create(
        user=request.user.username, action="查看公司資料", timestamp=timezone.now()
    )
    # 渲染公司詳情頁面，傳遞公司資料和資料表清單
    return render(
        request,
        "erp_integration/company_detail.html",
        {
            "company": company,
            "all_table_names": all_table_names,
            "sync_tables_list": sync_tables_list,
        },
    )


# 定義刪除公司視圖，用於刪除公司及其關聯的 PostgreSQL 資料庫
@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def delete_company(request, company_id):
    """刪除公司及其關聯的 PostgreSQL 資料庫"""
    # 確保請求方法為 POST，防止誤操作
    if request.method != "POST":
        messages.error(request, "無效的請求方法！")
        return redirect("erp_integration:company_config")

    # 根據公司 ID 獲取公司物件，若不存在則返回 404
    company = get_object_or_404(CompanyConfig, id=company_id)
    mes_database = company.mes_database  # 獲取公司的 MES 資料庫名稱

    # 設置環境變數以避免 psql 提示輸入密碼
    env = os.environ.copy()
    env["PGPASSWORD"] = DATABASE_PASSWORD

    # 檢查資料庫是否存在，並考慮大小寫敏感和非敏感的情況
    if mes_database:
        try:
            # 列出 PostgreSQL 中的所有資料庫名稱
            list_db_cmd = (
                f"psql -U {DATABASE_USER} -h {DATABASE_HOST} -p {DATABASE_PORT} -d postgres -t -A -c "
                f'"SELECT datname FROM pg_database;"'
            )
            result = subprocess.run(
                list_db_cmd, shell=True, capture_output=True, text=True, env=env
            )
            if result.returncode != 0:
                # 如果無法列出資料庫，記錄錯誤並繼續
                logger.error(f"無法列出資料庫：{result.stderr}")
                ERPIntegrationOperationLog.objects.create(
                    user=request.user.username,
                    action=f"無法列出資料庫：{result.stderr[:900]}",
                    timestamp=timezone.now(),
                )
            else:
                # 檢查資料庫是否存在（匹配原始名稱或小寫名稱）
                databases = result.stdout.strip().split("\n")
                db_name_to_drop = None
                if mes_database in databases:
                    db_name_to_drop = mes_database
                elif mes_database.lower() in databases:
                    db_name_to_drop = mes_database.lower()

                if db_name_to_drop:
                    # 終止資料庫的活躍連線，以允許刪除
                    terminate_cmd = (
                        f"psql -U {DATABASE_USER} -h {DATABASE_HOST} -p {DATABASE_PORT} -d postgres "
                        f'-c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity '
                        f"WHERE pg_stat_activity.datname = '{db_name_to_drop}' AND pid <> pg_backend_pid();\""
                    )
                    terminate_result = subprocess.run(
                        terminate_cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        env=env,
                    )
                    if terminate_result.returncode != 0:
                        # 如果終止連線失敗，記錄警告但繼續執行
                        logger.error(
                            f"無法終止資料庫 {db_name_to_drop} 的連線：{terminate_result.stderr}"
                        )

                    # 刪除資料庫
                    drop_db_cmd = (
                        f"psql -U {DATABASE_USER} -h {DATABASE_HOST} -p {DATABASE_PORT} -d postgres "
                        f"-c 'DROP DATABASE \"{db_name_to_drop}\" WITH (FORCE);'"
                    )
                    drop_result = subprocess.run(
                        drop_db_cmd, shell=True, capture_output=True, text=True, env=env
                    )
                    if drop_result.returncode != 0:
                        # 如果刪除資料庫失敗，記錄錯誤並顯示警告
                        error_msg = (
                            f"無法刪除資料庫 {db_name_to_drop}：{drop_result.stderr}"
                        )
                        messages.warning(request, error_msg)
                        logger.error(error_msg)
                        ERPIntegrationOperationLog.objects.create(
                            user=request.user.username,
                            action=f"刪除資料庫失敗：{error_msg[:900]}",
                            timestamp=timezone.now(),
                        )
                    else:
                        # 資料庫刪除成功，記錄操作日誌
                        logger.info(f"成功刪除 PostgreSQL 資料庫：{db_name_to_drop}")
                        ERPIntegrationOperationLog.objects.create(
                            user=request.user.username,
                            action=f"成功刪除 PostgreSQL 資料庫：{db_name_to_drop}",
                            timestamp=timezone.now(),
                        )
                else:
                    # 如果資料庫不存在，記錄資訊並跳過刪除
                    logger.info(f"資料庫 {mes_database} 不存在，跳過刪除")
                    ERPIntegrationOperationLog.objects.create(
                        user=request.user.username,
                        action=f"資料庫 {mes_database} 不存在，跳過刪除",
                        timestamp=timezone.now(),
                    )

        except Exception as e:
            # 捕獲刪除資料庫過程中可能發生的異常
            error_msg = f"刪除資料庫 {mes_database} 時發生錯誤：{str(e)}"
            messages.warning(request, error_msg)
            logger.error(error_msg)
            ERPIntegrationOperationLog.objects.create(
                user=request.user.username,
                action=f"刪除資料庫失敗：{error_msg[:900]}",
                timestamp=timezone.now(),
            )

    # 刪除公司記錄
    try:
        with transaction.atomic():  # 使用事務確保資料一致性
            company_name = company.company_name  # 記錄公司名稱以用於日誌
            company.delete()  # 刪除公司記錄
            messages.success(request, f"公司 {company_name} 已成功刪除！")
            ERPIntegrationOperationLog.objects.create(
                user=request.user.username,
                action=f"刪除公司 - {company_name}",
                timestamp=timezone.now(),
            )
    except Exception as e:
        # 如果刪除公司記錄失敗，記錄錯誤並顯示訊息
        error_msg = f"刪除公司失敗：{str(e)}"
        messages.error(request, error_msg)
        logger.error(error_msg)
        ERPIntegrationOperationLog.objects.create(
            user=request.user.username,
            action=f"刪除公司失敗：{error_msg[:900]}",
            timestamp=timezone.now(),
        )

    # 重定向到公司設定頁面
    return redirect("erp_integration:company_config")


# 定義資料表搜尋視圖，用於在 MSSQL 或 PostgreSQL 資料庫中搜尋特定字串（自動搜尋）
@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def table_search(request):
    # 從表單中獲取搜尋參數，若為 GET 請求則設置為空值或預設值
    search_strings = (
        request.POST.get("search_strings", "") if request.method == "POST" else ""
    )  # 搜尋字串
    search_condition = (
        request.POST.get("search_condition", "OR") if request.method == "POST" else "OR"
    )  # 搜尋條件（AND/OR）
    selected_company_code = (
        request.POST.get("company_code", "") if request.method == "POST" else ""
    )  # 選擇的公司代碼
    selected_table = (
        request.POST.get("selected_table", "") if request.method == "POST" else ""
    )  # 選擇的特定資料表
    table_select = (
        request.POST.getlist("table_select") if request.method == "POST" else []
    )  # 從下拉框選擇的資料表
    order_direction = request.GET.get("order_direction", "")  # 排序方向
    search_target = (
        request.POST.get("search_target", "erp") if request.method == "POST" else "erp"
    )  # 搜尋目標（ERP 或 MES）

    # 獲取所有公司設定和允許的資料表清單
    companies = CompanyConfig.objects.all()  # 獲取所有公司設定
    all_table_names = load_allowed_tables()  # 從 tables.json 載入允許的資料表清單
    error_message = None  # 初始化錯誤訊息變數

    # 檢查是否選擇了公司，並驗證相關設定
    if selected_company_code:
        company = CompanyConfig.objects.filter(
            company_code=selected_company_code
        ).first()
        if company:
            config = ERPConfig.objects.first()
            if not config:
                error_message = "ERP 連線設定不存在！請先完成設定。"
                messages.error(request, error_message)
                ERPIntegrationOperationLog.objects.create(
                    user=request.user.username,
                    action="ERP 連線設定不存在，無法獲取資料表清單",
                    timestamp=timezone.now(),
                )
            elif not config.server or not config.username or not config.password:
                error_message = (
                    "ERP 連線設定不完整（缺少服務器、使用者名稱或密碼）！請先完成設定。"
                )
                messages.error(request, error_message)
                ERPIntegrationOperationLog.objects.create(
                    user=request.user.username,
                    action="ERP 連線設定不完整（缺少服務器、使用者名稱或密碼），無法獲取資料表清單",
                    timestamp=timezone.now(),
                )
            elif not company.mssql_database:
                error_message = f"公司 {company.company_name} 未設定 MSSQL 資料庫名稱！"
                messages.error(request, error_message)
                ERPIntegrationOperationLog.objects.create(
                    user=request.user.username,
                    action=f"公司 {company.company_name} 未設定 MSSQL 資料庫名稱，無法獲取資料表清單",
                    timestamp=timezone.now(),
                )
            elif not company.mes_database and search_target == "mes":
                error_message = f"公司 {company.company_name} 未設定 MES 資料庫名稱！"
                messages.error(request, error_message)
                ERPIntegrationOperationLog.objects.create(
                    user=request.user.username,
                    action=f"公司 {company.company_name} 未設定 MES 資料庫名稱，無法搜尋本機 MES 資料庫",
                    timestamp=timezone.now(),
                )
            else:
                if not all_table_names:
                    error_message = "資料表清單為空，請檢查配置文件！"
                    messages.warning(request, error_message)
                    ERPIntegrationOperationLog.objects.create(
                        user=request.user.username,
                        action="資料表清單為空",
                        timestamp=timezone.now(),
                    )
                else:
                    logger.info(
                        f"從配置文件載入資料表清單，總計 {len(all_table_names)} 個表：{all_table_names[:10]}..."
                    )

    # 如果是 GET 請求，渲染搜尋頁面
    if request.method != "POST":
        ERPIntegrationOperationLog.objects.create(
            user=request.user.username,
            action="訪問資料表搜尋頁面",
            timestamp=timezone.now(),
        )
        return render(
            request,
            "erp_integration/table_search.html",
            {
                "companies": companies,
                "search_strings": search_strings,
                "search_condition": search_condition,
                "selected_company_code": selected_company_code,
                "order_direction": order_direction,
                "all_table_names": all_table_names,
                "error_message": error_message,
                "search_target": search_target,
            },
        )

    # 處理 POST 請求（執行自動搜尋）
    company_code = request.POST.get("company_code")
    search_strings = request.POST.get("search_strings", "").strip()
    search_condition = request.POST.get("search_condition", "OR")
    selected_table = request.POST.get("selected_table", "").strip()
    table_select = request.POST.getlist("table_select")  # 從下拉框獲取選擇的資料表
    matched_tables = (
        request.POST.get("matched_tables", "").split(",")
        if request.POST.get("matched_tables")
        else []
    )  # 從表單獲取 matched_tables
    search_target = request.POST.get("search_target", "erp")

    # 檢查必填欄位：公司代碼
    if not company_code:
        messages.error(request, "請選擇公司！")
        return render(
            request,
            "erp_integration/table_search.html",
            {
                "companies": companies,
                "search_strings": search_strings,
                "search_condition": search_condition,
                "selected_company_code": selected_company_code,
                "order_direction": order_direction,
                "all_table_names": all_table_names,
                "error_message": "請選擇公司！",
                "search_target": search_target,
            },
        )

    # 檢查必填欄位：搜尋字串
    if not search_strings:
        messages.error(request, "請輸入搜尋字串！")
        return render(
            request,
            "erp_integration/table_search.html",
            {
                "companies": companies,
                "search_strings": search_strings,
                "search_condition": search_condition,
                "selected_company_code": selected_company_code,
                "order_direction": order_direction,
                "all_table_names": all_table_names,
                "error_message": "請輸入搜尋字串！",
                "search_target": search_target,
            },
        )

    # 如果未選擇特定資料表，也未從下拉框選擇資料表，則搜尋所有資料表
    if not selected_table and not table_select:
        table_names_list = all_table_names  # 自動搜尋所有資料表
    else:
        # 優先使用下拉框選擇的資料表
        if table_select:
            table_names_list = table_select
        else:
            table_names_list = []

    # 獲取公司物件並檢查 ERP 連線設定
    company = get_object_or_404(CompanyConfig, company_code=company_code)
    config = ERPConfig.objects.first()
    if not config or not config.server or not company.mssql_database:
        messages.error(request, "ERP 連線設定不完整！請先完成設定。")
        return redirect("erp_integration:config")

    # 處理搜尋字串和資料表名稱，轉為列表形式
    search_strings_list = [
        s.strip() for s in search_strings.split(",")
    ]  # 將搜尋字串分割為列表
    logger.info(f"解析出的資料表名稱列表：{table_names_list}")
    results = []  # 儲存搜尋結果
    matched_tables_list = matched_tables  # 保留原始的 matched_tables 列表
    failed_tables = []  # 儲存搜尋失敗的資料表
    failed_reasons = {}  # 儲存失敗原因

    # 根據搜尋目標（ERP 或 MES）執行搜尋
    if search_target == "erp":
        # 搜尋遠端 ERP 資料庫（MSSQL）
        conn = None
        try:
            # 定義連線函數，方便後續重試
            def connect_to_db():
                return pymssql.connect(
                    server=config.server,
                    user=config.username,
                    password=config.password,
                    database=company.mssql_database,
                    timeout=30,
                    tds_version="7.0",
                )

            conn = connect_to_db()  # 建立 MSSQL 連線
            cursor = conn.cursor()  # 創建 MSSQL 游標

            all_tables = all_table_names  # 獲取所有允許的資料表
            if not all_tables:
                # 如果資料表清單為空，顯示警告並返回
                messages.warning(request, "資料表清單為空，請檢查配置文件！")
                ERPIntegrationOperationLog.objects.create(
                    user=request.user.username,
                    action="資料表清單為空",
                    timestamp=timezone.now(),
                )
                return render(
                    request,
                    "erp_integration/table_search.html",
                    {
                        "companies": companies,
                        "search_strings": search_strings,
                        "search_condition": search_condition,
                        "selected_company_code": selected_company_code,
                        "order_direction": order_direction,
                        "all_table_names": all_table_names,
                        "error_message": "資料表清單為空，請檢查配置文件！",
                        "search_target": search_target,
                    },
                )

            # 如果指定了資料表名稱，則過濾出匹配的資料表
            if table_names_list:
                tables = []
                all_tables_lower = [t.lower() for t in all_tables]
                for t in table_names_list:
                    if t.lower() in all_tables_lower:
                        index = all_tables_lower.index(t.lower())
                        tables.append(all_tables[index])
                logger.info(f"匹配到的資料表：{tables}")
                if not tables:
                    messages.warning(request, "未找到指定的資料表！")
                    return render(
                        request,
                        "erp_integration/table_search.html",
                        {
                            "companies": companies,
                            "search_strings": search_strings,
                            "search_condition": search_condition,
                            "selected_company_code": selected_company_code,
                            "order_direction": order_direction,
                            "all_table_names": all_table_names,
                            "error_message": "未找到指定的資料表！",
                            "search_target": search_target,
                        },
                    )
            else:
                tables = all_tables  # 如果未指定資料表，則搜尋所有允許的資料表

            # 如果選擇了特定資料表，則只搜尋該表
            if selected_table:
                selected_table_lower = selected_table.lower()
                all_tables_lower = [t.lower() for t in all_tables]
                if selected_table_lower in all_tables_lower:
                    index = all_tables_lower.index(selected_table_lower)
                    tables = [all_tables[index]]
                else:
                    tables = []
                results = []  # 重置搜尋結果
            else:
                matched_tables_list = []

            # 逐一搜尋每個資料表
            for table in tables:
                logger.info(f"開始搜尋表（遠端 ERP 資料庫）：{table}")
                try:
                    # 獲取資料表的欄位資訊
                    cursor.execute(
                        """
                        SELECT COLUMN_NAME, DATA_TYPE
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_NAME = %s
                    """,
                        (table,),
                    )
                    columns = cursor.fetchall()

                    # 僅搜尋字符串類型的欄位（varchar, nvarchar, char, nchar）
                    searchable_columns = [
                        col[0]
                        for col in columns
                        if col[1] in ("varchar", "nvarchar", "char", "nchar")
                    ]

                    if not searchable_columns:
                        logger.info(
                            f"表 {table} 沒有可搜尋的欄位（只允許 varchar, nvarchar, char, nchar），跳過"
                        )
                        continue

                    # 構建搜尋條件
                    conditions = []
                    params = []
                    for search_str in search_strings_list:
                        if search_condition == "AND":
                            # 如果條件為 AND，則每個搜尋字串必須在至少一個欄位中匹配
                            table_conditions = [
                                f"CAST([{col}] AS NVARCHAR(MAX)) LIKE %s"
                                for col in searchable_columns
                            ]
                            if table_conditions:
                                conditions.append(
                                    "(" + " OR ".join(table_conditions) + ")"
                                )
                                params.extend(
                                    [f"%{search_str}%"] * len(searchable_columns)
                                )
                        else:
                            # 如果條件為 OR，則每個搜尋字串在每個欄位中檢查
                            for col in searchable_columns:
                                conditions.append(
                                    f"CAST([{col}] AS NVARCHAR(MAX)) LIKE %s"
                                )
                                params.append(f"%{search_str}%")

                    if not conditions:
                        logger.info(f"表 {table} 沒有有效的搜尋條件，跳過")
                        continue

                    # 構建 WHERE 條件語句
                    where_clause = (
                        " AND ".join(conditions)
                        if search_condition == "AND"
                        else " OR ".join(conditions)
                    )

                    # 構建查詢語句，限制最多返回 10 筆記錄
                    query = f"""
                        SELECT TOP 10 *
                        FROM {table}
                        WHERE {where_clause}
                    """
                    logger.debug(
                        f"執行查詢（遠端 ERP 資料庫）：{query}，參數：{params}"
                    )
                    cursor.execute(query, params)

                    # 逐行處理查詢結果
                    column_names = [col[0] for col in columns]  # 獲取欄位名稱
                    rows = []
                    while True:
                        try:
                            raw_row = cursor.fetchone()  # 逐行讀取資料
                            if raw_row is None:
                                break
                            row_dict = {}
                            for idx, value in enumerate(raw_row):
                                col_name = column_names[idx]
                                if isinstance(value, bytes):
                                    try:
                                        # 假設 MSSQL varchar 字段使用 CP950 編碼，進行解碼
                                        row_dict[col_name] = value.decode(
                                            "cp950", errors="replace"
                                        )
                                    except (
                                        UnicodeEncodeError,
                                        UnicodeDecodeError,
                                    ) as e:
                                        row_dict[col_name] = ""
                                        logger.warning(
                                            f"表 {table} 的欄位 {col_name} 包含無法解碼的字元（假設 CP950），已設為空白：{value}"
                                        )
                                elif isinstance(value, str):
                                    # 確保字符串是有效的 UTF-8 編碼
                                    try:
                                        row_dict[col_name] = value.encode(
                                            "utf-8"
                                        ).decode("utf-8")
                                    except (
                                        UnicodeEncodeError,
                                        UnicodeDecodeError,
                                    ) as e:
                                        # 如果不是有效的 UTF-8，假設為 CP950 並嘗試轉換
                                        try:
                                            row_dict[col_name] = value.encode(
                                                "latin1"
                                            ).decode("cp950", errors="replace")
                                        except (
                                            UnicodeEncodeError,
                                            UnicodeDecodeError,
                                        ) as e2:
                                            row_dict[col_name] = ""
                                            logger.warning(
                                                f"表 {table} 的欄位 {col_name} 包含無法解碼的字串（假設 CP950），已設為空白：{value}"
                                            )
                                else:
                                    row_dict[col_name] = value  # 其他類型直接存儲
                            rows.append(row_dict)
                        except (UnicodeEncodeError, UnicodeDecodeError) as e:
                            logger.warning(
                                f"表 {table} 的某一行包含無法解碼的字元，已跳過該行：{str(e)}"
                            )
                            continue

                    if rows:
                        if selected_table:
                            # 如果選擇了特定資料表，處理搜尋結果並存儲
                            processed_rows = []
                            for row in rows:
                                processed_row = [
                                    row.get(col_name, None) for col_name in column_names
                                ]
                                processed_rows.append(processed_row)

                            results.append(
                                {
                                    "table_name": table,
                                    "rows": processed_rows,
                                    "column_names": column_names,
                                    "source": "遠端 ERP 資料庫",
                                }
                            )
                            logger.info(
                                f"表 {table} 找到 {len(processed_rows)} 筆記錄（遠端 ERP 資料庫）"
                            )
                        else:
                            # 如果未選擇特定資料表，僅記錄匹配的資料表名稱
                            if table:  # 確保 table 不為空
                                matched_tables_list.append(table)
                                logger.info(
                                    f"表 {table} 包含匹配記錄（遠端 ERP 資料庫）"
                                )

                except Exception as e:
                    # 捕獲搜尋過程中可能發生的異常
                    error_msg = str(e) if str(e) else "未知錯誤"
                    failed_tables.append(table)  # 記錄失敗的資料表
                    failed_reasons[table] = error_msg  # 記錄失敗原因
                    logger.error(
                        f"搜尋表 {table} 時發生錯誤（遠端 ERP 資料庫）：{error_msg}\n堆疊資訊：{traceback.format_exc()}"
                    )
                    ERPIntegrationOperationLog.objects.create(
                        user=request.user.username,
                        action=f"搜尋字串失敗（表：{table}，遠端 ERP 資料庫）：{error_msg[:900]}",
                        timestamp=timezone.now(),
                    )

                    try:
                        # 嘗試重新連線以繼續處理其他資料表
                        cursor.close()
                        conn.close()
                        conn = connect_to_db()
                        cursor = conn.cursor()
                        logger.info(f"重新連接到遠端 ERP 資料庫成功")
                    except Exception as reconnect_err:
                        logger.error(f"重新連接到遠端 ERP 資料庫失敗：{reconnect_err}")
                        break

            if conn:
                cursor.close()
                conn.close()  # 關閉連線

        except Exception as e:
            # 捕獲連線或搜尋過程中可能發生的異常
            error_msg = str(e) if str(e) else "未知錯誤"
            messages.error(
                request,
                f"搜尋失敗（遠端 ERP 資料庫）：{error_msg}\n連線參數：服務器={config.server}, 使用者={config.username}, 資料庫={company.mssql_database}",
            )
            ERPIntegrationOperationLog.objects.create(
                user=request.user.username,
                action=f"搜尋失敗（遠端 ERP 資料庫）：{error_msg[:900]}\n連線參數：服務器={config.server}, 使用者={config.username}, 資料庫={company.mssql_database}",
                timestamp=timezone.now(),
            )
            logger.error(
                f"搜尋失敗詳細日誌（遠端 ERP 資料庫）：{error_msg}\n堆疊資訊：{traceback.format_exc()}"
            )
            if conn:
                conn.close()
            return render(
                request,
                "erp_integration/table_search.html",
                {
                    "companies": companies,
                    "search_strings": search_strings,
                    "search_condition": search_condition,
                    "selected_company_code": selected_company_code,
                    "order_direction": order_direction,
                    "all_table_names": all_table_names,
                    "error_message": f"搜尋失敗（遠端 ERP 資料庫）：{error_msg}",
                    "search_target": search_target,
                },
            )

    elif search_target == "mes":
        # 搜尋本機 MES 資料庫（PostgreSQL）
        conn = None
        try:
            # 連接到 PostgreSQL 資料庫
            conn = psycopg2.connect(
                dbname=company.mes_database,
                user=DATABASE_USER,
                password=DATABASE_PASSWORD,
                host=DATABASE_HOST,
                port=DATABASE_PORT,
            )
            cursor = conn.cursor()

            all_tables = all_table_names
            if not all_tables:
                # 如果資料表清單為空，顯示警告並返回
                messages.warning(request, "資料表清單為空，請檢查配置文件！")
                ERPIntegrationOperationLog.objects.create(
                    user=request.user.username,
                    action="資料表清單為空",
                    timestamp=timezone.now(),
                )
                return render(
                    request,
                    "erp_integration/table_search.html",
                    {
                        "companies": companies,
                        "search_strings": search_strings,
                        "search_condition": search_condition,
                        "selected_company_code": selected_company_code,
                        "order_direction": order_direction,
                        "all_table_names": all_table_names,
                        "error_message": "資料表清單為空，請檢查配置文件！",
                        "search_target": search_target,
                    },
                )

            # 如果指定了資料表名稱，則過濾出匹配的資料表
            if table_names_list:
                tables = []
                all_tables_lower = [t.lower() for t in all_tables]
                for t in table_names_list:
                    if t.lower() in all_tables_lower:
                        index = all_tables_lower.index(t.lower())
                        tables.append(all_tables[index])
                logger.info(f"匹配到的資料表（本機 MES 資料庫）：{tables}")
                if not tables:
                    messages.warning(request, "未找到指定的資料表！")
                    return render(
                        request,
                        "erp_integration/table_search.html",
                        {
                            "companies": companies,
                            "search_strings": search_strings,
                            "search_condition": search_condition,
                            "selected_company_code": selected_company_code,
                            "order_direction": order_direction,
                            "all_table_names": all_table_names,
                            "error_message": "未找到指定的資料表！",
                            "search_target": search_target,
                        },
                    )
            else:
                tables = all_tables

            # 如果選擇了特定資料表，則只搜尋該表
            if selected_table:
                selected_table_lower = selected_table.lower()
                all_tables_lower = [t.lower() for t in all_tables]
                if selected_table_lower in all_tables_lower:
                    index = all_tables_lower.index(selected_table_lower)
                    tables = [all_tables[index]]
                else:
                    tables = []
                results = []
            else:
                matched_tables_list = []

            # 逐一搜尋每個資料表
            for table in tables:
                logger.info(f"開始搜尋表（本機 MES 資料庫）：{table}")
                try:
                    # 檢查表是否存在
                    cursor.execute(
                        """
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = %s
                        );
                    """,
                        (table,),
                    )
                    table_exists = cursor.fetchone()[0]

                    if not table_exists:
                        logger.info(f"表 {table} 在本機 MES 資料庫中不存在，跳過")
                        continue

                    # 獲取表的欄位資訊
                    cursor.execute(
                        """
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                        AND table_name = %s
                    """,
                        (table,),
                    )
                    columns = cursor.fetchall()

                    # 僅搜尋字符串類型的欄位（varchar, char, text, character varying）
                    searchable_columns = [
                        col[0]
                        for col in columns
                        if col[1].lower()
                        in ("varchar", "char", "text", "character varying")
                    ]

                    if not searchable_columns:
                        logger.info(
                            f"表 {table} 沒有可搜尋的欄位（只允許 varchar, char, text, character varying），跳過"
                        )
                        continue

                    # 構建搜尋條件，使用 ILIKE 忽略大小寫
                    conditions = []
                    params = []
                    for search_str in search_strings_list:
                        if search_condition == "AND":
                            table_conditions = [
                                f'CAST("{col}" AS TEXT) ILIKE %s'
                                for col in searchable_columns
                            ]
                            if table_conditions:
                                conditions.append(
                                    "(" + " OR ".join(table_conditions) + ")"
                                )
                                params.extend(
                                    [f"%{search_str}%"] * len(searchable_columns)
                                )
                        else:
                            for col in searchable_columns:
                                conditions.append(f'CAST("{col}" AS TEXT) ILIKE %s')
                                params.append(f"%{search_str}%")

                    if not conditions:
                        logger.info(f"表 {table} 沒有有效的搜尋條件，跳過")
                        continue

                    # 構建 WHERE 條件語句
                    where_clause = (
                        " AND ".join(conditions)
                        if search_condition == "AND"
                        else " OR ".join(conditions)
                    )

                    # 構建查詢語句，限制最多返回 10 筆記錄
                    query = f"""
                        SELECT *
                        FROM "{table}"
                        WHERE {where_clause}
                        LIMIT 10
                    """
                    logger.debug(
                        f"執行查詢（本機 MES 資料庫）：{query}，參數：{params}"
                    )
                    cursor.execute(query, params)

                    # 逐行處理查詢結果
                    column_names = [col[0] for col in columns]
                    rows = []
                    while True:
                        raw_row = cursor.fetchone()
                        if raw_row is None:
                            break
                        row_dict = {}
                        for idx, value in enumerate(raw_row):
                            col_name = column_names[idx]
                            row_dict[col_name] = value
                        rows.append(row_dict)

                    if rows:
                        if selected_table:
                            # 如果選擇了特定資料表，處理搜尋結果並存儲
                            processed_rows = []
                            for row in rows:
                                processed_row = [
                                    row.get(col_name, None) for col_name in column_names
                                ]
                                processed_rows.append(processed_row)

                            results.append(
                                {
                                    "table_name": table,
                                    "rows": processed_rows,
                                    "column_names": column_names,
                                    "source": "本機 MES 資料庫",
                                }
                            )
                            logger.info(
                                f"表 {table} 找到 {len(processed_rows)} 筆記錄（本機 MES 資料庫）"
                            )
                        else:
                            # 如果未選擇特定資料表，僅記錄匹配的資料表名稱
                            if table:  # 確保 table 不為空
                                matched_tables_list.append(table)
                                logger.info(
                                    f"表 {table} 包含匹配記錄（本機 MES 資料庫）"
                                )

                except Exception as e:
                    # 捕獲搜尋過程中可能發生的異常
                    error_msg = str(e) if str(e) else "未知錯誤"
                    failed_tables.append(table)
                    failed_reasons[table] = error_msg
                    logger.error(
                        f"搜尋表 {table} 時發生錯誤（本機 MES 資料庫）：{error_msg}\n堆疊資訊：{traceback.format_exc()}"
                    )
                    ERPIntegrationOperationLog.objects.create(
                        user=request.user.username,
                        action=f"搜尋字串失敗（表：{table}，本機 MES 資料庫）：{error_msg[:900]}",
                        timestamp=timezone.now(),
                    )

                    try:
                        # 嘗試重新連線以繼續處理其他資料表
                        cursor.close()
                        conn.close()
                        conn = psycopg2.connect(
                            dbname=company.mes_database,
                            user=DATABASE_USER,
                            password=DATABASE_PASSWORD,
                            host=DATABASE_HOST,
                            port=DATABASE_PORT,
                        )
                        cursor = conn.cursor()
                        logger.info(f"重新連接到本機 MES 資料庫成功")
                    except Exception as reconnect_err:
                        logger.error(f"重新連接到本機 MES 資料庫失敗：{reconnect_err}")
                        break

            if conn:
                cursor.close()
                conn.close()  # 關閉連線

        except Exception as e:
            # 捕獲連線或搜尋過程中可能發生的異常
            error_msg = str(e) if str(e) else "未知錯誤"
            messages.error(request, f"搜尋失敗（本機 MES 資料庫）：{error_msg}")
            ERPIntegrationOperationLog.objects.create(
                user=request.user.username,
                action=f"搜尋失敗（本機 MES 資料庫）：{error_msg[:900]}",
                timestamp=timezone.now(),
            )
            logger.error(
                f"搜尋失敗詳細日誌（本機 MES 資料庫）：{error_msg}\n堆疊資訊：{traceback.format_exc()}"
            )
            if conn:
                conn.close()
            return render(
                request,
                "erp_integration/table_search.html",
                {
                    "companies": companies,
                    "search_strings": search_strings,
                    "search_condition": search_condition,
                    "selected_company_code": selected_company_code,
                    "order_direction": order_direction,
                    "all_table_names": all_table_names,
                    "error_message": f"搜尋失敗（本機 MES 資料庫）：{error_msg}",
                    "search_target": search_target,
                },
            )

    # 過濾 matched_tables_list，移除空值並去重
    matched_tables_list = list(
        set([t for t in matched_tables_list if t])
    )  # 移除空值並去重
    matched_tables_str = (
        ",".join(matched_tables_list) if matched_tables_list else ""
    )  # 將列表轉為逗號分隔的字符串以供表單使用

    # 無論是否選擇了特定資料表，都保留 matched_tables_list
    if matched_tables_list and not results:
        # 如果有匹配的資料表但未選擇特定表，顯示匹配的資料表列表
        return render(
            request,
            "erp_integration/table_search.html",
            {
                "companies": companies,
                "search_strings": search_strings,
                "search_condition": search_condition,
                "selected_company_code": company_code,
                "order_direction": order_direction,
                "all_table_names": all_tables,
                "matched_tables": matched_tables_list,  # 傳遞列表，而不是字串
                "matched_tables_str": matched_tables_str,  # 保留字串形式以供表單使用
                "failed_tables": failed_tables,
                "failed_reasons": failed_reasons,
                "search_target": search_target,
                "error_message": error_message,  # 確保傳遞 error_message
            },
        )

    if failed_tables:
        # 如果有搜尋失敗的資料表，顯示警告
        messages.warning(request, f'部分資料表搜尋失敗：{", ".join(failed_tables)}')

    # 記錄搜尋操作日誌
    ERPIntegrationOperationLog.objects.create(
        user=request.user.username,
        action=f"搜尋字串 - 公司代碼：{company_code}，搜尋目標：{search_target}，搜尋字串：{search_strings}，條件：{search_condition}，結果數量：{sum(len(result['rows']) for result in results)}",
        timestamp=timezone.now(),
    )

    # 渲染最終結果頁面，同時保留 matched_tables_list
    return render(
        request,
        "erp_integration/table_search.html",
        {
            "companies": companies,
            "search_strings": search_strings,
            "search_condition": search_condition,
            "selected_company_code": company_code,
            "order_direction": order_direction,
            "all_table_names": all_tables,
            "results": results,
            "matched_tables": matched_tables_list,  # 保留匹配的資料表列表
            "matched_tables_str": matched_tables_str,  # 保留字串形式以供表單使用
            "failed_tables": failed_tables,
            "failed_reasons": failed_reasons,
            "search_target": search_target,
            "error_message": error_message,  # 確保傳遞 error_message
        },
    )


# 定義操作日誌視圖，用於顯示 ERP 整合操作日誌
@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def operation_log(request):
    # 查詢所有操作日誌記錄，按時間降序排列
    logs = ERPIntegrationOperationLog.objects.all().order_by("-timestamp")

    # 記錄訪問操作日誌頁面的行為
    ERPIntegrationOperationLog.objects.create(
        user=request.user.username, action="訪問操作日誌頁面", timestamp=timezone.now()
    )

    # 渲染操作日誌頁面，傳遞日誌記錄
    return render(
        request,
        "erp_integration/operation_log.html",
        {
            "logs": logs,
        },
    )


# 定義手動搜尋視圖（SQL 查詢）
@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def manual_search(request):
    companies = CompanyConfig.objects.all()
    error_message = None
    results = []
    column_names = []

    # 初始化表單變數（即使是 GET 請求也設置預設值）
    selected_company_code = (
        request.POST.get("company_code", "") if request.method == "POST" else ""
    )
    search_target = (
        request.POST.get("search_target", "erp") if request.method == "POST" else "erp"
    )
    custom_sql = (
        request.POST.get("custom_sql", "").strip() if request.method == "POST" else ""
    )

    if request.method == "POST":
        company_code = request.POST.get("company_code", "")
        search_target = request.POST.get("search_target", "erp")
        custom_sql = request.POST.get("custom_sql", "").strip()

        # 檢查必填欄位：公司代碼
        if not company_code:
            error_message = "請選擇公司！"
            messages.error(request, error_message)

        # 檢查必填欄位：手動 SQL 指令
        if not custom_sql:
            error_message = "請輸入 SQL 查詢！"
            messages.error(request, error_message)

        # 確保查詢以 SELECT 開頭
        if custom_sql and not custom_sql.upper().startswith("SELECT"):
            error_message = "僅允許 SELECT 查詢！"
            messages.error(request, error_message)

        # 如果有錯誤，重新渲染表單
        if error_message:
            return render(
                request,
                "erp_integration/manual_search.html",
                {
                    "companies": companies,
                    "selected_company_code": company_code,
                    "custom_sql": custom_sql,
                    "results": results,
                    "column_names": column_names,
                    "error_message": error_message,
                    "search_target": search_target,
                },
            )

        # 獲取公司物件並檢查 ERP 連線設定
        company = get_object_or_404(CompanyConfig, company_code=company_code)
        config = ERPConfig.objects.first()
        if not config or not config.server or not company.mssql_database:
            error_message = "ERP 連線設定不完整！請先完成設定。"
            messages.error(request, error_message)
            return render(
                request,
                "erp_integration/manual_search.html",
                {
                    "companies": companies,
                    "selected_company_code": company_code,
                    "custom_sql": custom_sql,
                    "results": results,
                    "column_names": column_names,
                    "error_message": error_message,
                    "search_target": search_target,
                },
            )

        if search_target == "erp":
            # 搜尋遠端 ERP 資料庫（MSSQL）
            conn = None
            try:
                conn = pymssql.connect(
                    server=config.server,
                    user=config.username,
                    password=config.password,
                    database=company.mssql_database,
                    timeout=30,
                    tds_version="7.0",
                )
                cursor = conn.cursor()

                # 執行手動 SQL 查詢
                logger.info(f"執行手動 SQL 查詢（遠端 ERP 資料庫）：{custom_sql}")
                cursor.execute(custom_sql)

                # 獲取查詢結果
                raw_results = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]

                # 記錄查詢結果詳細日誌
                logger.info(f"查詢結果：{raw_results}")
                logger.info(f"欄位名稱：{column_names}")

                # 確保 COUNT(*) 或單值查詢有欄位名
                if len(column_names) == 1 and column_names[0] is None:
                    if "COUNT(*)" in custom_sql.upper():
                        column_names = ["count"]
                    else:
                        column_names = ["value"]

                # 處理查詢結果（轉為字典格式）
                processed_rows = []
                if raw_results:
                    for row in raw_results:
                        processed_row = []
                        for value in row:
                            if isinstance(value, bytes):
                                value = "0x" + value.hex()
                            elif value is None:
                                value = ""
                            processed_row.append(str(value))
                        processed_rows.append(processed_row)
                else:
                    processed_rows = [[0]]  # 如果結果為空，返回一個包含 0 的行
                    logger.info("查詢結果為空，返回默認值 [[0]]")

                # 將結果包裝為字典格式
                results = [
                    {
                        "table_name": "手動 SQL 查詢",
                        "source": "遠端 ERP 資料庫",
                        "rows": processed_rows,
                        "column_names": column_names,
                    }
                ]
                logger.info(f"包裝後的查詢結果：{results}")

                # 記錄操作日誌
                ERPIntegrationOperationLog.objects.create(
                    user=request.user.username,
                    action=f"執行手動 SQL 查詢（遠端 ERP 資料庫）：{custom_sql}，結果數量：{len(processed_rows)}",
                    timestamp=timezone.now(),
                )

                cursor.close()
                conn.close()

            except Exception as e:
                error_msg = str(e) if str(e) else "未知錯誤"
                messages.error(
                    request, f"手動 SQL 查詢失敗（遠端 ERP 資料庫）：{error_msg}"
                )
                ERPIntegrationOperationLog.objects.create(
                    user=request.user.username,
                    action=f"手動 SQL 查詢失敗（遠端 ERP 資料庫）：{error_msg[:900]}",
                    timestamp=timezone.now(),
                )
                logger.error(
                    f"手動 SQL 查詢失敗詳細日誌：{error_msg}\n堆疊資訊：{traceback.format_exc()}"
                )
                if conn:
                    conn.close()
                return render(
                    request,
                    "erp_integration/manual_search.html",
                    {
                        "companies": companies,
                        "selected_company_code": company_code,
                        "custom_sql": custom_sql,
                        "results": results,
                        "column_names": column_names,
                        "error_message": error_msg,
                        "search_target": search_target,
                    },
                )

        elif search_target == "mes":
            # 搜尋本機 MES 資料庫（PostgreSQL）
            conn = None
            try:
                conn = psycopg2.connect(
                    dbname=company.mes_database,
                    user=DATABASE_USER,
                    password=DATABASE_PASSWORD,
                    host=DATABASE_HOST,
                    port=DATABASE_PORT,
                )
                cursor = conn.cursor()

                # 執行手動 SQL 查詢
                logger.info(f"執行手動 SQL 查詢（本機 MES 資料庫）：{custom_sql}")
                cursor.execute(custom_sql)

                # 獲取查詢結果
                raw_results = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]

                # 記錄查詢結果詳細日誌
                logger.info(f"查詢結果：{raw_results}")
                logger.info(f"欄位名稱：{column_names}")

                # 確保 COUNT(*) 或單值查詢有欄位名
                if len(column_names) == 1 and column_names[0] is None:
                    if "COUNT(*)" in custom_sql.upper():
                        column_names = ["count"]
                    else:
                        column_names = ["value"]

                # 處理查詢結果（轉為字典格式）
                processed_rows = []
                if raw_results:
                    for row in raw_results:
                        processed_row = []
                        for value in row:
                            if isinstance(value, bytes):
                                value = "0x" + value.hex()
                            elif value is None:
                                value = ""
                            processed_row.append(str(value))
                        processed_rows.append(processed_row)
                else:
                    processed_rows = [[0]]  # 如果結果為空，返回一個包含 0 的行
                    logger.info("查詢結果為空，返回默認值 [[0]]")

                # 將結果包裝為字典格式
                results = [
                    {
                        "table_name": "手動 SQL 查詢",
                        "source": "本機 MES 資料庫",
                        "rows": processed_rows,
                        "column_names": column_names,
                    }
                ]
                logger.info(f"包裝後的查詢結果：{results}")

                # 記錄操作日誌
                ERPIntegrationOperationLog.objects.create(
                    user=request.user.username,
                    action=f"執行手動 SQL 查詢（本機 MES 資料庫）：{custom_sql}，結果數量：{len(processed_rows)}",
                    timestamp=timezone.now(),
                )

                cursor.close()
                conn.close()

            except Exception as e:
                error_msg = str(e) if str(e) else "未知錯誤"
                messages.error(
                    request, f"手動 SQL 查詢失敗（本機 MES 資料庫）：{error_msg}"
                )
                ERPIntegrationOperationLog.objects.create(
                    user=request.user.username,
                    action=f"手動 SQL 查詢失敗（本機 MES 資料庫）：{error_msg[:900]}",
                    timestamp=timezone.now(),
                )
                logger.error(
                    f"手動 SQL 查詢失敗詳細日誌：{error_msg}\n堆疊資訊：{traceback.format_exc()}"
                )
                if conn:
                    conn.close()
                return render(
                    request,
                    "erp_integration/manual_search.html",
                    {
                        "companies": companies,
                        "selected_company_code": company_code,
                        "custom_sql": custom_sql,
                        "results": results,
                        "column_names": column_names,
                        "error_message": error_msg,
                        "search_target": search_target,
                    },
                )

        return render(
            request,
            "erp_integration/manual_search.html",
            {
                "companies": companies,
                "selected_company_code": company_code,
                "custom_sql": custom_sql,
                "results": results,
                "column_names": column_names,
                "error_message": error_message,  # 確保 error_message 始終傳遞
                "search_target": search_target,
            },
        )

    # GET 請求：渲染手動搜尋頁面
    ERPIntegrationOperationLog.objects.create(
        user=request.user.username, action="訪問手動搜尋頁面", timestamp=timezone.now()
    )
    return render(
        request,
        "erp_integration/manual_search.html",
        {
            "companies": companies,
            "selected_company_code": selected_company_code,
            "custom_sql": custom_sql,
            "results": results,
            "column_names": column_names,
            "error_message": error_message,
            "search_target": search_target,
        },
    )


# 定義 API 視圖：獲取 ERP 連線設定
@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def get_config(request):
    ERPIntegrationOperationLog.objects.create(
        user=request.user.username,
        action="通過 API 獲取 ERP 連線設定",
        timestamp=timezone.now(),
    )
    config = ERPConfig.objects.first()
    if config:
        config_data = {
            "id": config.id,
            "server": config.server,
            "username": config.username,
            "last_updated": config.last_updated.isoformat(),
        }
    else:
        config_data = {}
    return JsonResponse({"config": config_data})


# 定義 API 視圖：獲取所有公司設定
@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def get_companies(request):
    ERPIntegrationOperationLog.objects.create(
        user=request.user.username,
        action="通過 API 獲取公司設定",
        timestamp=timezone.now(),
    )
    companies = CompanyConfig.objects.all()
    companies_data = [
        {
            "id": company.id,
            "company_name": company.company_name,
            "company_code": company.company_code,
            "database": company.database,
            "mssql_database": company.mssql_database,
            "mes_database": company.mes_database,
            "notes": company.notes,
            "sync_tables": company.sync_tables,
            "last_sync_version": company.last_sync_version,
            "last_sync_time": (
                company.last_sync_time.isoformat() if company.last_sync_time else None
            ),
            "sync_interval_minutes": company.sync_interval_minutes,
        }
        for company in companies
    ]
    return JsonResponse({"companies": companies_data})


# 定義 API 視圖：獲取操作日誌
@login_required
@user_passes_test(superuser_required, login_url="/accounts/login/")
def get_operation_logs(request):
    ERPIntegrationOperationLog.objects.create(
        user=request.user.username,
        action="通過 API 獲取操作日誌",
        timestamp=timezone.now(),
    )
    logs = ERPIntegrationOperationLog.objects.all().order_by("-timestamp")
    logs_data = [
        {
            "id": log.id,
            "user": log.user,
            "action": log.action,
            "timestamp": log.timestamp.isoformat(),
        }
        for log in logs
    ]
    return JsonResponse({"operation_logs": logs_data})
