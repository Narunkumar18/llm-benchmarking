import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import time
from datetime import datetime
import psutil
import os
from tqdm import tqdm

INVENTORY_SERVICE_URL = "http://localhost:8082"
ORDER_SERVICE_URL = "http://localhost:8081"
PAYMENT_SERVICE_URL = "http://localhost:8083"
TRACKING_SERVICE_URL = "http://localhost:8084"

process = psutil.Process(os.getpid())

def measure_performance(func):
    """Decorator to measure API call performance"""
    def wrapper(*args, **kwargs):
        cpu_start = process.cpu_times()
        t1 = time.time()
        
        response = func(*args, **kwargs)
        
        t2 = time.time()
        cpu_end = process.cpu_times()
        cpu_used = (cpu_end.user - cpu_start.user) + (cpu_end.system - cpu_start.system)
        
        if isinstance(response, requests.Response):
            req_size = len(response.request.body or b"") + sum(len(str(v)) for v in response.request.headers.values())
            res_size = len(response.content) + sum(len(str(v)) for v in response.headers.values())
            payload_size = req_size + res_size
            
            return {
                "response": response.json(),
                "metrics": {
                    "response_time": round((t2-t1), 3),
                    "cpu_time": round(cpu_used, 5),
                    "payload_size": payload_size
                }
            }
        return response
    return wrapper

@measure_performance
def place_order(item: str, qty: int, delay: int = 0):
    """Place a single order and return performance metrics"""
    response = requests.post(
        f"{ORDER_SERVICE_URL}/order",
        json={"item": item, "qty": qty, "delay": delay}
    )
    return response

async def place_order_async(item: str, qty: int, delay: int = 0):
    """Place a single order asynchronously"""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, place_order, item, qty, delay)

def clear_all_services():
    """Clear all services data"""
    requests.post(f"{INVENTORY_SERVICE_URL}/clear_stocks")
    requests.post(f"{ORDER_SERVICE_URL}/clear_orders")

def init_inventory(items, initial_stock=10):
    """Initialize inventory with items"""
    for item in items:
        requests.post(f"{INVENTORY_SERVICE_URL}/init_stock", 
                     json={"item": item, "stock": initial_stock})

async def run_parallel_scenario(orders, delay=0, report_file="ms_sc1_parallel.txt"):
    """Run parallel order placement scenario"""
    start_time = time.time()
    results = []
    
    # Place orders concurrently
    tasks = [
        place_order_async(order["item"], order["qty"], delay)
        for order in orders
    ]
    
    order_results = await asyncio.gather(*tasks)
    
    for result in order_results:
        results.append({
            "order_result": result["response"],
            "metrics": result["metrics"]
        })
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Prepare report data
    report_data = {
        "scenario": "parallel",
        "total_time": total_time,
        "total_orders": len(orders),
        "average_response_time": sum(r["metrics"]["response_time"] for r in results) / len(results),
        "average_cpu_time": sum(r["metrics"]["cpu_time"] for r in results) / len(results),
        "average_payload_size": sum(r["metrics"]["payload_size"] for r in results) / len(results),
        "orders": results
    }
    
    # Save report
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2)
    
    return report_data

def run_sequential_scenario(orders, delay=0, report_file="ms_sc1_sequential.txt"):
    """Run sequential order placement scenario"""
    start_time = time.time()
    results = []
    
    # Place orders sequentially
    for order in tqdm(orders, desc="Processing Orders"):
        result = place_order(order["item"], order["qty"], delay)
        results.append({
            "order_result": result["response"],
            "metrics": result["metrics"]
        })
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Prepare report data
    report_data = {
        "scenario": "sequential",
        "total_time": total_time,
        "total_orders": len(orders),
        "average_response_time": sum(r["metrics"]["response_time"] for r in results) / len(results),
        "average_cpu_time": sum(r["metrics"]["cpu_time"] for r in results) / len(results),
        "average_payload_size": sum(r["metrics"]["payload_size"] for r in results) / len(results),
        "orders": results
    }
    
    # Save report
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2)
    
    return report_data

async def main():
    # Test data
    items = ["item1", "item2", "item3"]
    orders = [
        {"item": "item1", "qty": 2},
        {"item": "item2", "qty": 3},
        {"item": "item3", "qty": 1},
        {"item": "item1", "qty": 1},
        {"item": "item2", "qty": 2}
    ]
    
    # Parameters
    delay = 1  # 1 second delay
    trials = 5
    
    print("\nStarting Order Processing Benchmark...")
    print(f"Number of trials: {trials}")
    print(f"Number of orders per trial: {len(orders)}")
    print(f"Artificial delay per operation: {delay}s")
    
    sequential_results = []
    parallel_results = []
    
    for trial in range(trials):
        print(f"\nTrial {trial + 1}/{trials}")
        
        # Clear and initialize services
        clear_all_services()
        init_inventory(items)
        
        # Run sequential scenario
        print("\nRunning Sequential Scenario...")
        seq_result = run_sequential_scenario(
            orders, 
            delay,
            f"ms_sc1_sequential_trial_{trial + 1}.txt"
        )
        sequential_results.append(seq_result)
        
        # Clear and reinitialize for parallel test
        clear_all_services()
        init_inventory(items)
        
        # Run parallel scenario
        print("\nRunning Parallel Scenario...")
        par_result = await run_parallel_scenario(
            orders,
            delay,
            f"ms_sc1_parallel_trial_{trial + 1}.txt"
        )
        parallel_results.append(par_result)
    
    # Calculate and print averages across trials
    print("\nFinal Results (averaged across all trials):")
    
    avg_sequential_time = sum(r["total_time"] for r in sequential_results) / trials
    avg_parallel_time = sum(r["total_time"] for r in parallel_results) / trials
    
    print(f"\nSequential Scenario:")
    print(f"Average Total Time: {avg_sequential_time:.2f} seconds")
    print(f"Average Response Time: {sum(r['average_response_time'] for r in sequential_results)/trials:.3f} seconds")
    print(f"Average CPU Time: {sum(r['average_cpu_time'] for r in sequential_results)/trials:.3f} seconds")
    
    print(f"\nParallel Scenario:")
    print(f"Average Total Time: {avg_parallel_time:.2f} seconds")
    print(f"Average Response Time: {sum(r['average_response_time'] for r in parallel_results)/trials:.3f} seconds")
    print(f"Average CPU Time: {sum(r['average_cpu_time'] for r in parallel_results)/trials:.3f} seconds")
    
    improvement = ((avg_sequential_time - avg_parallel_time) / avg_sequential_time) * 100
    print(f"\nAverage Performance Improvement: {improvement:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())
