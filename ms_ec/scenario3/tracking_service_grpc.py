"""
Tracking Service - gRPC Implementation
Handles real-time order tracking with multiple status stages
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
LOG = logging.getLogger("tracking_service")

# Thread pool for blocking database operations
executor = ThreadPoolExecutor(max_workers=20)

# Tracking status progression stages
TRACKING_STAGES = [
    "INITIATED",
    "PROCESSING",
    "SHIPPED",
    "IN_TRANSIT",
    "OUT_FOR_DELIVERY",
    "DELIVERED"
]


class TrackingServicer(rpc.TrackingServiceServicer):
    """gRPC Tracking Service Implementation"""
    
    def __init__(self):
        self.db = get_database()
        LOG.info("Tracking Service initialized")
    
    async def InitiateTracking(self, request: pb.InitiateTrackingRequest, context) -> pb.InitiateTrackingResponse:
        """Initiate tracking for an order"""
        order_id = request.order_id
        delay_ms = request.delay_ms
        
        # Calculate request size
        req_size = request.ByteSize()
        
        LOG.info(f"InitiateTracking: order={order_id}, delay={delay_ms}ms")
        
        try:
            # Generate tracking ID
            tracking_id = str(uuid.uuid4())
            
            # Inject artificial delay if specified
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000.0)
            
            # Create tracking record with initial status
            initial_status = TRACKING_STAGES[0]  # INITIATED
            success = await asyncio.get_event_loop().run_in_executor(
                executor, self.db.create_tracking, tracking_id, order_id, initial_status
            )
            
            if success:
                response = pb.InitiateTrackingResponse(
                    success=True,
                    tracking_id=tracking_id,
                    status=initial_status,
                    message=f"Tracking initiated for order {order_id}",
                    request_bytes=req_size,
                    response_bytes=0
                )
                LOG.info(f"Tracking initiated: {tracking_id} for order {order_id}")
                
                # Start background task to progress through tracking stages
                asyncio.create_task(self._progress_tracking(tracking_id))
            else:
                response = pb.InitiateTrackingResponse(
                    success=False,
                    tracking_id="",
                    status="ERROR",
                    message=f"Failed to initiate tracking for order {order_id}",
                    request_bytes=req_size,
                    response_bytes=0
                )
                LOG.error(f"Failed to initiate tracking for order {order_id}")
            
            # Set response size
            response.response_bytes = response.ByteSize()
            
            # Send metadata
            await context.send_initial_metadata((
                ("request-bytes", str(req_size)),
                ("response-bytes", str(response.response_bytes)),
            ))
            
            return response
            
        except Exception as e:
            LOG.error(f"Error initiating tracking for order {order_id}: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error initiating tracking: {str(e)}")
            return pb.InitiateTrackingResponse(
                success=False,
                tracking_id="",
                status="ERROR",
                message=f"Error: {str(e)}",
                request_bytes=req_size,
                response_bytes=0
            )
    
    async def _progress_tracking(self, tracking_id: str):
        """
        Background task to progress tracking through stages
        Simulates real-world tracking updates over time
        """
        try:
            # Wait a bit before starting progression
            await asyncio.sleep(1.0)
            
            # Progress through each stage
            for stage in TRACKING_STAGES[1:]:  # Skip INITIATED as it's already set
                await asyncio.sleep(2.0)  # Wait between stages
                
                success = await asyncio.get_event_loop().run_in_executor(
                    executor, self.db.update_tracking_status, tracking_id, stage
                )
                
                if success:
                    LOG.info(f"Tracking {tracking_id} updated to {stage}")
                else:
                    LOG.error(f"Failed to update tracking {tracking_id} to {stage}")
                    break
                
        except Exception as e:
            LOG.error(f"Error in tracking progression for {tracking_id}: {e}")
    
    async def UpdateTrackingStatus(self, request: pb.UpdateTrackingStatusRequest, context) -> pb.UpdateTrackingStatusResponse:
        """Manually update tracking status"""
        tracking_id = request.tracking_id
        status = request.status
        
        LOG.info(f"UpdateTrackingStatus: tracking={tracking_id}, status={status}")
        
        try:
            success = await asyncio.get_event_loop().run_in_executor(
                executor, self.db.update_tracking_status, tracking_id, status
            )
            
            if success:
                message = f"Tracking status updated to {status}"
                LOG.info(f"Tracking {tracking_id} updated to {status}")
            else:
                message = f"Failed to update tracking status for {tracking_id}"
                LOG.error(message)
            
            return pb.UpdateTrackingStatusResponse(success=success, message=message)
            
        except Exception as e:
            LOG.error(f"Error updating tracking {tracking_id}: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error updating tracking: {str(e)}")
            return pb.UpdateTrackingStatusResponse(
                success=False,
                message=f"Error: {str(e)}"
            )
    
    async def GetTrackingStatus(self, request: pb.GetTrackingStatusRequest, context) -> pb.GetTrackingStatusResponse:
        """Get current tracking status"""
        tracking_id = request.tracking_id
        
        LOG.info(f"GetTrackingStatus: tracking={tracking_id}")
        
        try:
            # Get tracking from database
            tracking = await asyncio.get_event_loop().run_in_executor(
                executor, self.db.get_tracking, tracking_id
            )
            
            if not tracking:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Tracking not found: {tracking_id}")
                return pb.GetTrackingStatusResponse(
                    tracking_id=tracking_id,
                    order_id="",
                    status="NOT_FOUND",
                    timestamp="",
                    status_history=[]
                )
            
            # Parse status history
            status_history = tracking['status_history'].split(',') if tracking['status_history'] else []
            
            return pb.GetTrackingStatusResponse(
                tracking_id=tracking['tracking_id'],
                order_id=tracking['order_id'],
                status=tracking['status'],
                timestamp=tracking['updated_at'],
                status_history=status_history
            )
            
        except Exception as e:
            LOG.error(f"Error getting tracking status for {tracking_id}: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error getting tracking status: {str(e)}")
            return pb.GetTrackingStatusResponse(
                tracking_id=tracking_id,
                order_id="",
                status="ERROR",
                timestamp="",
                status_history=[]
            )
    
    async def ClearTracking(self, request: pb.Empty, context) -> pb.Empty:
        """Clear all tracking records (for testing)"""
        LOG.info("ClearTracking: clearing all tracking data")
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                executor, self.db.clear_tracking
            )
            LOG.info("Tracking records cleared successfully")
            return pb.Empty()
            
        except Exception as e:
            LOG.error(f"Error clearing tracking: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error clearing tracking: {str(e)}")
            return pb.Empty()


async def serve(host: str = "0.0.0.0", port: int = 50053):
    """Start the Tracking gRPC server"""
    server = grpc.aio.server()
    rpc.add_TrackingServiceServicer_to_server(TrackingServicer(), server)
    server.add_insecure_port(f"{host}:{port}")
    
    LOG.info(f"Starting Tracking gRPC server on {host}:{port}")
    await server.start()
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        LOG.info("Shutting down Tracking service")
        await server.stop(grace=5)


if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        LOG.info("Tracking service stopped")
