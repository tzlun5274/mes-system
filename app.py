        # å¾žè??™åº«?²å?è¨‚å–®?Œè?æº?
        orders = get_orders()
        resources = get_resources()
        # ?·è??ªå??’ç?
        schedule = auto_schedule(orders, resources)
        return render_template('index.html', schedule=schedule, message="è¨‚å–®å·²æ?äº¤ä¸¦?’ç?")
    orders = get_orders()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
