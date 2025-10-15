#!/bin/bash
# Stop all gRPC services

echo "Stopping gRPC Microservices..."
echo "================================"

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file="logs/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat $pid_file)
        if ps -p $pid > /dev/null 2>&1; then
            echo "Stopping $service_name (PID: $pid)..."
            kill $pid
            sleep 1
            
            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                echo "Force stopping $service_name..."
                kill -9 $pid
            fi
            
            echo "✓ $service_name stopped"
        else
            echo "✗ $service_name not running"
        fi
        rm -f $pid_file
    else
        echo "✗ No PID file for $service_name"
    fi
}

# Stop services
stop_service "Order"
stop_service "Inventory"
stop_service "Payment"
stop_service "Tracking"

# Also kill any remaining Python processes running these services
echo ""
echo "Cleaning up any remaining service processes..."
pkill -f "inventory_service_grpc.py"
pkill -f "payment_service_grpc.py"
pkill -f "tracking_service_grpc.py"
pkill -f "order_service_grpc.py"

echo ""
echo "================================"
echo "✓ All services stopped!"
echo "================================"
