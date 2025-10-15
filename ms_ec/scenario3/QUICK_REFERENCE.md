# Scenario 4 - Quick Reference Guide

## Setup (First Time)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate proto files
chmod +x *.sh
./generate_proto.sh

# 3. Start services
./start_services.sh

# 4. Test services
./test_services.sh
```

## Daily Usage

```bash
# Start services
./start_services.sh

# Run experiments
python run_trial.py

# Stop services
./stop_services.sh
```

## Service Ports

- Order Service: `50050`
- Inventory Service: `50051`
- Payment Service: `50052`
- Tracking Service: `50053`

## Common Commands

### View Logs
```bash
tail -f logs/Order.log
tail -f logs/Inventory.log
tail -f logs/Payment.log
tail -f logs/Tracking.log
```

### Check Service Status
```bash
./test_services.sh
```

### Clear Database
```bash
rm retail.db
```

### Regenerate Proto Files
```bash
./generate_proto.sh
```

### Kill All Services
```bash
./stop_services.sh
pkill -f "service_grpc.py"
```

## Experiment Types

1. **Parallel Orders + Sequential Workflow**
   - Multiple threads place orders
   - Each order: Inventory → Payment → Tracking (sequential)

2. **Parallel Orders + Parallel Workflow**
   - Multiple threads place orders
   - Each order: Inventory → (Payment + Tracking in parallel)

3. **Sequential Orders + Sequential Workflow**
   - Orders placed one by one
   - Each order: Inventory → Payment → Tracking (sequential)

4. **Sequential Orders + Parallel Workflow**
   - Orders placed one by one
   - Each order: Inventory → (Payment + Tracking in parallel)

## Expected Results

- Initial Stock: 10 units
- Total Orders: 100
- **Expected Success**: Exactly 10 orders
- **Expected Failures**: 90 orders (out of stock)

## Troubleshooting

### Port Already in Use
```bash
lsof -ti:50050,50051,50052,50053 | xargs kill -9
```

### Database Locked
```bash
rm retail.db
```

### Services Not Starting
```bash
# Check if proto files exist
ls proto/retail_pb2.py

# If not, generate them
./generate_proto.sh
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Regenerate proto files
./generate_proto.sh
```

## File Structure

```
scenario4/
├── proto/
│   ├── __init__.py
│   ├── retail.proto
│   ├── retail_pb2.py (generated)
│   └── retail_pb2_grpc.py (generated)
├── database.py
├── inventory_service_grpc.py
├── payment_service_grpc.py
├── tracking_service_grpc.py
├── order_service_grpc.py
├── run_trial.py
├── generate_proto.sh
├── start_services.sh
├── stop_services.sh
├── test_services.sh
├── requirements.txt
├── README.md
├── QUICK_REFERENCE.md (this file)
└── .gitignore
```

## Performance Metrics

Each order tracks:
- **Total Time**: Complete order processing time
- **Inventory Time**: Stock reservation time
- **Payment Time**: Payment processing time
- **Tracking Time**: Tracking initiation time
- **CPU Time**: CPU usage
- **Payload Sizes**: Request/response bytes

## Key Features

✅ Atomic stock operations (no overselling)
✅ Automatic rollback on payment failure
✅ Real-time tracking with auto-progression
✅ Thread-safe database operations
✅ Comprehensive error handling
✅ Performance metrics collection
✅ Both sequential and parallel workflows

## Architecture

```
Client
  │
  ▼
Order Service (Orchestrator)
  ├─► Inventory Service (Check & Reserve)
  ├─► Payment Service (Process Payment)
  └─► Tracking Service (Initiate Tracking)
       │
       └─► Background: Auto-progress tracking stages
```

## Workflow Comparison

### Sequential Workflow
```
Inventory → Payment → Tracking
Total Time = T1 + T2 + T3
```

### Parallel Workflow
```
Inventory → ┌─ Payment ─┐
            └─ Tracking ─┘
Total Time = T1 + max(T2, T3)
Speedup: ~1.5-2x
```

## Testing Tips

1. **Start Fresh**: Clear database between major test runs
2. **Monitor Logs**: Keep logs open to see real-time activity
3. **Check Services**: Use test script before running experiments
4. **Be Patient**: Wait for all threads to complete
5. **Read Reports**: Generated .txt files contain detailed results

## Advanced Usage

### Custom Stock Levels
Edit `run_trial.py`:
```python
INIT_STOCK = 20  # Change this value
```

### Custom Delays
Edit `run_trial.py`:
```python
DELAY_MS = 100  # Add artificial delay
```

### Database Inspection
```bash
sqlite3 retail.db
sqlite> SELECT * FROM orders;
sqlite> SELECT * FROM inventory;
sqlite> .quit
```

### Manual Testing
```python
import grpc
from proto import retail_pb2 as pb
from proto import retail_pb2_grpc as rpc

channel = grpc.insecure_channel('localhost:50050')
stub = rpc.OrderServiceStub(channel)

request = pb.CreateOrderRequest(
    product_id="TEST001",
    quantity=1,
    amount=99.99,
    parallel_processing=True
)

response = stub.CreateOrder(request)
print(response)
```

## Success Criteria

✅ All services start successfully
✅ Service connectivity test passes
✅ Exactly INIT_STOCK orders succeed per trial
✅ No database errors
✅ Clean shutdown with stop script

## Common Issues

| Issue | Solution |
|-------|----------|
| Proto import error | Run `./generate_proto.sh` |
| Service not starting | Check port availability |
| Database locked | Remove `retail.db` file |
| Connection refused | Verify services are running |
| Import errors | Reinstall requirements |

## Best Practices

1. Always start services before running tests
2. Stop services cleanly with script
3. Clear data between major experiments
4. Monitor resource usage with `htop` or Activity Monitor
5. Keep logs for debugging

## Support

- Check README.md for detailed documentation
- Review service logs for errors
- Test connectivity with test_services.sh
- Verify proto files are generated
