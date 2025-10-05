from fastapi import FastAPI
import uuid
import sqlite3

app = FastAPI(title="RealTimeTracking Service")
DB_PATH = "tracking.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tracking (
            order_id TEXT PRIMARY KEY,
            status TEXT
        )
    """)
    return conn

@app.post("/update_status")
def update_status(request: dict):
    order_id = request["order_id"]
    status = request["status"]
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO tracking (order_id, status) VALUES (?, ?)",
        (order_id, status)
    )
    conn.commit()
    conn.close()
    return {"order_id": order_id, "status": status}

@app.get("/get_status")
def get_status(order_id: str):
    conn = get_db()
    cur = conn.execute("SELECT status FROM tracking WHERE order_id = ?", (order_id,))
    row = cur.fetchone()
    conn.close()
    return {"order_id": order_id, "status": row[0] if row else "unknown"}
