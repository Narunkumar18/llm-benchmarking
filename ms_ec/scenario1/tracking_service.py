
from fastapi import FastAPI
import uuid
from database import get_db_connection

app = FastAPI(title="Tracking Service")

@app.post("/start_tracking")
def start_tracking(request: dict):
    order_id = request["order_id"]
    tracking_id = str(uuid.uuid4())
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    tracking_status = "SHIPPED"
    
    cursor.execute(
        "INSERT INTO tracking (tracking_id, order_id, status) VALUES (?, ?, ?)",
        (tracking_id, order_id, tracking_status)
    )
    conn.commit()
    conn.close()
    
    return {"tracking_id": tracking_id, "status": tracking_status}

@app.get("/track_order/{order_id}")
def track_order(order_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT status FROM tracking WHERE order_id = ?", (order_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return {"order_id": order_id, "status": result["status"]}
    else:
        return {"order_id": order_id, "status": "NOT_FOUND"}

@app.post("/clear_tracking")
def clear_tracking():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tracking")
    conn.commit()
    conn.close()
