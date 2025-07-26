from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy
from ..models import Event
from ..utils import log_user_operation
import logging
import csv
import io
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger("scheduling.views")
TAIWAN_TZ = ZoneInfo("Asia/Taipei")


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def import_events(request):
    if request.method == "POST":
        try:
            file = request.FILES.get("file")
            if not file:
                messages.error(request, gettext_lazy("請選擇一個 CSV 檔案"))
                return JsonResponse(
                    {"status": "error", "message": "請選擇一個 CSV 檔案"}, status=400
                )

            if not file.name.endswith(".csv"):
                messages.error(request, gettext_lazy("檔案格式必須為 CSV"))
                return JsonResponse(
                    {"status": "error", "message": "檔案格式必須為 CSV"}, status=400
                )

            try:
                file_data = file.read().decode("utf-8-sig")  # 處理 UTF-8 BOM
            except UnicodeDecodeError:
                messages.error(
                    request,
                    gettext_lazy("無法解碼 CSV 檔案，請確保檔案使用 UTF-8 編碼"),
                )
                return JsonResponse(
                    {"status": "error", "message": "無法解碼 CSV 檔案"}, status=400
                )

            csv_data = csv.DictReader(io.StringIO(file_data))
            expected_headers = ["subject", "start date", "end date", "all day event"]
            actual_headers = [
                header.strip().lower() for header in csv_data.fieldnames if header
            ]
            missing_headers = [
                header for header in expected_headers if header not in actual_headers
            ]
            if missing_headers:
                messages.error(
                    request,
                    gettext_lazy(f"CSV 缺少必要欄位: {', '.join(missing_headers)}"),
                )
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"CSV 缺少必要欄位: {', '.join(missing_headers)}",
                    },
                    status=400,
                )

            header_mapping = {
                header.strip().lower(): header
                for header in csv_data.fieldnames
                if header
            }
            subject_key = header_mapping["subject"]
            start_date_key = header_mapping["start date"]
            end_date_key = header_mapping["end date"]
            all_day_key = header_mapping["all day event"]
            description_key = header_mapping.get("description", "Description")

            created_count = 0
            errors = []
            for row in csv_data:
                try:
                    if not row[subject_key]:
                        logger.debug("跳過空行")
                        continue
                    if row[subject_key] == "補行上班":
                        logger.debug("跳過補行上班日")
                        continue

                    title = row[subject_key]
                    if title == "例假日":
                        title = "週末"

                    start_date_str = row[start_date_key].strip()
                    end_date_str = row[end_date_key].strip()
                    try:
                        start_date = datetime.strptime(
                            start_date_str, "%Y/%m/%d"
                        ).replace(tzinfo=TAIWAN_TZ)
                        end_date = datetime.strptime(end_date_str, "%Y/%m/%d").replace(
                            tzinfo=TAIWAN_TZ
                        )
                    except ValueError as e:
                        errors.append(f"事件 '{title}': 日期格式無效 ({str(e)})")
                        continue

                    all_day = row[all_day_key].strip().upper() == "TRUE"
                    description = row.get(description_key, "")

                    duration = (end_date - start_date).days + 1
                    for i in range(duration):
                        current_date = start_date + timedelta(days=i)
                        start_datetime = current_date.replace(hour=0, minute=0)
                        end_datetime = current_date.replace(hour=23, minute=59)

                        existing_event = Event.objects.filter(
                            start=start_datetime, end=end_datetime, type="holiday"
                        ).first()

                        if existing_event:
                            existing_event.title = title
                            existing_event.description = description
                            existing_event.all_day = all_day
                            existing_event.category = "general"
                            existing_event.save()
                            logger.debug(f"更新現有事件: {title} ({start_datetime})")
                        else:
                            Event.objects.create(
                                title=title,
                                start=start_datetime,
                                end=end_datetime,
                                type="holiday",
                                description=description,
                                classNames="holiday",
                                all_day=all_day,
                                category="general",
                                created_by=request.user.username,
                            )
                            logger.debug(f"創建新事件: {title} ({start_datetime})")
                        created_count += 1

                except (ValueError, KeyError) as e:
                    errors.append(
                        f"事件 '{row.get(subject_key, '未知')}': 數據無效 ({str(e)})"
                    )
                    continue

            log_user_operation(
                username=request.user.username,
                module="scheduling",
                action=f"匯入事件: 成功 {created_count} 筆，失敗 {len(errors)} 筆",
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            if created_count > 0:
                messages.success(
                    request, gettext_lazy(f"成功匯入 {created_count} 筆事件")
                )
            if errors:
                messages.warning(
                    request, gettext_lazy(f"以下事件匯入失敗: {'; '.join(errors)}")
                )

            return JsonResponse(
                {
                    "status": "success" if created_count > 0 else "warning",
                    "message": f"匯入完成: 成功 {created_count} 筆，失敗 {len(errors)} 筆",
                }
            )

        except Exception as e:
            logger.error(f"匯入事件失敗: {str(e)}", exc_info=True)
            messages.error(request, gettext_lazy("匯入事件失敗，請聯繫管理員"))
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    else:
        return render(
            request, "scheduling/import_events.html", {"show_duplicate_events": False}
        )
