                    update_resource(machine, False)  # 標�?機器?��???
                    break
            else:
                schedule.append(f"{order['name']} (?��?: {order['quantity']}) 等�?資�?")
    return schedule
