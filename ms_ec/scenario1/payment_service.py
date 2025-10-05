from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import time, uuid
from datetime import datetime
from database import get_db, Payment, Order

app = FastAPI(title="Payment Service")

@app.post("/process_payment")
def process_payment(request: dict, db: Session = Depends(get_db)):
    order_id: str = request["order_id"]
    amount: float = request["amount"]
    delay: int = request.get("delay", 0)
    
    # Check if order exists
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Create payment record
    payment_id = str(uuid.uuid4())
    payment = Payment(
        id=payment_id,
        order_id=order_id,
        amount=amount,
        status="PENDING"
    )
    db.add(payment)
    db.commit()
    
    # Simulate payment processing
    time.sleep(delay)
    
    # Mock payment processing (success 90% of the time)
    import random
    success = random.random() < 0.9
    
    if success:
        payment.status = "COMPLETED"
        db.commit()
        return {
            "status": "success",
            "payment_id": payment_id,
            "message": "Payment processed successfully"
        }
    else:
        payment.status = "FAILED"
        db.commit()
        return {
            "status": "failed",
            "payment_id": payment_id,
            "message": "Payment processing failed"
        }

@app.get("/payment_status/{payment_id}")
def get_payment_status(payment_id: str, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return {
        "payment_id": payment.id,
        "order_id": payment.order_id,
        "amount": payment.amount,
        "status": payment.status,
        "created_at": payment.created_at.isoformat(),
        "updated_at": payment.updated_at.isoformat()
    }