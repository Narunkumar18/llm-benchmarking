# Scenario 4 Architecture Diagrams

## System Overview

```
┌────────────────────────────────────────────────────────────────┐
│                        Client/Test Runner                       │
│                         (run_trial.py)                          │
└───────────────────────────┬────────────────────────────────────┘
                            │ gRPC over HTTP/2
                            ▼
        ┌───────────────────────────────────────┐
        │       Order Service (Port 50050)       │
        │    • Workflow Orchestration            │
        │    • Sequential/Parallel Processing    │
        │    • Rollback Management               │
        └───────────┬───────────────────────────┘
                    │
        ┌───────────┼────────────┬──────────────┐
        │           │            │              │
        ▼           ▼            ▼              ▼
┌─────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  Inventory  │ │ Payment  │ │ Tracking │ │ Database │
│ Port 50051  │ │Port 50052│ │Port 50053│ │ (SQLite) │
│             │ │          │ │          │ │          │
│• Check      │ │• Process │ │• Initiate│ │• Orders  │
│• Reserve    │ │• Validate│ │• Update  │ │• Inventory│
│• Release    │ │• Status  │ │• Query   │ │• Payments│
│• Initialize │ │          │ │          │ │• Tracking│
└─────────────┘ └──────────┘ └──────────┘ └──────────┘
```

## Sequential Workflow

```
Client Request
     │
     ▼
┌─────────────────┐
│  Order Service  │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Step 1  │ Check & Reserve Inventory
    └────┬────┘
         │
    ┌────┴────┐
    │ Step 2  │ Process Payment
    └────┬────┘
         │
    ┌────┴────┐
    │ Step 3  │ Initiate Tracking
    └────┬────┘
         │
         ▼
     Response

Timeline:
├────┤ Inventory (T1)
     ├────┤ Payment (T2)
          ├────┤ Tracking (T3)

Total Time = T1 + T2 + T3
```

## Parallel Workflow

```
Client Request
     │
     ▼
┌─────────────────┐
│  Order Service  │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Step 1  │ Check & Reserve Inventory
    └────┬────┘
         │
    ┌────┴────────────┐
    │                 │
┌───┴────┐      ┌─────┴────┐
│ Step 2a│      │ Step 2b  │
│ Payment│      │ Tracking │
└───┬────┘      └─────┬────┘
    │                 │
    └────────┬────────┘
             │
             ▼
         Response

Timeline:
├────┤ Inventory (T1)
     ├────┤ Payment (T2)
     ├────┤ Tracking (T3)

Total Time = T1 + max(T2, T3)
Speedup: ~1.5-2x
```

## Database Schema

```
┌─────────────────────────────────────────────────────────────┐
│                        retail.db                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────┐        ┌─────────────────┐             │
│  │    orders      │◄───┐   │  reservations   │             │
│  ├────────────────┤    │   ├─────────────────┤             │
│  │ order_id (PK)  │    └───│ order_id (FK)   │             │
│  │ product_id     │        │ reservation_id  │             │
│  │ quantity       │        │ product_id      │             │
│  │ amount         │        │ quantity        │             │
│  │ status         │        │ status          │             │
│  │ payment_id     │        └─────────────────┘             │
│  │ tracking_id    │                                         │
│  │ reservation_id │                                         │
│  └────────────────┘                                         │
│         │                                                    │
│         ├──────────────┐                                    │
│         │              │                                    │
│         ▼              ▼                                    │
│  ┌────────────────┐  ┌─────────────────┐                  │
│  │   payments     │  │    tracking     │                  │
│  ├────────────────┤  ├─────────────────┤                  │
│  │ payment_id(PK) │  │ tracking_id(PK) │                  │
│  │ order_id (FK)  │  │ order_id (FK)   │                  │
│  │ amount         │  │ status          │                  │
│  │ payment_method │  │ status_history  │                  │
│  │ status         │  │ created_at      │                  │
│  └────────────────┘  │ updated_at      │                  │
│                      └─────────────────┘                  │
│                                                             │
│  ┌─────────────────┐                                       │
│  │   inventory     │                                       │
│  ├─────────────────┤                                       │
│  │ product_id (PK) │                                       │
│  │ stock           │                                       │
│  │ reserved        │                                       │
│  │ updated_at      │                                       │
│  └─────────────────┘                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Order State Machine

```
┌──────────┐
│ INITIATED│
└─────┬────┘
      │ Create order in DB
      ▼
┌──────────┐
│PROCESSING│
└─────┬────┘
      │ Check inventory
      ▼
┌──────────────────────┐
│INVENTORY_RESERVED    │
└─────┬────────────────┘
      │
      ├─── Sequential ───┐
      │                  │
      │ Process Payment  │
      ▼                  │
┌──────────┐            │
│PAYMENT_OK│            │
└─────┬────┘            │
      │                 │
      │ Initiate Track  │
      ▼                 │
┌──────────┐            │
│TRACKING  │            │
│_INITIATED│            │
└─────┬────┘            │
      │                 │
      │                 │
      ├─── Parallel ────┤
      │                 │
      │  Payment ||     │
      │  Tracking       │
      │                 │
      ▼                 │
┌──────────┐            │
│COMPLETED │◄───────────┘
└──────────┘

Error Paths:
INVENTORY_RESERVED → FAILED_OUT_OF_STOCK (inventory unavailable)
PAYMENT_OK → FAILED_PAYMENT (payment failed → rollback)
```

## Tracking Progression

```
Order Placed
     │
     ▼
┌──────────┐
│INITIATED │  ← Initial state
└─────┬────┘
      │ (2s delay)
      ▼
┌──────────┐
│PROCESSING│  ← Order being processed
└─────┬────┘
      │ (2s delay)
      ▼
┌──────────┐
│ SHIPPED  │  ← Order shipped
└─────┬────┘
      │ (2s delay)
      ▼
┌──────────┐
│IN_TRANSIT│  ← In delivery
└─────┬────┘
      │ (2s delay)
      ▼
┌─────────────────┐
│OUT_FOR_DELIVERY │  ← Final delivery stage
└─────┬───────────┘
      │ (2s delay)
      ▼
┌──────────┐
│DELIVERED │  ← Completed
└──────────┘

Note: Progression happens automatically in background
```

## Error Handling Flow

```
┌─────────────┐
│ Order Start │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Reserve         │──✗──► FAILED_OUT_OF_STOCK
│ Inventory       │
└──────┬──────────┘
       │✓
       ▼
┌─────────────────┐
│ Process         │──✗──┐
│ Payment         │     │
└──────┬──────────┘     │
       │✓               │
       ▼                │
┌─────────────────┐     │
│ Initiate        │     │ Release
│ Tracking        │     │ Inventory
└──────┬──────────┘     │
       │✓               │
       ▼                ▼
┌─────────────────┐  ┌─────────────┐
│   COMPLETED     │  │FAILED_PAYMENT│
└─────────────────┘  └─────────────┘
```

## Request/Response Flow

```
Client
  │
  │ CreateOrderRequest {
  │   product_id: "LAPTOP001"
  │   quantity: 1
  │   amount: 999.99
  │   parallel_processing: true
  │ }
  │
  ▼
Order Service
  │
  ├──► Inventory Service
  │    Request: ReserveStockRequest
  │    Response: ReserveStockResponse
  │       { success, reservation_id }
  │
  ├──┬─► Payment Service (parallel)
  │  │   Request: ProcessPaymentRequest
  │  │   Response: ProcessPaymentResponse
  │  │      { success, payment_id }
  │  │
  │  └─► Tracking Service (parallel)
  │      Request: InitiateTrackingRequest
  │      Response: InitiateTrackingResponse
  │         { success, tracking_id }
  │
  ▼
Client
  CreateOrderResponse {
    success: true
    order_id: "uuid"
    payment_id: "uuid"
    tracking_id: "uuid"
    status: "COMPLETED"
    metrics: { ... }
  }
```

## gRPC Connection Pooling

```
┌──────────────────┐
│  Order Service   │
└────────┬─────────┘
         │
         │ Persistent Channels (HTTP/2)
         │
    ┌────┼────┬────────┐
    │    │    │        │
    ▼    ▼    ▼        ▼
┌────┐┌────┐┌────┐┌────────┐
│Inv ││Pay ││Trk ││Database│
└────┘└────┘└────┘└────────┘

Benefits:
• Connection reuse
• Lower latency
• HTTP/2 multiplexing
• Better throughput
```

## Testing Architecture

```
┌─────────────────────────────────────────┐
│          Test Runner (run_trial.py)      │
└───────────────┬─────────────────────────┘
                │
    ┌───────────┼───────────┬──────────────┐
    │           │           │              │
    ▼           ▼           ▼              ▼
Parallel    Parallel   Sequential    Sequential
Orders +    Orders +   Orders +      Orders +
Sequential  Parallel   Sequential    Parallel
Workflow    Workflow   Workflow      Workflow

Each Test:
├─ Clear all data
├─ Initialize stock (10 units)
├─ Place orders (100 orders)
├─ Collect metrics
│  ├─ Success count
│  ├─ Failure count
│  ├─ Timing data
│  ├─ CPU usage
│  └─ Payload sizes
└─ Generate report
```

## Deployment View

```
┌─────────────────────────────────────────────────────┐
│                    Host Machine                      │
│                                                      │
│  ┌────────────────┐  ┌────────────────┐            │
│  │ Order Service  │  │ Inventory Svc  │            │
│  │   :50050       │  │    :50051      │            │
│  └────────────────┘  └────────────────┘            │
│                                                      │
│  ┌────────────────┐  ┌────────────────┐            │
│  │ Payment Service│  │ Tracking Svc   │            │
│  │   :50052       │  │    :50053      │            │
│  └────────────────┘  └────────────────┘            │
│                                                      │
│  ┌──────────────────────────────────┐               │
│  │        SQLite Database           │               │
│  │         retail.db                │               │
│  └──────────────────────────────────┘               │
│                                                      │
│  ┌──────────────────────────────────┐               │
│  │         Logs Directory            │               │
│  │  • Order.log                     │               │
│  │  • Inventory.log                 │               │
│  │  • Payment.log                   │               │
│  │  • Tracking.log                  │               │
│  └──────────────────────────────────┘               │
└─────────────────────────────────────────────────────┘
```

## Thread Safety

```
┌───────────────────────────────────────┐
│          Database Layer               │
│                                       │
│  Thread 1     Thread 2     Thread 3  │
│     │            │            │       │
│     ▼            ▼            ▼       │
│  ┌──────────────────────────────┐   │
│  │   Thread-Local Connections   │   │
│  └──────────────────────────────┘   │
│     │            │            │       │
│     ▼            ▼            ▼       │
│  ┌──────────────────────────────┐   │
│  │    Context Managers          │   │
│  │    (auto commit/rollback)    │   │
│  └──────────────────────────────┘   │
│     │            │            │       │
│     └────────────┼────────────┘      │
│                  ▼                    │
│           ┌─────────────┐            │
│           │  SQLite DB  │            │
│           │ (WAL mode)  │            │
│           └─────────────┘            │
└───────────────────────────────────────┘
```

## Performance Optimization

```
Protocol Buffers
     │ 10-50x faster serialization
     │ 3-10x smaller messages
     ▼
HTTP/2
     │ Multiplexing
     │ Header compression
     │ Connection reuse
     ▼
Async/Await
     │ Non-blocking I/O
     │ Better concurrency
     │ Resource efficiency
     ▼
Thread Pool
     │ DB operations
     │ Controlled concurrency
     │ Resource management
     ▼
Atomic Operations
     │ Race condition prevention
     │ Data consistency
     │ No overselling
     ▼
Result: 2.5-3x faster than REST
```

---

These diagrams provide a comprehensive visual understanding of Scenario 4's architecture, workflows, and design decisions.
