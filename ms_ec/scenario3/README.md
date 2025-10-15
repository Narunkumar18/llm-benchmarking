# Scenario 4: gRPC Microservices E-Commerce System

## Overview

A comprehensive microservices-based e-commerce system built with **gRPC** and **Protocol Buffers**, implementing:

- ✅ **Complete Order Workflow**: Validation → Inventory → Payment → Tracking
- ✅ **Real-time Tracking**: Multi-stage order tracking with automatic progression
- ✅ **Sequential & Parallel Processing**: Configurable workflow execution
- ✅ **SQLite Database**: Thread-safe persistence layer
- ✅ **Performance Metrics**: Request/response sizes, timing, CPU usage
- ✅ **Atomic Operations**: Race condition prevention
- ✅ **Comprehensive Testing**: Parallel and sequential order placement experiments

## Architecture

```
┌─────────────────────┐
│   Order Service     │ (Port 50050) - Orchestrates workflow
└──────────┬──────────┘
           │
           ├─────────► Inventory Service (Port 50051) - Stock management
           │
           ├─────────► Payment Service   (Port 50052) - Payment processing
           │
           └─────────► Tracking Service  (Port 50053) - Real-time tracking
```

### Communication Flow

```
Client → Order Service → [Inventory Check] → [Inventory Reserve]
                      → [Payment Process] ──┐
                      → [Tracking Initiate] ─┤
                                              ├→ [Sequential/Parallel]
                      ← [Response] ←─────────┘
```

## Features

### 🎯 Complete Order Processing

1. **Order Validation**: Product and quantity validation
2. **Inventory Checking**: Real-time stock availability verification
3. **Inventory Reservation**: Atomic stock reservation with rollback support
4. **Payment Processing**: Secure payment validation and processing
5. **Real-time Tracking**: Multi-stage tracking with automatic updates

### 🔄 Processing Modes

#### Sequential Workflow
- Steps executed one after another
- Payment → Tracking
- More predictable timing
- Lower concurrency overhead

#### Parallel Workflow
- Payment and Tracking executed concurrently
- Faster overall processing
- Better resource utilization
- ~1.5-2x speedup

### 📊 Tracking Stages

Orders progress through the following stages automatically:

1. `INITIATED` - Tracking started
2. `PROCESSING` - Order being processed
3. `SHIPPED` - Order shipped
4. `IN_TRANSIT` - In delivery
5. `OUT_FOR_DELIVERY` - Out for final delivery
6. `DELIVERED` - Completed

### 💾 Database Schema

**SQLite Tables:**

- `orders` - Order information and status
- `inventory` - Product stock levels
- `reservations` - Stock reservations
- `payments` - Payment records
- `tracking` - Order tracking status

## Quick Start

### Prerequisites

```bash
Python 3.8+
```

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate Proto Files

```bash
chmod +x generate_proto.sh
./generate_proto.sh
```

This generates:
- `proto/retail_pb2.py` - Message definitions
- `proto/retail_pb2_grpc.py` - Service stubs

### 3. Start All Services

```bash
chmod +x start_services.sh
./start_services.sh
```

Services will start on:
- Order Service: `localhost:50050`
- Inventory Service: `localhost:50051`
- Payment Service: `localhost:50052`
- Tracking Service: `localhost:50053`

### 4. Test Services

```bash
chmod +x test_services.sh
./test_services.sh
```

### 5. Run Experiments

```bash
python run_trial.py
```

Select from:
1. Parallel Orders - Sequential Workflow
2. Parallel Orders - Parallel Workflow
3. Sequential Orders - Sequential Workflow
4. Sequential Orders - Parallel Workflow
5. Run All Experiments

### 6. Stop Services

```bash
chmod +x stop_services.sh
./stop_services.sh
```

## Services Documentation

### Order Service (Port 50050)

**Purpose**: Orchestrates the complete order workflow

**Methods:**
- `CreateOrder` - Process new order with full workflow
- `GetOrderStatus` - Retrieve order details
- `ClearOrders` - Clear all orders (testing)

**Workflow:**
1. Create order record
2. Reserve inventory
3. Process payment (sequential or parallel with tracking)
4. Initiate tracking
5. Update order status
6. Commit reservation

### Inventory Service (Port 50051)

**Purpose**: Manages product inventory and reservations

**Methods:**
- `CheckStock` - Check product availability
- `ReserveStock` - Atomically reserve stock
- `ReleaseStock` - Release reservation (rollback)
- `InitializeStock` - Add/update product stock
- `ClearInventory` - Clear all inventory (testing)

**Features:**
- Atomic stock operations
- Race condition prevention
- Reservation tracking
- Automatic rollback support

### Payment Service (Port 50052)

**Purpose**: Handles payment processing and validation

**Methods:**
- `ProcessPayment` - Process and validate payment
- `GetPaymentStatus` - Retrieve payment details
- `ClearPayments` - Clear all payments (testing)

**Features:**
- Payment validation
- Multiple payment methods support
- 99% success simulation rate
- Status tracking

### Tracking Service (Port 50053)

**Purpose**: Manages real-time order tracking

**Methods:**
- `InitiateTracking` - Start tracking for order
- `UpdateTrackingStatus` - Manually update status
- `GetTrackingStatus` - Retrieve tracking details
- `ClearTracking` - Clear all tracking (testing)

**Features:**
- Automatic status progression
- Status history tracking
- Real-time updates
- Background task management

## Experiment Types

### Parallel Order Placement

Tests concurrent order processing with race condition handling.

**Configuration:**
- Multiple threads place orders simultaneously
- Initial stock: 10 units
- Concurrent orders: 100
- Expected: Exactly 10 orders succeed

**Purpose:**
- Test atomic operations
- Verify race condition handling
- Measure concurrency performance
- Validate overselling prevention

### Sequential Order Placement

Tests ordered request processing.

**Configuration:**
- Orders placed one at a time
- Initial stock: 10 units
- Total orders: 100
- Expected: Exactly 10 orders succeed

**Purpose:**
- Baseline performance measurement
- Verify sequential correctness
- Compare with parallel performance

## Performance Metrics

The system tracks comprehensive metrics:

### Timing Metrics
- **Total Time**: End-to-end order processing
- **Inventory Time**: Stock reservation duration
- **Payment Time**: Payment processing duration
- **Tracking Time**: Tracking initiation duration
- **CPU Time**: CPU usage per operation

### Size Metrics
- **Request Bytes**: Protobuf message sizes (requests)
- **Response Bytes**: Protobuf message sizes (responses)
- **Total Payload**: Combined request/response sizes

### Performance Comparison

**gRPC vs REST:**
- Serialization: ~10-50x faster (Protobuf vs JSON)
- Message Size: ~3-10x smaller
- Transport: HTTP/2 multiplexing
- Concurrency: Better under load

## Database Layer

### Thread-Safe Operations

All database operations use thread-local connections with context managers:

```python
with db.get_cursor() as cursor:
    cursor.execute("...")
    # Auto-commit on success
    # Auto-rollback on error
```

### Atomic Operations

Critical operations use database-level atomicity:

```python
# Atomic stock reservation
cursor.execute("""
    UPDATE inventory 
    SET reserved = reserved + ?
    WHERE product_id = ? AND (stock - reserved) >= ?
""")
```

## Testing

### Unit Testing

Run individual service tests:

```bash
python -m pytest tests/
```

### Integration Testing

Full workflow testing:

```bash
python test_integration.py
```

### Load Testing

Stress test with high concurrency:

```bash
python run_trial.py
# Select option 5 for all experiments
```

## Logs

Service logs are stored in the `logs/` directory:

```
logs/
├── Order.log
├── Inventory.log
├── Payment.log
└── Tracking.log
```

View logs in real-time:

```bash
tail -f logs/Order.log
```

## Troubleshooting

### Services Won't Start

**Problem**: Port already in use

**Solution:**
```bash
./stop_services.sh
lsof -ti:50050,50051,50052,50053 | xargs kill -9
./start_services.sh
```

### Proto Generation Fails

**Problem**: `grpc_tools` not installed

**Solution:**
```bash
pip install grpcio-tools
./generate_proto.sh
```

### Database Locked

**Problem**: SQLite database locked

**Solution:**
```bash
rm retail.db
./start_services.sh
```

### Connection Refused

**Problem**: Services not running

**Solution:**
```bash
./test_services.sh  # Check service status
./start_services.sh  # Start if needed
```

## Configuration

### Service Ports

Edit service files to change ports:

```python
# inventory_service_grpc.py
async def serve(host="0.0.0.0", port=50051):
```

### Database Path

Edit `database.py`:

```python
def get_database(db_path: str = "retail.db"):
```

### Delays

Configure artificial delays for testing:

```python
# In run_trial.py
DELAY_MS = 100  # milliseconds
```

## Project Structure

```
scenario4/
├── proto/
│   ├── retail.proto          # Protobuf definitions
│   ├── retail_pb2.py         # Generated messages
│   └── retail_pb2_grpc.py    # Generated services
├── database.py               # SQLite database layer
├── inventory_service_grpc.py # Inventory gRPC service
├── payment_service_grpc.py   # Payment gRPC service
├── tracking_service_grpc.py  # Tracking gRPC service
├── order_service_grpc.py     # Order orchestration service
├── run_trial.py              # Experiment runner
├── generate_proto.sh         # Proto generation script
├── start_services.sh         # Start all services
├── stop_services.sh          # Stop all services
├── test_services.sh          # Service connectivity test
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── logs/                     # Service logs (created at runtime)
```

## Results

Experiment results are saved as text files:

- `ms_sc4_parallel_sequential.txt` - Parallel orders, sequential workflow
- `ms_sc4_parallel_parallel.txt` - Parallel orders, parallel workflow
- `ms_sc4_sequential_sequential.txt` - Sequential orders, sequential workflow
- `ms_sc4_sequential_parallel.txt` - Sequential orders, parallel workflow

Each file contains:
- Configuration details
- Per-trial results
- Timing metrics
- Success/failure counts
- Overall summary

## API Example

### Python Client

```python
import grpc
from proto import retail_pb2 as pb
from proto import retail_pb2_grpc as rpc

# Connect to order service
channel = grpc.insecure_channel('localhost:50050')
stub = rpc.OrderServiceStub(channel)

# Create order
request = pb.CreateOrderRequest(
    product_id="LAPTOP001",
    quantity=1,
    amount=999.99,
    parallel_processing=True,
    delay_ms=0
)

response = stub.CreateOrder(request)
print(f"Order: {response.order_id}")
print(f"Status: {response.status}")
print(f"Payment: {response.payment_id}")
print(f"Tracking: {response.tracking_id}")
```

## Advanced Usage

### Custom Workflow

Modify `order_service_grpc.py` to customize the workflow:

```python
async def CreateOrder(self, request, context):
    # Add custom validation
    if request.amount < 0:
        return error_response("Invalid amount")
    
    # Add custom processing
    await self._custom_processing()
    
    # Continue with standard workflow
    ...
```

### Database Inspection

Query the database directly:

```bash
sqlite3 retail.db
```

```sql
-- View all orders
SELECT * FROM orders;

-- Check inventory
SELECT * FROM inventory;

-- View payments
SELECT * FROM payments;

-- Track orders
SELECT * FROM tracking;
```

## Performance Tuning

### Thread Pool Size

Adjust executor threads in services:

```python
executor = ThreadPoolExecutor(max_workers=50)
```

### gRPC Options

Configure gRPC server:

```python
server = grpc.aio.server(
    options=[
        ('grpc.max_send_message_length', 10 * 1024 * 1024),
        ('grpc.max_receive_message_length', 10 * 1024 * 1024),
    ]
)
```

### Database Optimization

Enable WAL mode for better concurrency:

```python
conn.execute("PRAGMA journal_mode=WAL")
```

## License

MIT License - Free to use and modify

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review service logs in `logs/`
3. Verify all services are running with `./test_services.sh`

## Contributing

Contributions welcome! Please:
1. Follow existing code style
2. Add tests for new features
3. Update documentation
4. Test all workflows

## Authors

Created for LLM benchmarking research - Scenario 4: gRPC Microservices Implementation
