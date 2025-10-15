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






## Authors

Created for LLM benchmarking research - Scenario 4: gRPC Microservices Implementation
