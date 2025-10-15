"""
Inventory Service - gRPC Implementation
Handles stock management, reservation, and availability checks
"""

import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

import grpc
from proto import retail_pb2 as pb
from proto import retail_pb2_grpc as rpc
from database import get_database

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("inventory_service")

# Thread pool for blocking database operations
executor = ThreadPoolExecutor(max_workers=20)


class InventoryServicer(rpc.InventoryServiceServicer):
    """gRPC Inventory Service Implementation"""
    
    def __init__(self):
        self.db = get_database()
        LOG.info("Inventory Service initialized")
    
    async def CheckStock(self, request: pb.CheckStockRequest, context) -> pb.CheckStockResponse:
        """Check if sufficient stock is available for a product"""
        product_id = request.product_id
        quantity = request.quantity
        
        LOG.info(f"CheckStock: product={product_id}, quantity={quantity}")
        
        try:
            # Run database operation in thread pool
            available, current_stock = await asyncio.get_event_loop().run_in_executor(
                executor, self.db.check_stock, product_id, quantity
            )
            
            if available:
                message = f"Stock available: {current_stock} units"
                LOG.info(f"Stock check passed: {product_id} - {current_stock} units available")
            else:
                message = f"Insufficient stock: {current_stock} units available, {quantity} requested"
                LOG.warning(f"Stock check failed: {product_id} - only {current_stock} units available")
            
            return pb.CheckStockResponse(
                available=available,
                current_stock=current_stock,
                message=message
            )
            
        except Exception as e:
            LOG.error(f"Error checking stock for {product_id}: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error checking stock: {str(e)}")
            return pb.CheckStockResponse(
                available=False,
                current_stock=0,
                message=f"Error: {str(e)}"
            )
    
    async def ReserveStock(self, request: pb.ReserveStockRequest, context) -> pb.ReserveStockResponse:
        """Reserve stock for an order"""
        order_id = request.order_id
        product_id = request.product_id
        quantity = request.quantity
        delay_ms = request.delay_ms
        
        # Calculate request size
        req_size = request.ByteSize()
        
        LOG.info(f"ReserveStock: order={order_id}, product={product_id}, qty={quantity}, delay={delay_ms}ms")
        
        try:
            # Reserve stock atomically
            success = await asyncio.get_event_loop().run_in_executor(
                executor, self.db.reserve_stock, product_id, quantity
            )
            
            # Inject artificial delay if specified
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000.0)
            
            if success:
                # Create reservation record
                reservation_id = str(uuid.uuid4())
                await asyncio.get_event_loop().run_in_executor(
                    executor, self.db.create_reservation, 
                    reservation_id, order_id, product_id, quantity
                )
                
                response = pb.ReserveStockResponse(
                    success=True,
                    reservation_id=reservation_id,
                    message=f"Reserved {quantity} units of {product_id}",
                    request_bytes=req_size,
                    response_bytes=0  # Will be set after creating response
                )
                LOG.info(f"Stock reserved: {reservation_id} for order {order_id}")
            else:
                response = pb.ReserveStockResponse(
                    success=False,
                    reservation_id="",
                    message=f"Failed to reserve stock for {product_id}",
                    request_bytes=req_size,
                    response_bytes=0
                )
                LOG.warning(f"Stock reservation failed for order {order_id}")
            
            # Set response size
            response.response_bytes = response.ByteSize()
            
            # Send metadata
            await context.send_initial_metadata((
                ("request-bytes", str(req_size)),
                ("response-bytes", str(response.response_bytes)),
            ))
            
            return response
            
        except Exception as e:
            LOG.error(f"Error reserving stock for order {order_id}: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error reserving stock: {str(e)}")
            return pb.ReserveStockResponse(
                success=False,
                reservation_id="",
                message=f"Error: {str(e)}",
                request_bytes=req_size,
                response_bytes=0
            )
    
    async def ReleaseStock(self, request: pb.ReleaseStockRequest, context) -> pb.ReleaseStockResponse:
        """Release reserved stock (rollback)"""
        order_id = request.order_id
        reservation_id = request.reservation_id
        
        LOG.info(f"ReleaseStock: order={order_id}, reservation={reservation_id}")
        
        try:
            # Get reservation details
            reservation = await asyncio.get_event_loop().run_in_executor(
                executor, self.db.get_reservation, order_id
            )
            
            if not reservation:
                message = f"Reservation not found for order {order_id}"
                LOG.warning(message)
                return pb.ReleaseStockResponse(success=False, message=message)
            
            # Release the reserved stock
            success = await asyncio.get_event_loop().run_in_executor(
                executor, self.db.release_stock, 
                reservation['product_id'], reservation['quantity']
            )
            
            if success:
                message = f"Released {reservation['quantity']} units of {reservation['product_id']}"
                LOG.info(message)
            else:
                message = f"Failed to release stock for order {order_id}"
                LOG.error(message)
            
            return pb.ReleaseStockResponse(success=success, message=message)
            
        except Exception as e:
            LOG.error(f"Error releasing stock for order {order_id}: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error releasing stock: {str(e)}")
            return pb.ReleaseStockResponse(
                success=False,
                message=f"Error: {str(e)}"
            )
    
    async def InitializeStock(self, request: pb.InitializeStockRequest, context) -> pb.InitializeStockResponse:
        """Initialize stock for a product"""
        product_id = request.product_id
        quantity = request.quantity
        
        LOG.info(f"InitializeStock: product={product_id}, quantity={quantity}")
        
        try:
            success = await asyncio.get_event_loop().run_in_executor(
                executor, self.db.initialize_stock, product_id, quantity
            )
            
            if success:
                message = f"Initialized {quantity} units of {product_id}"
                LOG.info(message)
            else:
                message = f"Failed to initialize stock for {product_id}"
                LOG.error(message)
            
            return pb.InitializeStockResponse(success=success, message=message)
            
        except Exception as e:
            LOG.error(f"Error initializing stock for {product_id}: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error initializing stock: {str(e)}")
            return pb.InitializeStockResponse(
                success=False,
                message=f"Error: {str(e)}"
            )
    
    async def ClearInventory(self, request: pb.Empty, context) -> pb.Empty:
        """Clear all inventory (for testing)"""
        LOG.info("ClearInventory: clearing all inventory data")
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                executor, self.db.clear_inventory
            )
            LOG.info("Inventory cleared successfully")
            return pb.Empty()
            
        except Exception as e:
            LOG.error(f"Error clearing inventory: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error clearing inventory: {str(e)}")
            return pb.Empty()


async def serve(host: str = "0.0.0.0", port: int = 50051):
    """Start the Inventory gRPC server"""
    server = grpc.aio.server()
    rpc.add_InventoryServiceServicer_to_server(InventoryServicer(), server)
    server.add_insecure_port(f"{host}:{port}")
    
    LOG.info(f"Starting Inventory gRPC server on {host}:{port}")
    await server.start()
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        LOG.info("Shutting down Inventory service")
        await server.stop(grace=5)


if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        LOG.info("Inventory service stopped")
