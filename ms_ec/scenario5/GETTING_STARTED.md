# Quick Start Guide - Scenario 5

## ✅ Services are Running!

All 4 gRPC services are now running:
- ✓ Order Service (Port 50050)
- ✓ Inventory Service (Port 50051)
- ✓ Payment Service (Port 50052)
- ✓ Tracking Service (Port 50053)

## 🚀 Run Experiments

```bash
python3 run_trial.py
```

Then select from the menu:
1. Parallel Orders - Sequential Workflow
2. Parallel Orders - Parallel Workflow
3. Sequential Orders - Sequential Workflow
4. Sequential Orders - Parallel Workflow
5. Run All Experiments

## 📊 What Each Test Does

### Test 1 & 2: Parallel Orders
- **Setup**: 100 threads placing orders simultaneously
- **Stock**: 10 units available
- **Expected**: 10 orders succeed, 90 fail (out of stock)
- **Tests**: Race condition handling, atomic operations

### Test 3 & 4: Sequential Orders
- **Setup**: 100 orders placed one at a time
- **Stock**: 10 units available
- **Expected**: First 10 succeed, rest fail
- **Tests**: Sequential correctness, baseline performance

### Sequential vs Parallel Workflow
- **Sequential**: Inventory → Payment → Tracking (one after another)
- **Parallel**: Inventory → (Payment || Tracking) (concurrent)
- **Benefit**: Parallel is ~1.5-2x faster

## 📝 Results

Results are saved as text files:
- `ms_sc5_parallel_sequential.txt`
- `ms_sc5_parallel_parallel.txt`
- `ms_sc5_sequential_sequential.txt`
- `ms_sc5_sequential_parallel.txt`

## 🔍 Monitor Services

### View logs in real-time:
```bash
# All services
tail -f logs/*.log

# Specific service
tail -f logs/Order.log
```

### Check service status:
```bash
./test_services.sh
```

## 🛑 Stop Services

When done:
```bash
./stop_services.sh
```

## 🔄 Restart Services

If something goes wrong:
```bash
./stop_services.sh
./start_services.sh
```

## 🆘 Troubleshooting

### Services not responding?
```bash
./stop_services.sh
pkill -f "_service_grpc.py"
./start_services.sh
```

### Port already in use?
```bash
lsof -ti:50050,50051,50052,50053 | xargs kill -9
./start_services.sh
```

### Database issues?
```bash
./stop_services.sh
rm retail.db
./start_services.sh
```

## 📚 Documentation

- **README.md** - Complete documentation
- **ARCHITECTURE.md** - System diagrams
- **COMPARISON.md** - Compare with other scenarios
- **IMPLEMENTATION_SUMMARY.md** - Feature overview

---

**You're all set! Run `python3 run_trial.py` to start experimenting! 🎉**
