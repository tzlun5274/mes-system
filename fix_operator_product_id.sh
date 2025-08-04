#!/bin/bash
# 作業員報工記錄產品編號修復腳本

echo "開始修復作業員報工記錄產品編號..."

# 1. 先修復工單關聯
echo "步驟1: 修復報工記錄關聯"
python manage.py 修復報工記錄關聯

# 2. 修正工單號碼格式
echo "步驟2: 修正錯誤工單號碼"
python manage.py 修正錯誤工單號碼

# 3. 處理重複工單記錄
echo "步驟3: 處理重複工單記錄"
python manage.py 處理重複工單記錄

# 4. 智能補充產品編號
echo "步驟4: 智能補充產品編號"
python manage.py 智能補充產品編號

# 5. 從工單補充產品編號
echo "步驟5: 從工單補充產品編號"
python manage.py 從工單補充產品編號

# 6. 從其他記錄補充產品編號
echo "步驟6: 從其他記錄補充產品編號"
python manage.py 從其他記錄補充產品編號

echo "修復完成！"
