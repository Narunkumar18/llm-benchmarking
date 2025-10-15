#!/bin/bash
# Start all gRPC services

echo "Starting gRPC Microservices..."
echo "================================"

# Check if proto files are generated
if [ ! -f "proto/retail_pb2.py" ]; then
    echo "Proto files not found. Generating..."
    ./generate_proto.sh
fi

# Function to start a service in the background
start_service() {
    local service_name=$1
    local service_file=$2
    local port=$3
    
    echo "Starting $service_name on port $port..."
    python3 $service_file > logs/${service_name}.log 2>&1 &
    local pid=$!
    echo $pid > logs/${service_name}.pid
    echo "✓ $service_name started (PID: $pid)"
}

# Create logs directory if it doesn't exist
mkdir -p logs

# Clear old log files
rm -f logs/*.log

# Start services
echo ""
start_service "Inventory" "inventory_service_grpc.py" "50051"
sleep 2

start_service "Payment" "payment_service_grpc.py" "50052"
sleep 2

start_service "Tracking" "tracking_service_grpc.py" "50053"
sleep 2

start_service "Order" "order_service_grpc.py" "50050"
sleep 2

echo ""
echo "================================"
echo "✓ All services started!"
echo ""
echo "Service Status:"
echo "  - Order Service:     http://localhost:50050"
echo "  - Inventory Service: http://localhost:50051"
echo "  - Payment Service:   http://localhost:50052"
echo "  - Tracking Service:  http://localhost:50053"
echo ""
echo "Logs are in the 'logs' directory"
echo "Run './stop_services.sh' to stop all services"
echo "================================"
