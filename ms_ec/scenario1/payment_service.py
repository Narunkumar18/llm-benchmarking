
from fastapi import FastAPI
import uuid
from database import get_db_connection

app = FastAPI(title="Payment Service")

@app.post("/process_payment")
def process_payment(request: dict):
    order_id = request["order_id"]
    payment_id = str(uuid.uuid4())
    
    # Mock payment processing
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # In a real scenario, you'd integrate with a payment gateway
    payment_status = "SUCCESS"  # Mocking success
    
    cursor.execute(
        "INSERT INTO payments (payment_id, order_id, status) VALUES (?, ?, ?)",
        (payment_id, order_id, payment_status)
    )
    conn.commit()
    conn.close()
    
    return {"payment_id": payment_id, "status": payment_status}

@app.post("/clear_payments")
def clear_payments():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM payments")
    conn.commit()
    conn.close()
