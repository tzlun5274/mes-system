        # 從�??�庫?��?訂單?��?�?
        orders = get_orders()
        resources = get_resources()
        # ?��??��??��?
        schedule = auto_schedule(orders, resources)
        return render_template('index.html', schedule=schedule, message="訂單已�?交並?��?")
    orders = get_orders()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
