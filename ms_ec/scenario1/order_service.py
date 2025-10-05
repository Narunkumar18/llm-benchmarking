from fastapi import FastAPI
import requests, uuid
from database import get_db_connection

app = FastAPI(title="Order Service")

@app.post("/clear_orders")
def clear_orders():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM orders")
    conn.commit()
    conn.close()

@app.post("/order")
def create_order(request: dict):
    item: str = request["item"]
    qty: int = request["qty"]
    delay: int = request.get("delay", 0)
    order_id = str(uuid.uuid4())

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (order_id, item, qty, status) VALUES (?, ?, ?, ?)",
        (order_id, item, qty, "INIT")
    )
    conn.commit()

    # Call Inventory Service
    r = requests.post("http://localhost:8082/reserve", json={"item": item, "qty": qty, "delay": delay})
    res = r.json()

    if res["status"] == "reserved":
        cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", ("RESERVED", order_id))
        conn.commit()

        # Call Payment Service
        r_payment = requests.post("http://localhost:8083/process_payment", json={"order_id": order_id})
        res_payment = r_payment.json()

        if res_payment["status"] == "SUCCESS":
            cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", ("PAID", order_id))
            conn.commit()

            # Call Tracking Service
            r_tracking = requests.post("http://localhost:8084/start_tracking", json={"order_id": order_id})
            res_tracking = r_tracking.json()

            if res_tracking["status"] == "SHIPPED":
                cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", ("COMPLETED", order_id))
                conn.commit()
            else:
                cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", ("FAILED_TRACKING", order_id))
                conn.commit()
        else:
            cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", ("FAILED_PAYMENT", order_id))
            conn.commit()
    elif res["status"] == "out_of_stock":
        cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", ("FAILED_OUT_OF_STOCK", order_id))
        conn.commit()
    else:
        cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", ("FAILED", order_id))
        conn.commit()

    cursor.execute("SELECT status FROM orders WHERE order_id = ?", (order_id,))
    final_status = cursor.fetchone()["status"]
    conn.close()

    return {"order_id": order_id, "final_status": final_status,
            "reservation_id": res.get("reservation_id")}

