class Order:
    def __init__(self, order_id, product_id, quantity, customer_id):
        self.order_id = order_id
        self.product_id = product_id
        self.quantity = quantity
        self.customer_id = customer_id
        self.status = 'pending'

class Inventory:
    def __init__(self):
        self.stock = {}  # {product_id: quantity}

    def check_stock(self, product_id, quantity):
        return self.stock.get(product_id, 0) >= quantity

    def update_stock(self, product_id, quantity):
        if self.check_stock(product_id, quantity):
            self.stock[product_id] -= quantity
            return True
        return False

class Payment:
    def __init__(self):
        self.transactions = []

    def process_payment(self, order_id, customer_id, amount):
        # Simulate payment processing
        self.transactions.append({
            'order_id': order_id,
            'customer_id': customer_id,
            'amount': amount,
            'status': 'completed'
        })
        return True

class RealTimeTracking:
    def __init__(self):
        self.tracking_info = {}  # {order_id: status}

    def update_status(self, order_id, status):
        self.tracking_info[order_id] = status

    def get_status(self, order_id):
        return self.tracking_info.get(order_id, 'unknown')
