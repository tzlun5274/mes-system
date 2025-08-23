"""
工單管理模組 - 視圖定義
負責工單管理的網頁視圖和表單處理
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse_lazy
from django.forms import ModelForm
from django import forms
from datetime import datetime, time
from decimal import Decimal
from django.conf import settings
from mes_config.date_utils import get_today_string, convert_date_for_html_input, normalize_date_string
from mes_config.custom_fields import smart_time_field
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
import csv
from io import StringIO
from django.http import HttpResponse
from io import StringIO, BytesIO
from django.utils import timezone
try:
    import openpyxl
except Exception:
    openpyxl = None

from .models import WorkOrder, WorkOrderProcess, WorkOrderProduction, WorkOrderProductionDetail, CompletedWorkOrder, CompletedWorkOrderProcess
from workorder.workorder_dispatch.models import WorkOrderDispatch
from workorder.fill_work.models import FillWork
from erp_integration.models import CompanyConfig
from process.models import ProcessName, Operator
from equip.models import Equipment

# 這裡可以添加其他視圖類別 