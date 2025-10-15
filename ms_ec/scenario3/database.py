"""
SQLite Database Layer for Microservices E-Commerce System
Thread-safe database operations for orders, inventory, payments, and tracking
"""

import sqlite3
import threading
import logging
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, Dict, List, Any

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("database")


class Database:
    """Thread-safe SQLite database handler"""
    
    def __init__(self, db_path: str = "retail.db"):
        self.db_path = db_path
        self.local = threading.local()
        self._initialize_database()
    
    def _get_connection(self):
        """Get thread-local database connection"""
        if not hasattr(self.local, "conn"):
            self.local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.local.conn.row_factory = sqlite3.Row
        return self.local.conn
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            LOG.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
    
    def _initialize_database(self):
        """Create tables if they don't exist"""
        with self.get_cursor() as cursor:
            # Orders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT NOT NULL,
                    payment_id TEXT,
                    tracking_id TEXT,
                    reservation_id TEXT,
                    parallel_processing INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Inventory table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    product_id TEXT PRIMARY KEY,
                    stock INTEGER NOT NULL DEFAULT 0,
                    reserved INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Reservations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reservations (
                    reservation_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(order_id)
                )
            """)
            
            # Payments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    payment_method TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(order_id)
                )
            """)
            
            # Tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracking (
                    tracking_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    status_history TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(order_id)
                )
            """)
            
            LOG.info("Database initialized successfully")
    
    # ========================================
    # Order Operations
    # ========================================
    
    def create_order(self, order_id: str, product_id: str, quantity: int, 
                    amount: float, parallel_processing: bool = False) -> bool:
        """Create a new order"""
        try:
            now = datetime.utcnow().isoformat()
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO orders (order_id, product_id, quantity, amount, 
                                      status, parallel_processing, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'INITIATED', ?, ?, ?)
                """, (order_id, product_id, quantity, amount, int(parallel_processing), now, now))
            LOG.info(f"Order created: {order_id}")
            return True
        except Exception as e:
            LOG.error(f"Failed to create order {order_id}: {e}")
            return False
    
    def update_order_status(self, order_id: str, status: str, 
                          payment_id: Optional[str] = None,
                          tracking_id: Optional[str] = None,
                          reservation_id: Optional[str] = None) -> bool:
        """Update order status and associated IDs"""
        try:
            now = datetime.utcnow().isoformat()
            with self.get_cursor() as cursor:
                updates = ["status = ?", "updated_at = ?"]
                params = [status, now]
                
                if payment_id:
                    updates.append("payment_id = ?")
                    params.append(payment_id)
                if tracking_id:
                    updates.append("tracking_id = ?")
                    params.append(tracking_id)
                if reservation_id:
                    updates.append("reservation_id = ?")
                    params.append(reservation_id)
                
                params.append(order_id)
                
                cursor.execute(f"""
                    UPDATE orders 
                    SET {', '.join(updates)}
                    WHERE order_id = ?
                """, params)
            LOG.info(f"Order {order_id} status updated to {status}")
            return True
        except Exception as e:
            LOG.error(f"Failed to update order {order_id}: {e}")
            return False
    
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order details"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            LOG.error(f"Failed to get order {order_id}: {e}")
            return None
    
    def clear_orders(self) -> bool:
        """Clear all orders"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("DELETE FROM orders")
            LOG.info("All orders cleared")
            return True
        except Exception as e:
            LOG.error(f"Failed to clear orders: {e}")
            return False
    
    # ========================================
    # Inventory Operations
    # ========================================
    
    def initialize_stock(self, product_id: str, quantity: int) -> bool:
        """Initialize or update stock for a product"""
        try:
            now = datetime.utcnow().isoformat()
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO inventory (product_id, stock, reserved, updated_at)
                    VALUES (?, ?, 0, ?)
                    ON CONFLICT(product_id) DO UPDATE SET
                        stock = stock + ?,
                        updated_at = ?
                """, (product_id, quantity, now, quantity, now))
            LOG.info(f"Stock initialized for {product_id}: {quantity}")
            return True
        except Exception as e:
            LOG.error(f"Failed to initialize stock for {product_id}: {e}")
            return False
    
    def check_stock(self, product_id: str, quantity: int) -> tuple[bool, int]:
        """Check if sufficient stock is available"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT stock, reserved FROM inventory WHERE product_id = ?
                """, (product_id,))
                row = cursor.fetchone()
                
                if not row:
                    return False, 0
                
                available = row['stock'] - row['reserved']
                return available >= quantity, available
        except Exception as e:
            LOG.error(f"Failed to check stock for {product_id}: {e}")
            return False, 0
    
    def reserve_stock(self, product_id: str, quantity: int) -> bool:
        """Reserve stock atomically"""
        try:
            now = datetime.utcnow().isoformat()
            with self.get_cursor() as cursor:
                # Check available stock
                cursor.execute("""
                    SELECT stock, reserved FROM inventory WHERE product_id = ?
                """, (product_id,))
                row = cursor.fetchone()
                
                if not row:
                    LOG.warning(f"Product {product_id} not found")
                    return False
                
                available = row['stock'] - row['reserved']
                if available < quantity:
                    LOG.warning(f"Insufficient stock for {product_id}: {available} < {quantity}")
                    return False
                
                # Reserve stock
                cursor.execute("""
                    UPDATE inventory 
                    SET reserved = reserved + ?, updated_at = ?
                    WHERE product_id = ?
                """, (quantity, now, product_id))
                
                LOG.info(f"Reserved {quantity} units of {product_id}")
                return True
        except Exception as e:
            LOG.error(f"Failed to reserve stock for {product_id}: {e}")
            return False
    
    def release_stock(self, product_id: str, quantity: int) -> bool:
        """Release reserved stock"""
        try:
            now = datetime.utcnow().isoformat()
            with self.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE inventory 
                    SET reserved = reserved - ?, updated_at = ?
                    WHERE product_id = ?
                """, (quantity, now, product_id))
            LOG.info(f"Released {quantity} units of {product_id}")
            return True
        except Exception as e:
            LOG.error(f"Failed to release stock for {product_id}: {e}")
            return False
    
    def commit_reservation(self, product_id: str, quantity: int) -> bool:
        """Commit reservation by reducing stock and reserved count"""
        try:
            now = datetime.utcnow().isoformat()
            with self.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE inventory 
                    SET stock = stock - ?, reserved = reserved - ?, updated_at = ?
                    WHERE product_id = ?
                """, (quantity, quantity, now, product_id))
            LOG.info(f"Committed reservation of {quantity} units of {product_id}")
            return True
        except Exception as e:
            LOG.error(f"Failed to commit reservation for {product_id}: {e}")
            return False
    
    def clear_inventory(self) -> bool:
        """Clear all inventory"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("DELETE FROM inventory")
            LOG.info("All inventory cleared")
            return True
        except Exception as e:
            LOG.error(f"Failed to clear inventory: {e}")
            return False
    
    # ========================================
    # Reservation Operations
    # ========================================
    
    def create_reservation(self, reservation_id: str, order_id: str, 
                          product_id: str, quantity: int) -> bool:
        """Create a reservation record"""
        try:
            now = datetime.utcnow().isoformat()
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO reservations (reservation_id, order_id, product_id, 
                                            quantity, status, created_at)
                    VALUES (?, ?, ?, ?, 'ACTIVE', ?)
                """, (reservation_id, order_id, product_id, quantity, now))
            LOG.info(f"Reservation created: {reservation_id}")
            return True
        except Exception as e:
            LOG.error(f"Failed to create reservation {reservation_id}: {e}")
            return False
    
    def get_reservation(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get reservation by order ID"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM reservations WHERE order_id = ?
                """, (order_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            LOG.error(f"Failed to get reservation for order {order_id}: {e}")
            return None
    
    # ========================================
    # Payment Operations
    # ========================================
    
    def create_payment(self, payment_id: str, order_id: str, amount: float, 
                      payment_method: str = "credit_card") -> bool:
        """Create a payment record"""
        try:
            now = datetime.utcnow().isoformat()
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO payments (payment_id, order_id, amount, 
                                        payment_method, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'PENDING', ?, ?)
                """, (payment_id, order_id, amount, payment_method, now, now))
            LOG.info(f"Payment created: {payment_id}")
            return True
        except Exception as e:
            LOG.error(f"Failed to create payment {payment_id}: {e}")
            return False
    
    def update_payment_status(self, payment_id: str, status: str) -> bool:
        """Update payment status"""
        try:
            now = datetime.utcnow().isoformat()
            with self.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE payments 
                    SET status = ?, updated_at = ?
                    WHERE payment_id = ?
                """, (status, now, payment_id))
            LOG.info(f"Payment {payment_id} status updated to {status}")
            return True
        except Exception as e:
            LOG.error(f"Failed to update payment {payment_id}: {e}")
            return False
    
    def get_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Get payment details"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            LOG.error(f"Failed to get payment {payment_id}: {e}")
            return None
    
    def clear_payments(self) -> bool:
        """Clear all payments"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("DELETE FROM payments")
            LOG.info("All payments cleared")
            return True
        except Exception as e:
            LOG.error(f"Failed to clear payments: {e}")
            return False
    
    # ========================================
    # Tracking Operations
    # ========================================
    
    def create_tracking(self, tracking_id: str, order_id: str, 
                       initial_status: str = "INITIATED") -> bool:
        """Create a tracking record"""
        try:
            now = datetime.utcnow().isoformat()
            status_history = initial_status
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO tracking (tracking_id, order_id, status, 
                                        status_history, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (tracking_id, order_id, initial_status, status_history, now, now))
            LOG.info(f"Tracking created: {tracking_id}")
            return True
        except Exception as e:
            LOG.error(f"Failed to create tracking {tracking_id}: {e}")
            return False
    
    def update_tracking_status(self, tracking_id: str, status: str) -> bool:
        """Update tracking status"""
        try:
            now = datetime.utcnow().isoformat()
            with self.get_cursor() as cursor:
                # Get current status history
                cursor.execute("""
                    SELECT status_history FROM tracking WHERE tracking_id = ?
                """, (tracking_id,))
                row = cursor.fetchone()
                
                if not row:
                    return False
                
                history = row['status_history']
                updated_history = f"{history},{status}"
                
                cursor.execute("""
                    UPDATE tracking 
                    SET status = ?, status_history = ?, updated_at = ?
                    WHERE tracking_id = ?
                """, (status, updated_history, now, tracking_id))
            LOG.info(f"Tracking {tracking_id} status updated to {status}")
            return True
        except Exception as e:
            LOG.error(f"Failed to update tracking {tracking_id}: {e}")
            return False
    
    def get_tracking(self, tracking_id: str) -> Optional[Dict[str, Any]]:
        """Get tracking details"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT * FROM tracking WHERE tracking_id = ?", (tracking_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            LOG.error(f"Failed to get tracking {tracking_id}: {e}")
            return None
    
    def clear_tracking(self) -> bool:
        """Clear all tracking records"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("DELETE FROM tracking")
            LOG.info("All tracking records cleared")
            return True
        except Exception as e:
            LOG.error(f"Failed to clear tracking: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if hasattr(self.local, "conn"):
            self.local.conn.close()
            LOG.info("Database connection closed")


# Singleton database instance
_db_instance = None

def get_database(db_path: str = "retail.db") -> Database:
    """Get or create database singleton instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(db_path)
    return _db_instance
