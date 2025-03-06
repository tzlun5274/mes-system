    # Âª∫Á?Ë≥áÊ?Ë°?
    c.execute('''CREATE TABLE IF NOT EXISTS resources (
                    machine TEXT PRIMARY KEY,
                    available INTEGER NOT NULL)''')
    # ?ùÂ??ñË?Ê∫êÔ?Â¶ÇÊ?Ë°®ÁÇ∫Á©∫Ô?
    c.execute("INSERT OR IGNORE INTO resources (machine, available) VALUES ('Machine1', 1)")
    c.execute("INSERT OR IGNORE INTO resources (machine, available) VALUES ('Machine2', 1)")
    conn.commit()
    conn.close()

def add_order(name, quantity):
    conn = sqlite3.connect('mes.db')
    c = conn.cursor()
    c.execute("INSERT INTO orders (name, quantity, status) VALUES (?, ?, 'ÂæÖÊ?Á®?)", (name, quantity))
    conn.commit()
    conn.close()

def get_orders():
    conn = sqlite3.connect('mes.db')
    c = conn.cursor()
    c.execute("SELECT id, name, quantity, status FROM orders")
    orders = [{"id": row[0], "name": row[1], "quantity": row[2], "status": row[3]} for row in c.fetchall()]
    conn.close()
    return orders

def get_resources():
    conn = sqlite3.connect('mes.db')
    c = conn.cursor()
    c.execute("SELECT machine, available FROM resources")
    resources = {row[0]: bool(row[1]) for row in c.fetchall()}
    conn.close()
    return resources

def update_order_status(order_id, status):
    conn = sqlite3.connect('mes.db')
    c = conn.cursor()
    c.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()

def update_resource(machine, available):
    conn = sqlite3.connect('mes.db')
    c = conn.cursor()
    c.execute("UPDATE resources SET available = ? WHERE machine = ?", (int(available), machine))
    conn.commit()
    conn.close()
