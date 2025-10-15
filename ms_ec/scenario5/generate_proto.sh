#!/bin/bash
# Generate Python code from protobuf definitions

echo "Generating Python gRPC code from protobuf..."

cd proto

python3 -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    retail.proto

echo "✓ Generated retail_pb2.py and retail_pb2_grpc.py"

# Fix import statements for proper module import
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' 's/^import retail_pb2/from . import retail_pb2/' retail_pb2_grpc.py
else
    # Linux
    sed -i 's/^import retail_pb2/from . import retail_pb2/' retail_pb2_grpc.py
fi

echo "✓ Fixed import statements"
echo "✓ Proto generation complete!"

cd ..
