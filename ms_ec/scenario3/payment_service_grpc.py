"""
Payment Service - gRPC Implementation
Handles payment processing and validation
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
LOG = logging.getLogger("payment_service")

# Thread pool for blocking database operations
executor = ThreadPoolExecutor(max_workers=20)


class PaymentServicer(rpc.PaymentServiceServicer):
    """gRPC Payment Service Implementation"""
    
    def __init__(self):
        self.db = get_database()
        LOG.info("Payment Service initialized")
    
    async def ProcessPayment(self, request: pb.ProcessPaymentRequest, context) -> pb.ProcessPaymentResponse:
        """Process payment for an order"""
        order_id = request.order_id
        amount = request.amount
        payment_method = request.payment_method or "credit_card"
        delay_ms = request.delay_ms
        
        # Calculate request size
        req_size = request.ByteSize()
        
        LOG.info(f"ProcessPayment: order={order_id}, amount=${amount:.2f}, method={payment_method}, delay={delay_ms}ms")
        
        try:
            # Generate payment ID
            payment_id = str(uuid.uuid4())
            
            # Create payment record
            success = await asyncio.get_event_loop().run_in_executor(
                executor, self.db.create_payment, payment_id, order_id, amount, payment_method
            )
            
            if not success:
                response = pb.ProcessPaymentResponse(
                    success=False,
                    payment_id="",
                    status="FAILED",
                    message="Failed to create payment record",
                    request_bytes=req_size,
                    response_bytes=0
                )
                response.response_bytes = response.ByteSize()
                return response
            
            # Inject artificial delay to simulate payment processing
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000.0)
            
            # Simulate payment validation
            # In real scenario, this would call external payment gateway
            payment_successful = await self._validate_payment(amount, payment_method)
            
            if payment_successful:
                # Update payment status to completed
                await asyncio.get_event_loop().run_in_executor(
                    executor, self.db.update_payment_status, payment_id, "COMPLETED"
                )
                
                response = pb.ProcessPaymentResponse(
                    success=True,
                    payment_id=payment_id,
                    status="COMPLETED",
                    message=f"Payment processed successfully: ${amount:.2f}",
                    request_bytes=req_size,
                    response_bytes=0
                )
                LOG.info(f"Payment completed: {payment_id} for order {order_id}")
            else:
                # Update payment status to failed
                await asyncio.get_event_loop().run_in_executor(
                    executor, self.db.update_payment_status, payment_id, "FAILED"
                )
                
                response = pb.ProcessPaymentResponse(
                    success=False,
                    payment_id=payment_id,
                    status="FAILED",
                    message="Payment validation failed",
                    request_bytes=req_size,
                    response_bytes=0
                )
                LOG.warning(f"Payment failed: {payment_id} for order {order_id}")
            
            # Set response size
            response.response_bytes = response.ByteSize()
            
            # Send metadata
            await context.send_initial_metadata((
                ("request-bytes", str(req_size)),
                ("response-bytes", str(response.response_bytes)),
            ))
            
            return response
            
        except Exception as e:
            LOG.error(f"Error processing payment for order {order_id}: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error processing payment: {str(e)}")
            return pb.ProcessPaymentResponse(
                success=False,
                payment_id="",
                status="ERROR",
                message=f"Error: {str(e)}",
                request_bytes=req_size,
                response_bytes=0
            )
    
    async def _validate_payment(self, amount: float, payment_method: str) -> bool:
        """
        Simulate payment validation
        In production, this would integrate with payment gateways like Stripe, PayPal, etc.
        """
        # Simulate validation logic
        # For demo purposes, we'll accept all payments with amount > 0
        await asyncio.sleep(0.01)  # Simulate network call
        
        if amount <= 0:
            LOG.warning(f"Invalid payment amount: {amount}")
            return False
        
        if payment_method not in ["credit_card", "debit_card", "paypal", "bank_transfer"]:
            LOG.warning(f"Invalid payment method: {payment_method}")
            return False
        
        # Simulate 99% success rate
        import random
        return random.random() < 0.99
    
    async def GetPaymentStatus(self, request: pb.GetPaymentStatusRequest, context) -> pb.GetPaymentStatusResponse:
        """Get payment status"""
        payment_id = request.payment_id
        
        LOG.info(f"GetPaymentStatus: payment={payment_id}")
        
        try:
            # Get payment from database
            payment = await asyncio.get_event_loop().run_in_executor(
                executor, self.db.get_payment, payment_id
            )
            
            if not payment:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Payment not found: {payment_id}")
                return pb.GetPaymentStatusResponse(
                    payment_id=payment_id,
                    status="NOT_FOUND",
                    amount=0.0,
                    timestamp=""
                )
            
            return pb.GetPaymentStatusResponse(
                payment_id=payment['payment_id'],
                status=payment['status'],
                amount=payment['amount'],
                timestamp=payment['created_at']
            )
            
        except Exception as e:
            LOG.error(f"Error getting payment status for {payment_id}: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error getting payment status: {str(e)}")
            return pb.GetPaymentStatusResponse(
                payment_id=payment_id,
                status="ERROR",
                amount=0.0,
                timestamp=""
            )
    
    async def ClearPayments(self, request: pb.Empty, context) -> pb.Empty:
        """Clear all payments (for testing)"""
        LOG.info("ClearPayments: clearing all payment data")
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                executor, self.db.clear_payments
            )
            LOG.info("Payments cleared successfully")
            return pb.Empty()
            
        except Exception as e:
            LOG.error(f"Error clearing payments: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error clearing payments: {str(e)}")
            return pb.Empty()


async def serve(host: str = "0.0.0.0", port: int = 50052):
    """Start the Payment gRPC server"""
    server = grpc.aio.server()
    rpc.add_PaymentServiceServicer_to_server(PaymentServicer(), server)
    server.add_insecure_port(f"{host}:{port}")
    
    LOG.info(f"Starting Payment gRPC server on {host}:{port}")
    await server.start()
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        LOG.info("Shutting down Payment service")
        await server.stop(grace=5)


if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        LOG.info("Payment service stopped")
