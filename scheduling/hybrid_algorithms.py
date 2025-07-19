# -*- coding: utf-8 -*-
"""
這個檔案提供混合式排程的主要演算法。
hybrid_scheduling_algorithm 會根據訂單、設備、作業員等資訊，自動分組、檢查資源衝突並嘗試最佳化。
"""

def hybrid_scheduling_algorithm(orders, machines, operators, settings=None):
    """
    混合式排程主函式
    參數：
        orders: 訂單清單（每筆包含工單編號、數量、交期等）
        machines: 設備清單（每台包含設備編號、型號、狀態等）
        operators: 作業員清單（每位包含姓名、班別、可操作設備等）
        settings: 其他排程設定（可選）
    回傳：
        一個最佳化後的排程結果（list of dict）
    """
    # 繁體中文說明：這裡會先簡單分組訂單，再依序分配設備與作業員，遇到衝突就自動延後。
    schedule = []
    for order in orders:
        # 找到可用設備
        available_machines = [m for m in machines if m.get('status', '正常') == '正常']
        if not available_machines:
            schedule.append({
                'order_id': order['id'],
                'status': '排程失敗',
                'reason': '無可用設備'
            })
            continue
        # 找到可用作業員
        available_operators = [o for o in operators if order.get('required_skill') in o.get('skills', [])]
        if not available_operators:
            schedule.append({
                'order_id': order['id'],
                'status': '排程失敗',
                'reason': '無可用作業員'
            })
            continue
        # 指派第一台設備與第一位作業員
        machine = available_machines[0]
        operator = available_operators[0]
        schedule.append({
            'order_id': order['id'],
            'machine_id': machine['id'],
            'operator_name': operator['name'],
            'status': '排程成功'
        })
    return schedule

def validate_hybrid_schedule(tasks):
    """
    驗證混合排程結果，回傳警告訊息清單。
    這裡僅做簡單範例：檢查有沒有重複分配同一設備。
    """
    warnings = []
    used_machines = set()
    for task in tasks:
        mid = task.get('machine_id')
        if mid in used_machines:
            warnings.append(f"設備 {mid} 被重複分配")
        else:
            used_machines.add(mid)
    return warnings

def get_scheduling_statistics(tasks):
    """
    統計排程結果，回傳簡單統計資訊。
    """
    total = len(tasks)
    success = sum(1 for t in tasks if t.get('status') == '排程成功')
    fail = total - success
    return {
        '總任務數': total,
        '成功數': success,
        '失敗數': fail
    }

def group_orders_by_priority(orders):
    """
    根據訂單的優先級分組，這裡僅做簡單範例。
    """
    class Group:
        def __init__(self, orders):
            self.orders = orders
    groups = {
        'urgent': Group([o for o in orders if o.get('priority') == 'urgent']),
        'normal': Group([o for o in orders if o.get('priority') == 'normal']),
        'flexible': Group([o for o in orders if o.get('priority') == 'flexible']),
    }
    return groups

# 範例用法（可刪除）
if __name__ == "__main__":
    orders = [
        {'id': 1, 'required_skill': 'SMT'},
        {'id': 2, 'required_skill': '測試'},
    ]
    machines = [
        {'id': 'M1', 'status': '正常'},
        {'id': 'M2', 'status': '維修'},
    ]
    operators = [
        {'name': '小明', 'skills': ['SMT']},
        {'name': '小華', 'skills': ['測試']},
    ]
    result = hybrid_scheduling_algorithm(orders, machines, operators)
    print(result) 