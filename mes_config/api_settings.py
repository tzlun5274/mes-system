"""
純 API 模式的 Django 設定
跳過所有 admin 相關功能
"""
from .settings import *

# 移除 admin 相關的應用
INSTALLED_APPS = [
    app for app in INSTALLED_APPS 
    if app not in ['django.contrib.admin']
]

# 移除 admin 相關的中間件
MIDDLEWARE = [
    middleware for middleware in MIDDLEWARE
    if 'admin' not in middleware.lower()
]

# 跳過所有 admin 檢查
SILENCED_SYSTEM_CHECKS = [
    'admin.E001', 'admin.E002', 'admin.E003', 'admin.E004', 'admin.E005',
    'admin.E006', 'admin.E007', 'admin.E008', 'admin.E009', 'admin.E010',
    'admin.E011', 'admin.E012', 'admin.E013', 'admin.E014', 'admin.E015',
    'admin.E016', 'admin.E017', 'admin.E018', 'admin.E019', 'admin.E020',
    'admin.E021', 'admin.E022', 'admin.E023', 'admin.E024', 'admin.E025',
    'admin.E026', 'admin.E027', 'admin.E028', 'admin.E029', 'admin.E030',
    'admin.E031', 'admin.E032', 'admin.E033', 'admin.E034', 'admin.E035',
    'admin.E036', 'admin.E037', 'admin.E038', 'admin.E039', 'admin.E040',
    'admin.E041', 'admin.E042', 'admin.E043', 'admin.E044', 'admin.E045',
    'admin.E046', 'admin.E047', 'admin.E048', 'admin.E049', 'admin.E050',
    'admin.E051', 'admin.E052', 'admin.E053', 'admin.E054', 'admin.E055',
    'admin.E056', 'admin.E057', 'admin.E058', 'admin.E059', 'admin.E060',
    'admin.E061', 'admin.E062', 'admin.E063', 'admin.E064', 'admin.E065',
    'admin.E066', 'admin.E067', 'admin.E068', 'admin.E069', 'admin.E070',
    'admin.E071', 'admin.E072', 'admin.E073', 'admin.E074', 'admin.E075',
    'admin.E076', 'admin.E077', 'admin.E078', 'admin.E079', 'admin.E080',
    'admin.E081', 'admin.E082', 'admin.E083', 'admin.E084', 'admin.E085',
    'admin.E086', 'admin.E087', 'admin.E088', 'admin.E089', 'admin.E090',
    'admin.E091', 'admin.E092', 'admin.E093', 'admin.E094', 'admin.E095',
    'admin.E096', 'admin.E097', 'admin.E098', 'admin.E099', 'admin.E100',
    'admin.E101', 'admin.E102', 'admin.E103', 'admin.E104', 'admin.E105',
    'admin.E106', 'admin.E107', 'admin.E108', 'admin.E109', 'admin.E110',
    'admin.E111', 'admin.E112', 'admin.E113', 'admin.E114', 'admin.E115',
    'admin.E116', 'admin.E117', 'admin.E118', 'admin.E119', 'admin.E120',
]

# 禁用 admin 相關的 URL
ROOT_URLCONF = 'mes_config.api_urls'
