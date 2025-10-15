# Scenario 5: Comprehensive Pipeline Diagram

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLIENT APPLICATION                               │
│                         (run_trial.py)                                   │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ gRPC/HTTP2
                               │ Port: 50050
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ORDER SERVICE (Main Orchestrator)                     │
│                    order_service_grpc.py                                 │
│                    Port: 50050                                           │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  CreateOrder RPC Handler                                     │       │
│  │  - Validates request                                         │       │
│  │  - Coordinates workflow (Sequential/Parallel)                │       │
│  │  - Manages distributed transactions                          │       │
│  │  - Handles rollback on failures                              │       │
│  └─────────────────────────────────────────────────────────────┘       │
└───┬─────────────────┬─────────────────┬─────────────────────────────────┘
    │                 │                 │
    │ gRPC/HTTP2      │ gRPC/HTTP2      │ gRPC/HTTP2
    │ Port: 50051     │ Port: 50052     │ Port: 50053
    ▼                 ▼                 ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│INVENTORY │    │ PAYMENT  │    │TRACKING  │
│ SERVICE  │    │ SERVICE  │    │ SERVICE  │
│Port:50051│    │Port:50052│    │Port:50053│
└────┬─────┘    └────┬─────┘    └────┬─────┘
     │               │               │
     │               │               │
     └───────────────┴───────────────┘
                     │
                     ▼
         ┌──────────────────────┐
         │   SQLite Database    │
         │   (Thread-Safe)      │
         │                      │
         │  Tables:             │
         │  - orders            │
         │  - inventory         │
         │  - reservations      │
         │  - payments          │
         │  - tracking_events   │
         └──────────────────────┘
```

## Workflow Pipelines

### Pipeline 1: Sequential Workflow (Step-by-Step)

```
Client Request
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Inventory Reservation                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Order Service → Inventory Service                        │ │
│ │ RPC: ReserveStock(product_id, quantity)                  │ │
│ │                                                           │ │
│ │ Inventory Service:                                        │ │
│ │ 1. Check stock availability                              │ │
│ │ 2. Create reservation record                             │ │
│ │ 3. Decrement available stock atomically                  │ │
│ │ 4. Return reservation_id or failure                      │ │
│ └─────────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │ Success?
                         │
            ┌────────────┴────────────┐
            │ YES                     │ NO
            ▼                         ▼
┌─────────────────────────────┐  ┌──────────────────┐
│ STEP 2: Payment Processing  │  │ Return FAILED    │
│ ┌─────────────────────────┐ │  │ OUT_OF_STOCK     │
│ │ Order Service →         │ │  └──────────────────┘
│ │ Payment Service         │ │
│ │                         │ │
│ │ RPC: ProcessPayment(    │ │
│ │   order_id, amount,     │ │
│ │   payment_method)       │ │
│ │                         │ │
│ │ Payment Service:        │ │
│ │ 1. Validate payment     │ │
│ │ 2. Process transaction  │ │
│ │ 3. Create payment record│ │
│ │ 4. Return payment_id    │ │
│ └─────────────────────────┘ │
└──────────┬──────────────────┘
           │ Success?
           │
    ┌──────┴──────┐
    │ YES         │ NO
    ▼             ▼
┌────────────┐  ┌─────────────────────┐
│ STEP 3:    │  │ ROLLBACK:           │
│ Tracking   │  │ Release Reservation │
│ Initiation │  │ Return FAILED       │
│            │  │ PAYMENT_FAILED      │
│ Order      │  └─────────────────────┘
│ Service →  │
│ Tracking   │
│ Service    │
│            │
│ RPC:       │
│ Initiate   │
│ Tracking(  │
│  order_id) │
│            │
│ Tracking   │
│ Service:   │
│ 1. Create  │
│    tracking│
│    record  │
│ 2. Start   │
│    auto-   │
│    progress│
│ 3. Return  │
│    tracking│
│    _id     │
└──────┬─────┘
       │
       ▼
┌──────────────┐
│ STEP 4:      │
│ Finalize     │
│ Order        │
│              │
│ 1. Update    │
│    order     │
│    status to │
│    COMPLETED │
│ 2. Store all │
│    IDs       │
│ 3. Return    │
│    response  │
└──────────────┘
```

### Pipeline 2: Parallel Workflow (Concurrent Execution)

```
Client Request
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Inventory Reservation (Same as Sequential)          │
│ Order Service → Inventory Service                            │
│ RPC: ReserveStock(product_id, quantity)                      │
└────────────────────────┬────────────────────────────────────┘
                         │ Success?
                         │
            ┌────────────┴────────────┐
            │ YES                     │ NO
            ▼                         ▼
┌───────────────────────────────────────────────┐  ┌────────────┐
│ STEP 2 & 3: Parallel Execution               │  │ Return     │
│ ┌────────────────────┬────────────────────┐  │  │ FAILED     │
│ │                    │                    │  │  │ OUT_OF     │
│ │ Thread Pool        │ Thread Pool        │  │  │ _STOCK     │
│ │ Executor           │ Executor           │  │  └────────────┘
│ │                    │                    │  │
│ ▼                    ▼                    │  │
│ ┌──────────────┐   ┌──────────────┐      │  │
│ │ Payment      │   │ Tracking     │      │  │
│ │ Processing   │   │ Initiation   │      │  │
│ │              │   │              │      │  │
│ │ Order Svc →  │   │ Order Svc →  │      │  │
│ │ Payment Svc  │   │ Tracking Svc │      │  │
│ │              │   │              │      │  │
│ │ RPC:         │   │ RPC:         │      │  │
│ │ Process      │   │ Initiate     │      │  │
│ │ Payment()    │   │ Tracking()   │      │  │
│ └──────┬───────┘   └──────┬───────┘      │  │
│        │                  │              │  │
│        └────────┬─────────┘              │  │
│                 │ Wait for both          │  │
│                 │ to complete            │  │
│                 ▼                        │  │
│         ┌──────────────────┐            │  │
│         │ Check Results:   │            │  │
│         │ - Both Success?  │            │  │
│         │ - Any Failure?   │            │  │
│         └────────┬─────────┘            │  │
└──────────────────┼──────────────────────┘  │
                   │                          │
         ┌─────────┴─────────┐               │
         │                   │               │
      SUCCESS            FAILURE             │
         │                   │               │
         ▼                   ▼               │
┌──────────────┐    ┌──────────────────┐    │
│ STEP 4:      │    │ ROLLBACK:        │    │
│ Finalize     │    │ - Release        │    │
│ Order        │    │   Reservation    │    │
│              │    │ - Rollback       │    │
│ Update to    │    │   Payment if     │    │
│ COMPLETED    │    │   successful     │    │
│              │    │ - Return FAILED  │    │
└──────────────┘    └──────────────────┘    │
```

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        DATA FLOW LAYERS                           │
└──────────────────────────────────────────────────────────────────┘

Layer 1: REQUEST/RESPONSE (Protocol Buffers - Binary Serialization)
─────────────────────────────────────────────────────────────────────
Client                        Order Service
  │                                │
  │ CreateOrderRequest             │
  │ {                              │
  │   customer_id: "CUST001"       │
  │   product_id: "LAPTOP001"      │
  │   quantity: 2                  │
  │   amount: 2499.98              │
  │   payment_method: "credit_card"│
  │   use_parallel: true           │
  │ }                              │
  ├────────────────────────────────►
  │                                │
  │ CreateOrderResponse            │
  │ {                              │
  │   order_id: "uuid-123"         │
  │   status: "COMPLETED"          │
  │   message: "Order successful"  │
  │   payment_id: "uuid-456"       │
  │   tracking_id: "uuid-789"      │
  │   timestamp: "2025-10-15..."   │
  │ }                              │
  ◄────────────────────────────────┤
  │                                │

Layer 2: INTER-SERVICE COMMUNICATION (gRPC Channels)
─────────────────────────────────────────────────────────────────────
Order Service          Inventory Service      Payment Service    Tracking Service
     │                        │                      │                  │
     │ ReserveStockRequest    │                      │                  │
     │ {                      │                      │                  │
     │   product_id: "..."    │                      │                  │
     │   quantity: 2          │                      │                  │
     │   order_id: "..."      │                      │                  │
     │ }                      │                      │                  │
     ├────────────────────────►                      │                  │
     │                        │                      │                  │
     │ ReserveStockResponse   │                      │                  │
     │ {                      │                      │                  │
     │   success: true        │                      │                  │
     │   reservation_id: "..." │                     │                  │
     │   available: 8         │                      │                  │
     │ }                      │                      │                  │
     ◄────────────────────────┤                      │                  │
     │                        │                      │                  │
     │                   ProcessPaymentRequest       │                  │
     │                   {                           │                  │
     │                     order_id: "..."           │                  │
     │                     amount: 2499.98           │                  │
     │                     payment_method: "cc"      │                  │
     │                   }                           │                  │
     ├───────────────────────────────────────────────►                  │
     │                        │                      │                  │
     │                   ProcessPaymentResponse      │                  │
     │                   {                           │                  │
     │                     success: true             │                  │
     │                     payment_id: "..."         │                  │
     │                     transaction_id: "..."     │                  │
     │                   }                           │                  │
     ◄───────────────────────────────────────────────┤                  │
     │                        │                      │                  │
     │                        │                  InitiateTrackingRequest│
     │                        │                  {                      │
     │                        │                    order_id: "..."      │
     │                        │                  }                      │
     ├────────────────────────────────────────────────────────────────►│
     │                        │                      │                  │
     │                        │                  InitiateTrackingResponse
     │                        │                  {                      │
     │                        │                    success: true        │
     │                        │                    tracking_id: "..."   │
     │                        │                    status: "PENDING"    │
     │                        │                  }                      │
     ◄────────────────────────────────────────────────────────────────┤
     │                        │                      │                  │

Layer 3: DATABASE OPERATIONS (SQLite with Thread Safety)
─────────────────────────────────────────────────────────────────────
Inventory Service          Payment Service          Tracking Service
     │                          │                          │
     ▼                          ▼                          ▼
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│ INVENTORY   │         │ PAYMENTS    │         │ TRACKING    │
│ TABLE       │         │ TABLE       │         │ EVENTS      │
│             │         │             │         │ TABLE       │
│ - product_id│         │ - payment_id│         │ - tracking_ │
│ - total     │         │ - order_id  │         │   id        │
│ - available │         │ - amount    │         │ - order_id  │
│ - reserved  │         │ - method    │         │ - status    │
│             │         │ - status    │         │ - timestamp │
└─────────────┘         └─────────────┘         └─────────────┘
     │                          │                          │
     ▼                          ▼                          ▼
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│RESERVATIONS │         │   ORDERS    │         │   ORDERS    │
│ TABLE       │         │   TABLE     │         │   TABLE     │
│             │         │             │         │             │
│ - reserv_id │         │ - order_id  │         │ - order_id  │
│ - order_id  │         │ - payment_id│         │ - tracking  │
│ - product_id│         │ - customer  │         │   _id       │
│ - quantity  │         │ - status    │         │ - status    │
│ - status    │         │ - amount    │         │             │
└─────────────┘         └─────────────┘         └─────────────┘
```

## Experiment Execution Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    run_trial.py Execution Flow                  │
└─────────────────────────────────────────────────────────────────┘

Start
  │
  ▼
┌─────────────────────────────────┐
│ 1. Initialize Database          │
│    - Create tables              │
│    - Insert 10 laptop units     │
│    - Set test parameters        │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ 2. Verify Services Reachable    │
│    - Check Order Service        │
│    - Check Inventory Service    │
│    - Check Payment Service      │
│    - Check Tracking Service     │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ 3. Display Experiment Menu      │
│    [1] Parallel Orders -        │
│        Sequential Workflow      │
│    [2] Parallel Orders -        │
│        Parallel Workflow        │
│    [3] Sequential Orders -      │
│        Sequential Workflow      │
│    [4] Sequential Orders -      │
│        Parallel Workflow        │
│    [5] Run All Experiments      │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Execute Selected Experiment(s)                           │
│                                                              │
│ For each experiment:                                         │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ A. Pre-Experiment Setup                                │ │
│ │    - Reset database                                    │ │
│ │    - Initialize inventory (10 units)                   │ │
│ │    - Start CPU/time monitoring                         │ │
│ │    - Prepare 100 order requests                        │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ B. Order Submission                                    │ │
│ │                                                         │ │
│ │    IF Parallel Orders:                                 │ │
│ │    ┌─────────────────────────────────────────────────┐│ │
│ │    │ - Create ThreadPoolExecutor(max_workers=10)     ││ │
│ │    │ - Submit all 100 orders concurrently            ││ │
│ │    │ - Use tqdm progress bar                         ││ │
│ │    │ - Collect futures.as_completed()                ││ │
│ │    └─────────────────────────────────────────────────┘│ │
│ │                                                         │ │
│ │    IF Sequential Orders:                               │ │
│ │    ┌─────────────────────────────────────────────────┐│ │
│ │    │ - Loop through 100 orders one by one            ││ │
│ │    │ - Make synchronous gRPC calls                   ││ │
│ │    │ - Use tqdm progress bar                         ││ │
│ │    └─────────────────────────────────────────────────┘│ │
│ │                                                         │ │
│ │    Each order includes:                                │ │
│ │    - use_parallel flag (for workflow selection)        │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ C. Result Collection & Analysis                        │ │
│ │    - Measure total execution time                      │ │
│ │    - Calculate CPU time used                           │ │
│ │    - Measure request/response payload sizes            │ │
│ │    - Count success vs. failures                        │ │
│ │    - Categorize failures (out_of_stock vs. payment)    │ │
│ │    - Calculate percentages                             │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ D. Report Generation                                   │ │
│ │    - Format results table                              │ │
│ │    - Include timing metrics                            │ │
│ │    - Include payload metrics                           │ │
│ │    - Save to ms_sc5_{order}_{workflow}.txt             │ │
│ │    - Display summary to console                        │ │
│ └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ 5. Final Summary                │
│    - Total experiments run      │
│    - All results file locations │
│    - Performance comparison     │
└─────────────────────────────────┘
         │
         ▼
       End
```

## Rollback/Error Handling Pipeline

```
┌─────────────────────────────────────────────────────────┐
│              ERROR HANDLING & ROLLBACK FLOW             │
└─────────────────────────────────────────────────────────┘

Order Request
     │
     ▼
┌──────────────────┐
│ Reserve Stock    │
└────┬─────────────┘
     │
   ┌─┴─┐
   │ ? │ Success?
   └─┬─┘
     │
 ┌───┴───┐
 │       │
NO      YES
 │       │
 │       ▼
 │  ┌──────────────────┐
 │  │ Process Payment  │
 │  └────┬─────────────┘
 │       │
 │     ┌─┴─┐
 │     │ ? │ Success?
 │     └─┬─┘
 │       │
 │   ┌───┴───┐
 │   │       │
 │  NO      YES
 │   │       │
 │   │       ▼
 │   │  ┌──────────────────┐
 │   │  │ Initiate Tracking│
 │   │  └────┬─────────────┘
 │   │       │
 │   │     ┌─┴─┐
 │   │     │ ? │ Success?
 │   │     └─┬─┘
 │   │       │
 │   │   ┌───┴───┐
 │   │   │       │
 │   │  NO      YES
 │   │   │       │
 │   │   │       ▼
 │   │   │  ┌────────────┐
 │   │   │  │ COMPLETED  │
 │   │   │  │ Return     │
 │   │   │  │ Success    │
 │   │   │  └────────────┘
 │   │   │
 │   │   └──► ┌─────────────────────────┐
 │   │        │ TRACKING FAILED         │
 │   │        │ Actions:                │
 │   │        │ 1. Rollback Payment     │
 │   │        │    - Void transaction   │
 │   │        │ 2. Release Reservation  │
 │   │        │    - Free inventory     │
 │   │        │ 3. Update order status  │
 │   │        │    to FAILED            │
 │   │        │ 4. Return error response│
 │   │        └─────────────────────────┘
 │   │
 │   └──────► ┌─────────────────────────┐
 │            │ PAYMENT FAILED          │
 │            │ Actions:                │
 │            │ 1. Release Reservation  │
 │            │    - Free inventory     │
 │            │ 2. Update order status  │
 │            │    to FAILED_PAYMENT    │
 │            │ 3. Return error response│
 │            └─────────────────────────┘
 │
 └──────────► ┌─────────────────────────┐
              │ OUT OF STOCK            │
              │ Actions:                │
              │ 1. Update order status  │
              │    to FAILED_OUT_OF_STOCK│
              │ 2. No rollback needed   │
              │    (no reservation made)│
              │ 3. Return error response│
              └─────────────────────────┘
```

## Performance Monitoring Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│              METRICS COLLECTION & MONITORING                 │
└─────────────────────────────────────────────────────────────┘

Experiment Start
     │
     ▼
┌──────────────────────────────────┐
│ Initialize Monitors              │
│ - psutil.Process(os.getpid())    │
│ - Start wall clock time          │
│ - Initialize payload counters    │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ During Execution                 │
│ ┌──────────────────────────────┐ │
│ │ For each order:              │ │
│ │                              │ │
│ │ Request Payload:             │ │
│ │ - Serialize protobuf msg     │ │
│ │ - Measure byte size          │ │
│ │ - Accumulate to total        │ │
│ │                              │ │
│ │ Response Payload:            │ │
│ │ - Receive protobuf msg       │ │
│ │ - Measure byte size          │ │
│ │ - Accumulate to total        │ │
│ │                              │ │
│ │ Timing:                      │ │
│ │ - Record individual latency  │ │
│ │ - Track min/max/avg          │ │
│ └──────────────────────────────┘ │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Post-Execution Analysis          │
│                                  │
│ Wall Clock Time:                 │
│ - Total elapsed seconds          │
│                                  │
│ CPU Time:                        │
│ - User mode CPU time             │
│ - System mode CPU time           │
│ - Total = user + system          │
│                                  │
│ Payload Metrics:                 │
│ - Total request bytes            │
│ - Total response bytes           │
│ - Average per order              │
│                                  │
│ Success Rate:                    │
│ - Completed orders               │
│ - Failed orders (by type)        │
│ - Percentage calculations        │
│                                  │
│ Throughput:                      │
│ - Orders per second              │
│ - Requests per second            │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ Report Generation                │
│ - Format metrics table           │
│ - Include all measurements       │
│ - Add comparison notes           │
│ - Save to text file              │
└──────────────────────────────────┘
```

## Technology Stack Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    TECHNOLOGY STACK LAYERS                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Layer 7: Client Layer                                        │
│ - Python asyncio event loop                                  │
│ - ThreadPoolExecutor for parallel order submission           │
│ - tqdm for progress visualization                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 6: RPC Framework                                       │
│ - gRPC (Python: grpcio, grpcio-tools)                        │
│ - Protocol Buffers 3 (protobuf compiler)                     │
│ - HTTP/2 transport protocol                                  │
│ - Binary serialization (10-50x smaller than JSON)            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 5: Service Layer                                       │
│ - Python 3.8+ asyncio                                        │
│ - grpc.aio async/await server                                │
│ - ThreadPoolExecutor for blocking DB operations              │
│ - Exception handling & error propagation                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Business Logic Layer                                │
│ - Order orchestration & workflow coordination                │
│ - Inventory management & atomic reservations                 │
│ - Payment processing & validation                            │
│ - Tracking status progression                                │
│ - Distributed transaction handling                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Data Access Layer                                   │
│ - database.py abstraction                                    │
│ - Thread-safe connection pooling                             │
│ - Context managers for transactions                          │
│ - Atomic operations with proper locking                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Database Layer                                      │
│ - SQLite3 (embedded database)                                │
│ - ACID transaction support                                   │
│ - Row-level locking                                          │
│ - Auto-incrementing IDs                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Monitoring & Observability                          │
│ - psutil for CPU/memory metrics                              │
│ - Custom timing measurements                                 │
│ - Payload size tracking                                      │
│ - Result aggregation & reporting                             │
└─────────────────────────────────────────────────────────────┘
```

## Summary

This comprehensive pipeline diagram illustrates:

1. **Architecture**: 4 microservices communicating via gRPC over HTTP/2
2. **Workflows**: Sequential vs. Parallel execution strategies
3. **Data Flow**: From client request through service mesh to database
4. **Error Handling**: Comprehensive rollback mechanisms
5. **Experimentation**: Systematic testing framework with 4 scenarios
6. **Monitoring**: Multi-layered performance tracking
7. **Technology Stack**: Modern async Python with gRPC

**Key Performance Characteristics:**
- **Protocol**: gRPC with binary serialization (smaller payloads)
- **Concurrency**: Asyncio + ThreadPoolExecutor (efficient resource usage)
- **Database**: SQLite with thread-safe operations (ACID guarantees)
- **Resilience**: Automatic rollback on failures (data consistency)
- **Scalability**: Parallel workflows reduce latency by ~50%

**Expected Results:**
- 10 orders succeed (stock available)
- 90 orders fail with OUT_OF_STOCK
- Parallel execution significantly faster than sequential
- gRPC payloads 10-50x smaller than equivalent JSON/REST
