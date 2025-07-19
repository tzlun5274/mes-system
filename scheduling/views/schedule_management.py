from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.utils import timezone
from ..models import SchedulingOperationLog
import logging
from django.contrib import messages
from django.urls import reverse
from datetime import datetime, timedelta
from ..models import Event

logger = logging.getLogger('scheduling.views')

def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name='排程使用者').exists()

@login_required
@user_passes_test(scheduling_user_required, login_url='/accounts/login/')
def schedule_management(request):
    try:
        SchedulingOperationLog.objects.create(
            user=request.user.username,
            action="查看排程管理頁面",
            timestamp=timezone.now(),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return render(request, 'scheduling/schedule_management.html')
    except Exception as e:
        logger.error(f"處理 /scheduling/schedule_management/ 請求時發生錯誤: {str(e)}")
        return render(request, 'scheduling/schedule_management.html', {'error': str(e)})

@login_required
@user_passes_test(scheduling_user_required, login_url='/accounts/login/')
def add_makeup_day(request):
    """添加補班日"""
    if request.method == 'POST':
        try:
            title = request.POST.get('title', '補班日')
            date_str = request.POST.get('date')
            description = request.POST.get('description', '')
            
            if not date_str:
                messages.error(request, '請選擇補班日期')
                return redirect('scheduling:schedule_management')
            
            # 解析日期
            makeup_date = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())
            
            # 檢查是否已存在
            existing = Event.objects.filter(
                type='workday',
                start__date=makeup_date.date(),
                end__date=makeup_date.date()
            )
            
            if existing.exists():
                messages.warning(request, f'{date_str} 已經是補班日')
                return redirect('scheduling:schedule_management')
            
            # 創建補班日事件
            event = Event.objects.create(
                title=title,
                start=makeup_date,
                end=makeup_date + timedelta(days=1),
                type='workday',
                description=description,
                all_day=True,
                created_by=request.user.username
            )
            
            messages.success(request, f'成功添加補班日: {title} ({date_str})')
            
            log_user_operation(
                username=request.user.username,
                module="scheduling",
                action=f"添加補班日: {title} ({date_str})",
                ip_address=request.META.get('REMOTE_ADDR'),
                event_related=event
            )
            
        except Exception as e:
            logger.error(f"添加補班日失敗: {str(e)}")
            messages.error(request, f'添加補班日失敗: {str(e)}')
    
    return redirect('scheduling:schedule_management')

@login_required
@user_passes_test(scheduling_user_required, login_url='/accounts/login/')
def remove_makeup_day(request, event_id):
    """移除補班日"""
    try:
        event = Event.objects.get(id=event_id, type='workday')
        event_title = event.title
        event_date = event.start.date()
        
        event.delete()
        
        messages.success(request, f'成功移除補班日: {event_title} ({event_date})')
        
        log_user_operation(
            username=request.user.username,
            module="scheduling",
            action=f"移除補班日: {event_title} ({event_date})",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
    except Event.DoesNotExist:
        messages.error(request, '補班日不存在')
    except Exception as e:
        logger.error(f"移除補班日失敗: {str(e)}")
        messages.error(request, f'移除補班日失敗: {str(e)}')
    
    return redirect('scheduling:schedule_management')
