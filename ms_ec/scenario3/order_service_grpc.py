"""
Order Service - gRPC Implementation
Orchestrates inventory, payment, and tracking services for order processing
Supports both sequential and parallel workflows
"""

import asyncio
import logging
import uuid
import time
from concurrent.futures import ThreadPoolExecutor

import grpc
from proto import retail_pb2 as pb
from proto import retail_pb2_grpc as rpc
from database import get_database

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("order_service")

# Thread pool for blocking database operations
executor = ThreadPoolExecutor(max_workers=20)

# Service addresses
INVENTORY_ADDR = "localhost:50051"
PAYMENT_ADDR = "localhost:50052"
TRACKING_ADDR = "localhost:50053"


class OrderServicer(rpc.OrderServiceServicer):
    """gRPC Order Service Implementation"""
    
    def __init__(self):
        self.db = get_database()
        
        # Create gRPC channels and stubs
        self.inventory_channel = None
        self.payment_channel = None
        self.tracking_channel = None
        
        self.inventory_stub = None
        self.payment_stub = None
        self.tracking_stub = None
        
        LOG.info("Order Service initialized")
    
    async def _initialize_stubs(self):
        """Initialize gRPC stubs for other services"""
        if self.inventory_stub is None:
            self.inventory_channel = grpc.aio.insecure_channel(INVENTORY_ADDR)
            self.inventory_stub = rpc.InventoryServiceStub(self.inventory_channel)
            LOG.info(f"Connected to Inventory service at {INVENTORY_ADDR}")
        
        if self.payment_stub is None:
            self.payment_channel = grpc.aio.insecure_channel(PAYMENT_ADDR)
            self.payment_stub = rpc.PaymentServiceStub(self.payment_channel)
            LOG.info(f"Connected to Payment service at {PAYMENT_ADDR}")
        
        if self.tracking_stub is None:
            self.tracking_channel = grpc.aio.insecure_channel(TRACKING_ADDR)
            self.tracking_stub = rpc.TrackingServiceStub(self.tracking_channel)
            LOG.info(f"Connected to Tracking service at {TRACKING_ADDR}")
    
    async def CreateOrder(self, request: pb.CreateOrderRequest, context) -> pb.CreateOrderResponse:
        """
        Create and process an order with complete workflow
        Supports both sequential and parallel processing modes
        """
        product_id = request.product_id
        quantity = request.quantity
        amount = request.amount
        parallel_processing = request.parallel_processing
        delay_ms = request.delay_ms
        
        LOG.info(f"CreateOrder: product={product_id}, qty={quantity}, amount=${amount:.2f}, "
                f"parallel={parallel_processing}, delay={delay_ms}ms")
        
        # Initialize stubs if not already done
        await self._initialize_stubs()
        
        # Generate order ID
        order_id = str(uuid.uuid4())
        
        # Initialize metrics
        start_time = time.time()
        total_req_bytes = 0
        total_res_bytes = 0
        
        try:
            # Step 1: Create order in database
            success = await asyncio.get_event_loop().run_in_executor(
                executor, self.db.create_order, 
                order_id, product_id, quantity, amount, parallel_processing
            )
            
            if not success:
                return pb.CreateOrderResponse(
                    success=False,
                    order_id=order_id,
                    status="FAILED",
                    message="Failed to create order",
                    metrics=pb.OrderMetrics()
                )
            
            # Update order status to PROCESSING
            await asyncio.get_event_loop().run_in_executor(
                executor, self.db.update_order_status, order_id, "PROCESSING"
            )
            
            # Step 2: Check and reserve inventory
            inv_start = time.time()
            inventory_response = await self._reserve_inventory(
                order_id, product_id, quantity, delay_ms
            )
            inv_time = time.time() - inv_start
            
            if not inventory_response.success:
                # Inventory reservation failed
                await asyncio.get_event_loop().run_in_executor(
                    executor, self.db.update_order_status, 
                    order_id, "FAILED_OUT_OF_STOCK"
                )
                
                total_time = time.time() - start_time
                return pb.CreateOrderResponse(
                    success=False,
                    order_id=order_id,
                    status="FAILED_OUT_OF_STOCK",
                    message=inventory_response.message,
                    metrics=pb.OrderMetrics(
                        total_time=total_time,
                        inventory_time=inv_time,
                        total_request_bytes=inventory_response.request_bytes,
                        total_response_bytes=inventory_response.response_bytes
                    )
                )
            
            reservation_id = inventory_response.reservation_id
            total_req_bytes += inventory_response.request_bytes
            total_res_bytes += inventory_response.response_bytes
            
            # Update order with reservation ID
            await asyncio.get_event_loop().run_in_executor(
                executor, self.db.update_order_status, 
                order_id, "INVENTORY_RESERVED", None, None, reservation_id
            )
            
            # Step 3: Process payment and initiate tracking
            if parallel_processing:
                # Parallel mode: Execute payment and tracking concurrently
                LOG.info(f"Order {order_id}: Processing payment and tracking in parallel")
                payment_response, tracking_response, pay_time, track_time = \
                    await self._process_parallel(order_id, amount, delay_ms)
            else:
                # Sequential mode: Execute payment then tracking
                LOG.info(f"Order {order_id}: Processing payment and tracking sequentially")
                payment_response, tracking_response, pay_time, track_time = \
                    await self._process_sequential(order_id, amount, delay_ms)
            
            total_req_bytes += payment_response.request_bytes + tracking_response.request_bytes
            total_res_bytes += payment_response.response_bytes + tracking_response.response_bytes
            
            # Check if payment succeeded
            if not payment_response.success:
                # Payment failed - rollback inventory reservation
                LOG.warning(f"Order {order_id}: Payment failed, rolling back inventory")
                await self._rollback_inventory(order_id, reservation_id)
                
                await asyncio.get_event_loop().run_in_executor(
                    executor, self.db.update_order_status, 
                    order_id, "FAILED_PAYMENT"
                )
                
                total_time = time.time() - start_time
                return pb.CreateOrderResponse(
                    success=False,
                    order_id=order_id,
                    status="FAILED_PAYMENT",
                    reservation_id=reservation_id,
                    message=payment_response.message,
                    metrics=pb.OrderMetrics(
                        total_time=total_time,
                        inventory_time=inv_time,
                        payment_time=pay_time,
                        tracking_time=track_time,
                        total_request_bytes=total_req_bytes,
                        total_response_bytes=total_res_bytes
                    )
                )
            
            payment_id = payment_response.payment_id
            tracking_id = tracking_response.tracking_id if tracking_response.success else ""
            
            # Step 4: Update order to COMPLETED
            await asyncio.get_event_loop().run_in_executor(
                executor, self.db.update_order_status, 
                order_id, "COMPLETED", payment_id, tracking_id, None
            )
            
            # Commit inventory reservation (reduce actual stock)
            await asyncio.get_event_loop().run_in_executor(
                executor, self.db.commit_reservation, product_id, quantity
            )
            
            total_time = time.time() - start_time
            
            LOG.info(f"Order {order_id} completed successfully in {total_time:.3f}s")
            
            return pb.CreateOrderResponse(
                success=True,
                order_id=order_id,
                status="COMPLETED",
                payment_id=payment_id,
                tracking_id=tracking_id,
                reservation_id=reservation_id,
                message=f"Order processed successfully",
                metrics=pb.OrderMetrics(
                    total_time=total_time,
                    inventory_time=inv_time,
                    payment_time=pay_time,
                    tracking_time=track_time,
                    total_request_bytes=total_req_bytes,
                    total_response_bytes=total_res_bytes
                )
            )
            
        except Exception as e:
            LOG.error(f"Error processing order {order_id}: {e}")
            
            # Update order status to FAILED
            await asyncio.get_event_loop().run_in_executor(
                executor, self.db.update_order_status, order_id, "FAILED"
            )
            
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error processing order: {str(e)}")
            
            total_time = time.time() - start_time
            return pb.CreateOrderResponse(
                success=False,
                order_id=order_id,
                status="FAILED",
                message=f"Error: {str(e)}",
                metrics=pb.OrderMetrics(total_time=total_time)
            )
    
    async def _reserve_inventory(self, order_id: str, product_id: str, 
                                quantity: int, delay_ms: int) -> pb.ReserveStockResponse:
        """Reserve inventory for the order"""
        try:
            request = pb.ReserveStockRequest(
                order_id=order_id,
                product_id=product_id,
                quantity=quantity,
                delay_ms=delay_ms
            )
            
            response = await self.inventory_stub.ReserveStock(request, timeout=30.0)
            return response
            
        except grpc.aio.AioRpcError as e:
            LOG.error(f"Inventory reservation RPC error: {e}")
            return pb.ReserveStockResponse(
                success=False,
                reservation_id="",
                message=f"RPC Error: {e.details()}",
                request_bytes=0,
                response_bytes=0
            )
    
    async def _rollback_inventory(self, order_id: str, reservation_id: str):
        """Rollback inventory reservation"""
        try:
            request = pb.ReleaseStockRequest(
                order_id=order_id,
                reservation_id=reservation_id
            )
            
            await self.inventory_stub.ReleaseStock(request, timeout=10.0)
            LOG.info(f"Inventory rolled back for order {order_id}")
            
        except grpc.aio.AioRpcError as e:
            LOG.error(f"Failed to rollback inventory for order {order_id}: {e}")
    
    async def _process_sequential(self, order_id: str, amount: float, delay_ms: int):
        """Process payment and tracking sequentially"""
        # Process payment first
        pay_start = time.time()
        payment_response = await self._process_payment(order_id, amount, delay_ms)
        pay_time = time.time() - pay_start
        
        # Then initiate tracking
        track_start = time.time()
        tracking_response = await self._initiate_tracking(order_id, delay_ms)
        track_time = time.time() - track_start
        
        return payment_response, tracking_response, pay_time, track_time
    
    async def _process_parallel(self, order_id: str, amount: float, delay_ms: int):
        """Process payment and tracking in parallel"""
        start = time.time()
        
        # Execute both operations concurrently
        payment_task = self._process_payment(order_id, amount, delay_ms)
        tracking_task = self._initiate_tracking(order_id, delay_ms)
        
        payment_response, tracking_response = await asyncio.gather(
            payment_task, tracking_task
        )
        
        total_time = time.time() - start
        
        # For parallel processing, we report the total parallel time for both
        return payment_response, tracking_response, total_time, total_time
    
    async def _process_payment(self, order_id: str, amount: float, 
                              delay_ms: int) -> pb.ProcessPaymentResponse:
        """Process payment for the order"""
        try:
            request = pb.ProcessPaymentRequest(
                order_id=order_id,
                amount=amount,
                payment_method="credit_card",
                delay_ms=delay_ms
            )
            
            response = await self.payment_stub.ProcessPayment(request, timeout=30.0)
            return response
            
        except grpc.aio.AioRpcError as e:
            LOG.error(f"Payment processing RPC error: {e}")
            return pb.ProcessPaymentResponse(
                success=False,
                payment_id="",
                status="FAILED",
                message=f"RPC Error: {e.details()}",
                request_bytes=0,
                response_bytes=0
            )
    
    async def _initiate_tracking(self, order_id: str, delay_ms: int) -> pb.InitiateTrackingResponse:
        """Initiate tracking for the order"""
        try:
            request = pb.InitiateTrackingRequest(
                order_id=order_id,
                delay_ms=delay_ms
            )
            
            response = await self.tracking_stub.InitiateTracking(request, timeout=30.0)
            return response
            
        except grpc.aio.AioRpcError as e:
            LOG.error(f"Tracking initiation RPC error: {e}")
            return pb.InitiateTrackingResponse(
                success=False,
                tracking_id="",
                status="FAILED",
                message=f"RPC Error: {e.details()}",
                request_bytes=0,
                response_bytes=0
            )
    
    async def GetOrderStatus(self, request: pb.GetOrderStatusRequest, context) -> pb.GetOrderStatusResponse:
        """Get order status"""
        order_id = request.order_id
        
        LOG.info(f"GetOrderStatus: order={order_id}")
        
        try:
            # Get order from database
            order = await asyncio.get_event_loop().run_in_executor(
                executor, self.db.get_order, order_id
            )
            
            if not order:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Order not found: {order_id}")
                return pb.GetOrderStatusResponse(
                    order_id=order_id,
                    status="NOT_FOUND",
                    product_id="",
                    quantity=0,
                    amount=0.0,
                    payment_id="",
                    tracking_id="",
                    created_at="",
                    updated_at=""
                )
            
            return pb.GetOrderStatusResponse(
                order_id=order['order_id'],
                status=order['status'],
                product_id=order['product_id'],
                quantity=order['quantity'],
                amount=order['amount'],
                payment_id=order.get('payment_id', ''),
                tracking_id=order.get('tracking_id', ''),
                created_at=order['created_at'],
                updated_at=order['updated_at']
            )
            
        except Exception as e:
            LOG.error(f"Error getting order status for {order_id}: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error getting order status: {str(e)}")
            return pb.GetOrderStatusResponse(
                order_id=order_id,
                status="ERROR",
                product_id="",
                quantity=0,
                amount=0.0,
                payment_id="",
                tracking_id="",
                created_at="",
                updated_at=""
            )
    
    async def ClearOrders(self, request: pb.Empty, context) -> pb.Empty:
        """Clear all orders (for testing)"""
        LOG.info("ClearOrders: clearing all order data")
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                executor, self.db.clear_orders
            )
            LOG.info("Orders cleared successfully")
            return pb.Empty()
            
        except Exception as e:
            LOG.error(f"Error clearing orders: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error clearing orders: {str(e)}")
            return pb.Empty()
    
    async def close(self):
        """Close gRPC channels"""
        if self.inventory_channel:
            await self.inventory_channel.close()
        if self.payment_channel:
            await self.payment_channel.close()
        if self.tracking_channel:
            await self.tracking_channel.close()


async def serve(host: str = "0.0.0.0", port: int = 50050):
    """Start the Order gRPC server"""
    server = grpc.aio.server()
    rpc.add_OrderServiceServicer_to_server(OrderServicer(), server)
    server.add_insecure_port(f"{host}:{port}")
    
    LOG.info(f"Starting Order gRPC server on {host}:{port}")
    await server.start()
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        LOG.info("Shutting down Order service")
        await server.stop(grace=5)


if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        LOG.info("Order service stopped")
