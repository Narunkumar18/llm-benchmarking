from fastapi import FastAPI
import uuid
import sqlite3

app = FastAPI(title="Payment Service")
DB_PATH = "payments.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id TEXT PRIMARY KEY,
            order_id TEXT,
            customer_id TEXT,
            amount REAL,
            status TEXT
        )
    """)
    return conn

@app.post("/process_payment")
def process_payment(request: dict):
    order_id = request["order_id"]
    customer_id = request["customer_id"]
    amount = request["amount"]
    payment_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute(
        "INSERT INTO payments (id, order_id, customer_id, amount, status) VALUES (?, ?, ?, ?, ?)",
        (payment_id, order_id, customer_id, amount, "COMPLETED")
    )
    conn.commit()
    conn.close()
    return {"payment_id": payment_id, "status": "COMPLETED"}
