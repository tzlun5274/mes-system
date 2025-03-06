                    update_resource(machine, False)  # æ¨™è?æ©Ÿå™¨?ºå???
                    break
            else:
                schedule.append(f"{order['name']} (?¸é?: {order['quantity']}) ç­‰å?è³‡æ?")
    return schedule
