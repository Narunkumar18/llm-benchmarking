#!/bin/bash
# Test gRPC client to verify services are running

echo "Testing gRPC Services..."
echo "================================"

python3 << 'EOF'
import grpc
import sys
sys.path.append('.')

from proto import retail_pb2 as pb
from proto import retail_pb2_grpc as rpc

def test_service(service_name, address, stub_class):
    """Test if a service is reachable"""
    try:
        channel = grpc.insecure_channel(address)
        grpc.channel_ready_future(channel).result(timeout=5)
        print(f"✓ {service_name} is reachable at {address}")
        channel.close()
        return True
    except grpc.FutureTimeoutError:
        print(f"✗ {service_name} is NOT reachable at {address}")
        return False
    except Exception as e:
        print(f"✗ {service_name} error: {e}")
        return False

print("\nTesting service connectivity...\n")

services = [
    ("Order Service", "localhost:50050", rpc.OrderServiceStub),
    ("Inventory Service", "localhost:50051", rpc.InventoryServiceStub),
    ("Payment Service", "localhost:50052", rpc.PaymentServiceStub),
    ("Tracking Service", "localhost:50053", rpc.TrackingServiceStub),
]

all_ok = True
for name, addr, stub in services:
    if not test_service(name, addr, stub):
        all_ok = False

print("\n================================")
if all_ok:
    print("✓ All services are running!")
else:
    print("✗ Some services are not running")
    print("  Run './start_services.sh' to start services")
print("================================")
EOF
