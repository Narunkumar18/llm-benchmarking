from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db, OrderTracking, Order

app = FastAPI(title="Tracking Service")

@app.post("/update_tracking")
def update_tracking(request: dict, db: Session = Depends(get_db)):
    order_id: str = request["order_id"]
    status: str = request["status"]
    details: str = request.get("details", None)
    
    # Check if order exists
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Create tracking update
    tracking = OrderTracking(
        order_id=order_id,
        status=status,
        details=details,
        timestamp=datetime.utcnow()
    )
    db.add(tracking)
    db.commit()
    
    return {
        "status": "success",
        "tracking_id": tracking.id,
        "timestamp": tracking.timestamp.isoformat()
    }

@app.get("/tracking_history/{order_id}")
def get_tracking_history(order_id: str, db: Session = Depends(get_db)):
    # Check if order exists
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get all tracking updates for the order
    tracking_updates = (
        db.query(OrderTracking)
        .filter(OrderTracking.order_id == order_id)
        .order_by(OrderTracking.timestamp.desc())
        .all()
    )
    
    return {
        "order_id": order_id,
        "current_status": tracking_updates[0].status if tracking_updates else "UNKNOWN",
        "tracking_history": [
            {
                "status": update.status,
                "details": update.details,
                "timestamp": update.timestamp.isoformat()
            }
            for update in tracking_updates
        ]
    }