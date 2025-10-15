#!/bin/bash
# Complete setup script for Scenario 4
# Run this script to set up everything from scratch

echo "================================================"
echo "Scenario 4: gRPC Microservices Setup"
echo "================================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"
echo ""

# Install dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt
if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed"
else
    echo "✗ Failed to install dependencies"
    exit 1
fi
echo ""

# Generate proto files
echo "Generating Protocol Buffer files..."
./generate_proto.sh
if [ $? -eq 0 ]; then
    echo "✓ Proto files generated"
else
    echo "✗ Failed to generate proto files"
    exit 1
fi
echo ""

# Create logs directory
echo "Creating logs directory..."
mkdir -p logs
echo "✓ Logs directory created"
echo ""

# Check if ports are available
echo "Checking port availability..."
ports=(50050 50051 50052 50053)
for port in "${ports[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo "✗ Port $port is already in use"
        echo "  Run: lsof -ti:$port | xargs kill"
        exit 1
    else
        echo "✓ Port $port is available"
    fi
done
echo ""

echo "================================================"
echo "✓ Setup Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Start services:  ./start_services.sh"
echo "2. Test services:   ./test_services.sh"
echo "3. Run experiments: python run_trial.py"
echo "4. Stop services:   ./stop_services.sh"
echo ""
echo "Documentation:"
echo "- Quick start: QUICK_REFERENCE.md"
echo "- Full guide:  README.md"
echo "- Summary:     IMPLEMENTATION_SUMMARY.md"
echo ""
echo "================================================"
