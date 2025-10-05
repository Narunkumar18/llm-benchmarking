from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import requests, uuid, asyncio
from datetime import datetime
from database import get_db, Order

app = FastAPI(title="Order Service")

INVENTORY_SERVICE_URL = "http://localhost:8082"
PAYMENT_SERVICE_URL = "http://localhost:8083"
TRACKING_SERVICE_URL = "http://localhost:8084"

@app.post("/clear_orders")
def clear_orders(db: Session = Depends(get_db)):
    db.query(Order).delete()
    db.commit()
    return {"status": "success"}

async def update_tracking(order_id: str, status: str, details: str = None):
    try:
        requests.post(f"{TRACKING_SERVICE_URL}/update_tracking", 
                     json={"order_id": order_id, "status": status, "details": details})
    except Exception as e:
        print(f"Error updating tracking: {e}")

@app.post("/order")
async def create_order(request: dict, db: Session = Depends(get_db)):
    item: str = request["item"]
    qty: int = request["qty"]
    delay: int = request.get("delay", 0)
    amount: float = request.get("amount", qty * 10.0)  # Mock price calculation
    
    # Create order
    order_id = str(uuid.uuid4())
    order = Order(
        id=order_id,
        item=item,
        qty=qty,
        status="INIT",
        created_at=datetime.utcnow()
    )
    db.add(order)
    db.commit()
    
    # Update tracking - Order Created
    await update_tracking(order_id, "ORDER_CREATED", f"Order created for {qty} units of {item}")
    
    # Check inventory
    r = requests.post(f"{INVENTORY_SERVICE_URL}/reserve", 
                     json={"item": item, "qty": qty, "delay": delay})
    inventory_res = r.json()
    
    if inventory_res["status"] != "reserved":
        order.status = "FAILED_OUT_OF_STOCK"
        db.commit()
        await update_tracking(order_id, "FAILED", "Item out of stock")
        return {
            "order_id": order_id,
            "final_status": "FAILED_OUT_OF_STOCK",
            "reservation_id": None
        }
    
    # Update tracking - Stock Reserved
    await update_tracking(order_id, "STOCK_RESERVED", 
                        f"Stock reserved: {qty} units of {item}")
    
    # Process payment
    try:
        r = requests.post(f"{PAYMENT_SERVICE_URL}/process_payment",
                         json={"order_id": order_id, "amount": amount, "delay": delay})
        payment_res = r.json()
        
        if payment_res["status"] == "success":
            order.status = "COMPLETED"
            db.commit()
            await update_tracking(order_id, "PAYMENT_COMPLETED", 
                                f"Payment processed successfully: ${amount}")
        else:
            order.status = "PAYMENT_FAILED"
            db.commit()
            await update_tracking(order_id, "PAYMENT_FAILED", 
                                "Payment processing failed")
            # TODO: Release inventory
            return {
                "order_id": order_id,
                "final_status": "PAYMENT_FAILED",
                "reservation_id": inventory_res["reservation_id"]
            }
            
    except Exception as e:
        order.status = "PAYMENT_ERROR"
        db.commit()
        await update_tracking(order_id, "PAYMENT_ERROR", str(e))
        return {
            "order_id": order_id,
            "final_status": "PAYMENT_ERROR",
            "reservation_id": inventory_res["reservation_id"]
        }
    
    await update_tracking(order_id, "ORDER_COMPLETED", 
                        "Order has been completed successfully")
    
    return {
        "order_id": order_id,
        "final_status": "COMPLETED",
        "reservation_id": inventory_res["reservation_id"],
        "payment_id": payment_res.get("payment_id")
    }

@app.get("/order_status/{order_id}")
async def get_order_status(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get tracking history
    try:
        r = requests.get(f"{TRACKING_SERVICE_URL}/tracking_history/{order_id}")
        tracking_history = r.json()
    except:
        tracking_history = {"tracking_history": []}
    
    return {
        "order_id": order.id,
        "item": order.item,
        "qty": order.qty,
        "status": order.status,
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
        "tracking_history": tracking_history.get("tracking_history", [])
    }
