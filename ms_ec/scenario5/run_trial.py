"""
Run Trial Script for Scenario 5 - gRPC Microservices
Tests sequential and parallel order processing with performance metrics
"""

import threading
import time
import uuid
import psutil
import os
import sys
import grpc
from tqdm import tqdm
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from proto import retail_pb2 as pb
from proto import retail_pb2_grpc as rpc

# Process monitoring
process = psutil.Process(os.getpid())

# gRPC service addresses
ORDER_ADDR = "localhost:50050"
INVENTORY_ADDR = "localhost:50051"
PAYMENT_ADDR = "localhost:50052"
TRACKING_ADDR = "localhost:50053"

# Global stubs
order_stub = None
inventory_stub = None
payment_stub = None
tracking_stub = None


def initialize_stubs():
    """Initialize gRPC stubs for all services"""
    global order_stub, inventory_stub, payment_stub, tracking_stub
    
    order_channel = grpc.insecure_channel(ORDER_ADDR)
    order_stub = rpc.OrderServiceStub(order_channel)
    
    inventory_channel = grpc.insecure_channel(INVENTORY_ADDR)
    inventory_stub = rpc.InventoryServiceStub(inventory_channel)
    
    payment_channel = grpc.insecure_channel(PAYMENT_ADDR)
    payment_stub = rpc.PaymentServiceStub(payment_channel)
    
    tracking_channel = grpc.insecure_channel(TRACKING_ADDR)
    tracking_stub = rpc.TrackingServiceStub(tracking_channel)
    
    print("✓ gRPC stubs initialized")


def clear_all_data():
    """Clear all data from all services"""
    try:
        order_stub.ClearOrders(pb.Empty())
        inventory_stub.ClearInventory(pb.Empty())
        payment_stub.ClearPayments(pb.Empty())
        tracking_stub.ClearTracking(pb.Empty())
        print("✓ All data cleared")
        return True
    except Exception as e:
        print(f"✗ Error clearing data: {e}")
        return False


def initialize_product_stock(product_id: str, quantity: int) -> bool:
    """Initialize stock for a product"""
    try:
        request = pb.InitializeStockRequest(
            product_id=product_id,
            quantity=quantity
        )
        response = inventory_stub.InitializeStock(request)
        
        if response.success:
            print(f"✓ Stock initialized: {product_id} = {quantity} units")
            return True
        else:
            print(f"✗ Failed to initialize stock: {response.message}")
            return False
            
    except Exception as e:
        print(f"✗ Error initializing stock: {e}")
        return False


def place_order(product_id: str, quantity: int, amount: float, 
               parallel: bool, delay_ms: int, results: dict, idx: int):
    """Place a single order and store results"""
    try:
        # Measure CPU time
        cpu_start = process.cpu_times()
        
        # Measure wall time
        t_start = time.time()
        
        # Create order request
        request = pb.CreateOrderRequest(
            product_id=product_id,
            quantity=quantity,
            amount=amount,
            parallel_processing=parallel,
            delay_ms=delay_ms
        )
        
        # Call order service
        response = order_stub.CreateOrder(request, timeout=60.0)
        
        t_end = time.time()
        cpu_end = process.cpu_times()
        
        # Calculate metrics
        wall_time = t_end - t_start
        cpu_time = (cpu_end.user - cpu_start.user) + (cpu_end.system - cpu_start.system)
        
        # Store results
        results[idx] = {
            "success": response.success,
            "order_id": response.order_id,
            "status": response.status,
            "payment_id": response.payment_id,
            "tracking_id": response.tracking_id,
            "reservation_id": response.reservation_id,
            "wall_time": wall_time,
            "cpu_time": cpu_time,
            "metrics": {
                "total_time": response.metrics.total_time,
                "inventory_time": response.metrics.inventory_time,
                "payment_time": response.metrics.payment_time,
                "tracking_time": response.metrics.tracking_time,
                "total_request_bytes": response.metrics.total_request_bytes,
                "total_response_bytes": response.metrics.total_response_bytes
            }
        }
        
        # Log result
        status_icon = "✓" if response.success else "✗"
        print(f"{status_icon} Order {idx}: {response.status} | "
              f"Time: {wall_time:.3f}s | CPU: {cpu_time:.4f}s")
        
    except grpc.RpcError as e:
        print(f"✗ Order {idx} RPC Error: {e.code()} - {e.details()}")
        results[idx] = {
            "success": False,
            "error": str(e),
            "wall_time": 0,
            "cpu_time": 0
        }
    except Exception as e:
        print(f"✗ Order {idx} Error: {e}")
        results[idx] = {
            "success": False,
            "error": str(e),
            "wall_time": 0,
            "cpu_time": 0
        }


def run_parallel_orders(trials: int = 10, concurrent_orders: int = 100,
                       init_stock: int = 10, delay_ms: int = 0,
                       parallel_processing: bool = False):
    """
    Run parallel order placement experiment
    
    Args:
        trials: Number of trial runs
        concurrent_orders: Number of orders to place concurrently
        init_stock: Initial stock quantity
        delay_ms: Artificial delay in milliseconds
        parallel_processing: Use parallel workflow (payment + tracking in parallel)
    """
    print("\n" + "="*80)
    print(f"PARALLEL ORDER PLACEMENT EXPERIMENT")
    print(f"Workflow: {'PARALLEL' if parallel_processing else 'SEQUENTIAL'}")
    print("="*80)
    print(f"Trials: {trials}")
    print(f"Concurrent Orders per Trial: {concurrent_orders}")
    print(f"Initial Stock: {init_stock}")
    print(f"Delay: {delay_ms}ms")
    print("="*80 + "\n")
    
    success_count = 0
    failure_count = 0
    
    report_file = f"ms_sc5_parallel_{'parallel' if parallel_processing else 'sequential'}.txt"
    
    with open(report_file, 'w') as f:
        f.write(f"Parallel Order Experiment - {'Parallel' if parallel_processing else 'Sequential'} Workflow\n")
        f.write(f"Trials: {trials}, Concurrent Orders: {concurrent_orders}, "
                f"Stock: {init_stock}, Delay: {delay_ms}ms\n")
        f.write(f"Started: {datetime.now().isoformat()}\n")
        f.write("="*80 + "\n\n")
    
    for trial in range(trials):
        print(f"\n📊 Trial {trial + 1}/{trials}")
        print("-" * 40)
        
        # Clear and reset
        clear_all_data()
        
        # Generate unique product ID for this trial
        product_id = f"PROD_{uuid.uuid4().hex[:8]}"
        
        # Initialize stock
        if not initialize_product_stock(product_id, init_stock):
            failure_count += 1
            continue
        
        # Wait for user confirmation
        input("Press Enter to start placing orders...")
        
        # Place orders concurrently
        results = {}
        threads = []
        
        trial_start = time.time()
        
        for i in range(concurrent_orders):
            thread = threading.Thread(
                target=place_order,
                args=(product_id, 1, 99.99, parallel_processing, delay_ms, results, i)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        trial_end = time.time()
        trial_duration = trial_end - trial_start
        
        # Analyze results
        successful_orders = sum(1 for r in results.values() if r.get("success", False))
        failed_orders = len(results) - successful_orders
        
        total_wall_time = sum(r.get("wall_time", 0) for r in results.values())
        avg_wall_time = total_wall_time / len(results) if results else 0
        
        total_cpu_time = sum(r.get("cpu_time", 0) for r in results.values())
        avg_cpu_time = total_cpu_time / len(results) if results else 0
        
        print(f"\n📈 Trial {trial + 1} Results:")
        print(f"  Duration: {trial_duration:.3f}s")
        print(f"  Successful Orders: {successful_orders}/{concurrent_orders}")
        print(f"  Failed Orders: {failed_orders}")
        print(f"  Avg Wall Time: {avg_wall_time:.3f}s")
        print(f"  Avg CPU Time: {avg_cpu_time:.4f}s")
        
        # Check if trial succeeded (exactly init_stock orders should succeed)
        if successful_orders == init_stock:
            success_count += 1
            print("  ✓ Trial PASSED (correct number of orders succeeded)")
        else:
            failure_count += 1
            print(f"  ✗ Trial FAILED (expected {init_stock} successes, got {successful_orders})")
        
        # Write to report
        with open(report_file, 'a') as f:
            f.write(f"Trial {trial + 1}:\n")
            f.write(f"  Duration: {trial_duration:.3f}s\n")
            f.write(f"  Successful: {successful_orders}, Failed: {failed_orders}\n")
            f.write(f"  Avg Wall Time: {avg_wall_time:.3f}s\n")
            f.write(f"  Avg CPU Time: {avg_cpu_time:.4f}s\n")
            f.write(f"  Result: {'PASS' if successful_orders == init_stock else 'FAIL'}\n\n")
    
    # Final summary
    print("\n" + "="*80)
    print("EXPERIMENT SUMMARY")
    print("="*80)
    print(f"Total Trials: {trials}")
    print(f"Passed: {success_count}")
    print(f"Failed: {failure_count}")
    print(f"Success Rate: {success_count / trials * 100:.1f}%")
    print("="*80 + "\n")
    
    with open(report_file, 'a') as f:
        f.write("\n" + "="*80 + "\n")
        f.write("SUMMARY\n")
        f.write("="*80 + "\n")
        f.write(f"Total Trials: {trials}\n")
        f.write(f"Passed: {success_count}\n")
        f.write(f"Failed: {failure_count}\n")
        f.write(f"Success Rate: {success_count / trials * 100:.1f}%\n")
        f.write(f"Completed: {datetime.now().isoformat()}\n")
    
    print(f"✓ Report saved to: {report_file}")
    
    return success_count, failure_count


def run_sequential_orders(trials: int = 10, total_orders: int = 100,
                          init_stock: int = 10, delay_ms: int = 0,
                          parallel_processing: bool = False):
    """
    Run sequential order placement experiment
    
    Args:
        trials: Number of trial runs
        total_orders: Total number of orders to place sequentially
        init_stock: Initial stock quantity
        delay_ms: Artificial delay in milliseconds
        parallel_processing: Use parallel workflow (payment + tracking in parallel)
    """
    print("\n" + "="*80)
    print(f"SEQUENTIAL ORDER PLACEMENT EXPERIMENT")
    print(f"Workflow: {'PARALLEL' if parallel_processing else 'SEQUENTIAL'}")
    print("="*80)
    print(f"Trials: {trials}")
    print(f"Sequential Orders per Trial: {total_orders}")
    print(f"Initial Stock: {init_stock}")
    print(f"Delay: {delay_ms}ms")
    print("="*80 + "\n")
    
    success_count = 0
    failure_count = 0
    
    report_file = f"ms_sc5_sequential_{'parallel' if parallel_processing else 'sequential'}.txt"
    
    with open(report_file, 'w') as f:
        f.write(f"Sequential Order Experiment - {'Parallel' if parallel_processing else 'Sequential'} Workflow\n")
        f.write(f"Trials: {trials}, Sequential Orders: {total_orders}, "
                f"Stock: {init_stock}, Delay: {delay_ms}ms\n")
        f.write(f"Started: {datetime.now().isoformat()}\n")
        f.write("="*80 + "\n\n")
    
    for trial in range(trials):
        print(f"\n📊 Trial {trial + 1}/{trials}")
        print("-" * 40)
        
        # Clear and reset
        clear_all_data()
        
        # Generate unique product ID for this trial
        product_id = f"PROD_{uuid.uuid4().hex[:8]}"
        
        # Initialize stock
        if not initialize_product_stock(product_id, init_stock):
            failure_count += 1
            continue
        
        # Wait for user confirmation
        input("Press Enter to start placing orders...")
        
        # Place orders sequentially
        results = {}
        
        trial_start = time.time()
        
        for i in tqdm(range(total_orders), desc="Placing orders"):
            place_order(product_id, 1, 99.99, parallel_processing, delay_ms, results, i)
        
        trial_end = time.time()
        trial_duration = trial_end - trial_start
        
        # Analyze results
        successful_orders = sum(1 for r in results.values() if r.get("success", False))
        failed_orders = len(results) - successful_orders
        
        total_wall_time = sum(r.get("wall_time", 0) for r in results.values())
        avg_wall_time = total_wall_time / len(results) if results else 0
        
        total_cpu_time = sum(r.get("cpu_time", 0) for r in results.values())
        avg_cpu_time = total_cpu_time / len(results) if results else 0
        
        print(f"\n📈 Trial {trial + 1} Results:")
        print(f"  Duration: {trial_duration:.3f}s")
        print(f"  Successful Orders: {successful_orders}/{total_orders}")
        print(f"  Failed Orders: {failed_orders}")
        print(f"  Avg Wall Time: {avg_wall_time:.3f}s")
        print(f"  Avg CPU Time: {avg_cpu_time:.4f}s")
        
        # Check if trial succeeded
        if successful_orders == init_stock:
            success_count += 1
            print("  ✓ Trial PASSED")
        else:
            failure_count += 1
            print(f"  ✗ Trial FAILED (expected {init_stock} successes, got {successful_orders})")
        
        # Write to report
        with open(report_file, 'a') as f:
            f.write(f"Trial {trial + 1}:\n")
            f.write(f"  Duration: {trial_duration:.3f}s\n")
            f.write(f"  Successful: {successful_orders}, Failed: {failed_orders}\n")
            f.write(f"  Avg Wall Time: {avg_wall_time:.3f}s\n")
            f.write(f"  Avg CPU Time: {avg_cpu_time:.4f}s\n")
            f.write(f"  Result: {'PASS' if successful_orders == init_stock else 'FAIL'}\n\n")
    
    # Final summary
    print("\n" + "="*80)
    print("EXPERIMENT SUMMARY")
    print("="*80)
    print(f"Total Trials: {trials}")
    print(f"Passed: {success_count}")
    print(f"Failed: {failure_count}")
    print(f"Success Rate: {success_count / trials * 100:.1f}%")
    print("="*80 + "\n")
    
    with open(report_file, 'a') as f:
        f.write("\n" + "="*80 + "\n")
        f.write("SUMMARY\n")
        f.write("="*80 + "\n")
        f.write(f"Total Trials: {trials}\n")
        f.write(f"Passed: {success_count}\n")
        f.write(f"Failed: {failure_count}\n")
        f.write(f"Success Rate: {success_count / trials * 100:.1f}%\n")
        f.write(f"Completed: {datetime.now().isoformat()}\n")
    
    print(f"✓ Report saved to: {report_file}")
    
    return success_count, failure_count


def main():
    """Main function to run experiments"""
    print("\n" + "="*80)
    print("SCENARIO 5: gRPC MICROSERVICES ORDER PROCESSING")
    print("="*80 + "\n")
    
    # Initialize gRPC stubs
    try:
        initialize_stubs()
    except Exception as e:
        print(f"✗ Failed to initialize gRPC stubs: {e}")
        print("  Make sure all services are running!")
        return
    
    # Configuration
    TRIALS = 10
    INIT_STOCK = 10
    CONCURRENT_ORDERS = 100
    SEQUENTIAL_ORDERS = 100
    DELAY_MS = 0
    
    # Menu
    print("\nSelect experiment to run:")
    print("1. Parallel Orders - Sequential Workflow")
    print("2. Parallel Orders - Parallel Workflow")
    print("3. Sequential Orders - Sequential Workflow")
    print("4. Sequential Orders - Parallel Workflow")
    print("5. Run All Experiments")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == "1":
        run_parallel_orders(TRIALS, CONCURRENT_ORDERS, INIT_STOCK, DELAY_MS, False)
    elif choice == "2":
        run_parallel_orders(TRIALS, CONCURRENT_ORDERS, INIT_STOCK, DELAY_MS, True)
    elif choice == "3":
        run_sequential_orders(TRIALS, SEQUENTIAL_ORDERS, INIT_STOCK, DELAY_MS, False)
    elif choice == "4":
        run_sequential_orders(TRIALS, SEQUENTIAL_ORDERS, INIT_STOCK, DELAY_MS, True)
    elif choice == "5":
        print("\n🚀 Running all experiments...\n")
        run_parallel_orders(TRIALS, CONCURRENT_ORDERS, INIT_STOCK, DELAY_MS, False)
        run_parallel_orders(TRIALS, CONCURRENT_ORDERS, INIT_STOCK, DELAY_MS, True)
        run_sequential_orders(TRIALS, SEQUENTIAL_ORDERS, INIT_STOCK, DELAY_MS, False)
        run_sequential_orders(TRIALS, SEQUENTIAL_ORDERS, INIT_STOCK, DELAY_MS, True)
    else:
        print("Invalid choice!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Experiment interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
