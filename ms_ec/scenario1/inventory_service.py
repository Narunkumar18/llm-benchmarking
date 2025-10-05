from fastapi import FastAPI
import time, uuid, sqlite3

app = FastAPI(title="Inventory Service")
DB_PATH = "inventory.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            item TEXT PRIMARY KEY,
            stock INTEGER
        )
    """)
    return conn

@app.post("/clear_stocks")
def clear_orders():
    conn = get_db()
    conn.execute("DELETE FROM inventory")
    conn.commit()
    conn.close()

@app.post("/init_stock")
def init_stock(request: dict):
    item: str = request["item"]
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO inventory (item, stock) VALUES (?, ?)", (item, 10))
    conn.commit()
    conn.close()

@app.post("/reserve")
def reserve(request: dict):
    item: str = request["item"]
    qty: int = request["qty"]
    delay: int = request.get("delay", 0)
    conn = get_db()
    cur = conn.execute("SELECT stock FROM inventory WHERE item = ?", (item,))
    row = cur.fetchone()
    stock = row[0] if row else 10
    if stock >= qty:
        reservation_id = str(uuid.uuid4())
        conn.execute("UPDATE inventory SET stock = stock - ? WHERE item = ?", (qty, item))
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
    conn = get_db()
    cur = conn.execute("SELECT stock FROM inventory WHERE item = ?", (item,))
    row = cur.fetchone()
    stock = row[0] if row else 0
    conn.close()
    return {"item": item, "stock": stock}
