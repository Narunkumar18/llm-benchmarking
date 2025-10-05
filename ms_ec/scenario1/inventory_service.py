from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import time, uuid
from datetime import datetime
from database import get_db, Inventory

app = FastAPI(title="Inventory Service")

@app.post("/clear_stocks")
def clear_stocks(db: Session = Depends(get_db)):
    db.query(Inventory).delete()
    db.commit()
    return {"status": "success"}

@app.post("/init_stock")
def init_stock(request: dict, db: Session = Depends(get_db)):
    item: str = request["item"]
    stock_item = Inventory(
        item=item,
        stock=10,
        last_updated=datetime.utcnow()
    )
    db.add(stock_item)
    db.commit()
    return {"status": "success"}

@app.post("/reserve")
def reserve(request: dict, db: Session = Depends(get_db)):
    item: str = request["item"]
    qty: int = request["qty"]
    delay: int = request.get("delay", 0)
    
    stock_item = db.query(Inventory).filter(Inventory.item == item).first()
    if not stock_item:
        stock_item = Inventory(item=item, stock=10)
        db.add(stock_item)
        db.commit()
    
    if stock_item.stock >= qty:
        reservation_id = str(uuid.uuid4())
        stock_item.stock -= qty
        stock_item.last_updated = datetime.utcnow()
        db.commit()
        
        time.sleep(delay)  # Injected delay
        return {"status": "reserved", "reservation_id": reservation_id}
    else:
        time.sleep(delay)  # Injected delay
        return {"status": "out_of_stock", "reservation_id": None}

@app.get("/debug_stock")
def debug_stock(item: str, db: Session = Depends(get_db)):
    stock_item = db.query(Inventory).filter(Inventory.item == item).first()
    if not stock_item:
        return {"item": item, "stock": 0}
    return {"item": item, "stock": stock_item.stock}

# New endpoint for real-time stock updates
@app.get("/stock_status")
def get_stock_status(item: str, db: Session = Depends(get_db)):
    stock_item = db.query(Inventory).filter(Inventory.item == item).first()
    if not stock_item:
        return {
            "item": item,
            "stock": 0,
            "status": "unavailable",
            "last_updated": None
        }
    return {
        "item": item,
        "stock": stock_item.stock,
        "status": "in_stock" if stock_item.stock > 0 else "out_of_stock",
        "last_updated": stock_item.last_updated.isoformat()
    }
