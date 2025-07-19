from django.contrib import messages
from django.utils.translation import gettext_lazy
from django.utils import timezone
from zoneinfo import ZoneInfo
import logging

TAIWAN_TZ = ZoneInfo("Asia/Taipei")
logger = logging.getLogger('scheduling.views')
