from fastapi import FastAPI
import requests, uuid, sqlite3

app = FastAPI(title="Order Service")
DB_PATH = "orders.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            item TEXT,
            qty INTEGER,
            customer_id TEXT,
            status TEXT
        )
    """)
    return conn

@app.post("/clear_orders")
def clear_orders():
    conn = get_db()
    conn.execute("DELETE FROM orders")
    conn.commit()
    conn.close()

@app.post("/order")
def create_order(request: dict):
    item: str = request["item"]
    qty: int = request["qty"]
    delay: int = request.get("delay", 0)
    customer_id = request.get("customer_id", "guest")
    amount = request.get("amount", 100)  # Example amount
    order_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute(
        "INSERT INTO orders (id, item, qty, customer_id, status) VALUES (?, ?, ?, ?, ?)",
        (order_id, item, qty, customer_id, "INIT")
    )
    conn.commit()

    # Inventory check
    r = requests.post("http://localhost:8082/reserve", json={"item": item, "qty": qty, "delay": delay})
    res = r.json()
    reservation_id = res.get("reservation_id")

    if res["status"] == "reserved":
        conn.execute("UPDATE orders SET status = ? WHERE id = ?", ("RESERVED", order_id))
        conn.commit()
        # Payment processing
        pay_res = requests.post("http://localhost:8083/process_payment", json={"order_id": order_id, "customer_id": customer_id, "amount": amount})
        pay_status = pay_res.json().get("status")
        if pay_status == "COMPLETED":
            conn.execute("UPDATE orders SET status = ? WHERE id = ?", ("COMPLETED", order_id))
            conn.commit()
            # Real-time tracking update
            requests.post("http://localhost:8084/update_status", json={"order_id": order_id, "status": "COMPLETED"})
        else:
            conn.execute("UPDATE orders SET status = ? WHERE id = ?", ("FAILED_PAYMENT", order_id))
            conn.commit()
            requests.post("http://localhost:8084/update_status", json={"order_id": order_id, "status": "FAILED_PAYMENT"})
    elif res["status"] == "out_of_stock":
        conn.execute("UPDATE orders SET status = ? WHERE id = ?", ("FAILED_OUT_OF_STOCK", order_id))
        conn.commit()
        requests.post("http://localhost:8084/update_status", json={"order_id": order_id, "status": "FAILED_OUT_OF_STOCK"})
    else:
        conn.execute("UPDATE orders SET status = ? WHERE id = ?", ("FAILED", order_id))
        conn.commit()
        requests.post("http://localhost:8084/update_status", json={"order_id": order_id, "status": "FAILED"})

    # Get tracking status
    track_res = requests.get(f"http://localhost:8084/get_status?order_id={order_id}")
    tracking_status = track_res.json().get("status")

    cur = conn.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
    order_status = cur.fetchone()[0] if cur.fetchone() else "unknown"
    conn.close()

    return {
        "order_id": order_id,
        "final_status": order_status,
        "reservation_id": reservation_id,
        "tracking_status": tracking_status
    }
