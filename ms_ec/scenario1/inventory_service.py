from fastapi import FastAPI
import time, uuid
from database import get_db_connection

app = FastAPI(title="Inventory Service")

@app.post("/clear_stocks")
def clear_stocks():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory")
    conn.commit()
    conn.close()

@app.post("/init_stock")
def init_stock(request: dict):
    item: str = request["item"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO inventory (item, stock) VALUES (?, ?)", (item, 10))
    conn.commit()
    conn.close()

@app.post("/reserve")
def reserve(request: dict):
    item: str = request["item"]
    qty: int = request["qty"]
    delay: int = request.get("delay", 0)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT stock FROM inventory WHERE item = ?", (item,))
    result = cursor.fetchone()
    
    stock = result["stock"] if result else 10

    if stock >= qty:
        reservation_id = str(uuid.uuid4())
        
        new_stock = stock - qty
        cursor.execute("UPDATE inventory SET stock = ? WHERE item = ?", (new_stock, item))
        conn.commit()
        
        time.sleep(delay)  # Injected delay
        conn.close()
        return {"status": "reserved", "reservation_id": reservation_id}
    else:
        time.sleep(delay)  # Injected delay
        conn.close()
        return {"status": "out_of_stock", "reservation_id": None}

@app.get("/debug_stock")
def debug_stock(item: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT stock FROM inventory WHERE item = ?", (item,))
    result = cursor.fetchone()
    
    stock = result["stock"] if result else 0
    conn.close()
    
    return {"item": item, "stock": stock}

