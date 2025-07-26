from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, time
from .models import WorkOrder
from process.models import ProcessName, Operator
from equip.models import Equipment

# 主管審核記錄測試案例 - 已刪除，準備重新設計
