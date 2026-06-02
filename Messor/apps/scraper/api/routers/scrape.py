"""
WebSocket Scraper Module

This module implements a WebSocket interface for monitoring and controlling web scraping processes.
It provides real-time visibility into the scraping process, allowing clients to follow 
the progress and receive results as they become available.

The implementation uses a thread-safe message queue system to handle communication between
the synchronous scraper service and the asynchronous WebSocket interface.

Author: juliandelarosa@icloud.com
Date: July, 23, 2023
"""

import os
import sys
import asyncio
import threading
import time
import queue
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

import __main__

sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
from api.utils.api_security import _api_key_is_valid

# Set up logging for this module
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create router for FastAPI
router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections and message queues for each client.
    
    This class is responsible for:
    - Tracking active WebSocket connections
    - Managing message queues for each connection
    - Providing thread-safe methods to send messages to clients
    """
    
    def __init__(self):
        """Initialize the connection manager."""
        self.active_connections: List[WebSocket] = []
        self.message_queues: Dict[WebSocket, queue.Queue] = {}  # Stores message queues per websocket

    async def connect(self, websocket: WebSocket) -> None:
        """
        Accept a new WebSocket connection and set up a message queue for it.
        
        Args:
            websocket: The WebSocket connection to manage
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        self.message_queues[websocket] = queue.Queue()
        logger.debug(f"New connection added. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection and clean up its resources.
        
        Args:
            websocket: The WebSocket connection to remove
        """
        self.active_connections.remove(websocket)
        if websocket in self.message_queues:
            del self.message_queues[websocket]
        logger.debug(f"Connection removed. Total connections: {len(self.active_connections)}")

    def queue_message(self, message: str, websocket: WebSocket) -> bool:
        """
        Thread-safe method to queue a message for sending to a WebSocket client.
        
        This method can be called from any thread to safely queue messages
        for delivery to the WebSocket client.
        
        Args:
            message: The message to queue
            websocket: The WebSocket connection to send to
            
        Returns:
            bool: True if message was queued successfully, False otherwise
        """
        if websocket in self.message_queues:
            self.message_queues[websocket].put(message)
            return True
        return False

    async def process_message_queue(self, websocket: WebSocket) -> None:
        """
        Process messages from the queue and send them to the websocket.
        
        This method should be called from the asyncio event loop.
        
        Args:
            websocket: The WebSocket connection to process messages for
        """
        if websocket not in self.message_queues:
            return

        queue = self.message_queues[websocket]
        while not queue.empty():
            message = queue.get()
            try:
                await websocket.send_text(message)
                logger.debug(f"Message sent: {message}")
            except Exception as e:
                logger.error(f"Failed to send message: {str(e)}")
            finally:
                queue.task_done()

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """
        Send a message directly to a WebSocket client.
        
        This method should only be used from an async context (not from threads).
        For thread-safe message sending, use queue_message instead.
        
        Args:
            message: The message to send
            websocket: The WebSocket connection to send to
        """
        try:
            await websocket.send_text(message)
            logger.debug(f"Message sent: {message}")
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")


# Create a single instance of the connection manager
manager = ConnectionManager()


@router.websocket("/api/scrape/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for scraper monitoring and control.
    
    This endpoint:
    1. Authenticates the client using an API key
    2. Manages the WebSocket connection lifecycle
    3. Processes incoming commands
    4. Handles message queue processing
    
    Commands:
        start_scrape: Begin the scraping process
    """
    await manager.connect(websocket)
    try:
        # Get API key from query parameters
        api_key = websocket.query_params.get('api_key')
        logger.debug(f"Received API key: {api_key[:5]}*** (masked for security)")

        # Validate API key
        if not api_key or not _api_key_is_valid(api_key):
            logger.warning(f"Invalid or missing API key")
            await manager.send_personal_message("Invalid API key", websocket)
            await websocket.close()
            return

        # Connection established successfully
        logger.info(f"Successful WebSocket connection established")
        await manager.send_personal_message("Connected to scraper WebSocket", websocket)

        # Start a task to process the message queue
        queue_processor = asyncio.create_task(message_queue_processor(websocket))

        try:
            # Main message processing loop
            while True:
                try:
                    data = await websocket.receive_text()
                    logger.debug(f"Received message: {data}")
                    
                    # Handle commands
                    if data == "start_scrape":
                        logger.info("Received start_scrape command")
                        await manager.send_personal_message("Received start_scrape command", websocket)
                        
                        # Create a separate task for scraping to prevent blocking
                        asyncio.create_task(start_scrape(websocket))
                        
                        # Send immediate confirmation
                        await manager.send_personal_message("Scrape started in background", websocket)
                    else:
                        await manager.send_personal_message(f"Received: {data}", websocket)
                        
                except WebSocketDisconnect:
                    # Client disconnected
                    break
                
        finally:
            # Cancel the queue processor when the websocket disconnects
            queue_processor.cancel()
            try:
                await queue_processor
            except asyncio.CancelledError:
                pass
    
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        manager.disconnect(websocket)
        logger.info("WebSocket disconnected")


async def message_queue_processor(websocket: WebSocket) -> None:
    """
    Process messages from the queue at regular intervals.
    
    This coroutine runs in the background for each WebSocket connection,
    periodically checking the message queue and sending any pending messages.
    
    Args:
        websocket: The WebSocket connection to process messages for
        
    Raises:
        asyncio.CancelledError: When the task is cancelled during cleanup
    """
    try:
        while True:
            await manager.process_message_queue(websocket)
            await asyncio.sleep(0.1)  # Process queue 10 times per second
    except asyncio.CancelledError:
        # Final processing of any remaining messages before exiting
        await manager.process_message_queue(websocket)
        raise  # Re-raise to properly complete cancellation


class ThreadSafeLogger:
    """
    A proxy logger that safely queues messages for the WebSocket.
    
    This class intercepts logging calls from the scraper and forwards them
    to both the original logger and the WebSocket client via a thread-safe queue.
    """
    
    def __init__(self, original_logger, websocket: WebSocket, manager: ConnectionManager):
        """
        Initialize the thread-safe logger.
        
        Args:
            original_logger: The original logger to forward messages to
            websocket: The WebSocket connection to send messages to
            manager: The connection manager to queue messages with
        """
        self.original_logger = original_logger
        self.websocket = websocket
        self.manager = manager
        self.message_count = 0
        
    def info(self, message: str) -> None:
        """
        Log an info message and queue it for WebSocket delivery.
        
        Args:
            message: The message to log
        """
        self.original_logger.info(message)
        self.message_count += 1
        self.manager.queue_message(f"INFO #{self.message_count}: {message}", self.websocket)
        
    def error(self, message: str) -> None:
        """
        Log an error message and queue it for WebSocket delivery.
        
        Args:
            message: The message to log
        """
        self.original_logger.error(message)
        self.message_count += 1
        self.manager.queue_message(f"ERROR #{self.message_count}: {message}", self.websocket)
        
    def warning(self, message: str) -> None:
        """
        Log a warning message and queue it for WebSocket delivery.
        
        Args:
            message: The message to log
        """
        self.original_logger.warning(message)
        self.message_count += 1
        self.manager.queue_message(f"WARNING #{self.message_count}: {message}", self.websocket)


async def start_scrape(websocket: WebSocket) -> None:
    """
    Execute the scraping process and monitor progress.
    
    This coroutine:
    1. Initializes the scraping process
    2. Temporarily replaces the scraper's logger with a thread-safe version
    3. Runs the scraper in a background thread
    4. Processes and reports the results
    
    Args:
        websocket: The WebSocket connection to send updates to
    """
    logger.info("Starting scrape process")
    
    try:
        # Send initial message
        await manager.send_personal_message("Scrape initiated", websocket)
        
        # Get reference to the scraper service
        scraper = __main__.app.command_processor.scraper_service
        scraper_type = type(scraper).__name__
        await manager.send_personal_message(f"Using scraper: {scraper_type}", websocket)
        
        # Start the scraping process
        await manager.send_personal_message("Starting scraping process...", websocket)
        
        # Create a function that will run in the thread pool
        def run_scraper_with_logging():
            """
            Run the scraper with intercepted logging.
            
            This function:
            1. Saves the original logger
            2. Replaces it with our thread-safe logger
            3. Runs the scraping process
            4. Restores the original logger
            
            Returns:
                The result of the scraping process
            """
            # Save the original logger
            original_logger = scraper.logger
            
            try:
                # Replace with our thread-safe logger
                scraper.logger = ThreadSafeLogger(original_logger, websocket, manager)
                
                # Run the scraping process
                return scraper.execute_scraping_process()
            finally:
                # Restore the original logger
                scraper.logger = original_logger
        
        # Run the scraper in a thread pool and await its result
        start_time = time.time()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_scraper_with_logging)
        execution_time = time.time() - start_time
        
        # Process the result
        await manager.send_personal_message(f"Scraping completed in {execution_time:.2f} seconds", websocket)
        
        if result:
            await manager.send_personal_message(f"Scraped {len(result)} outlets/sources successfully", websocket)
            
            # Send more detailed results (limited to 5 sessions)
            try:
                import json
                for i, session in enumerate(result[:5]):
                    # Extract basic info that should be available on any session object
                    session_summary = {
                        "outlet": str(session.outlet) if hasattr(session, 'outlet') else "Unknown",
                        "articles_count": len(session.articles) if hasattr(session, 'articles') else 0,
                        "success": session.success if hasattr(session, 'success') else False
                    }
                    await manager.send_personal_message(
                        f"Session {i+1} summary: {json.dumps(session_summary)}", 
                        websocket
                    )
                
                if len(result) > 5:
                    await manager.send_personal_message(f"... and {len(result) - 5} more sessions", websocket)
            except Exception as e:
                logger.error(f"Error sending detailed results: {str(e)}")
                await manager.send_personal_message(f"Error sending detailed results: {str(e)}", websocket)
        else:
            await manager.send_personal_message("No scraping results returned", websocket)
        
    except Exception as e:
        error_msg = f"Error in scrape process: {str(e)}"
        logger.error(error_msg)
        await manager.send_personal_message(error_msg, websocket)
    finally:
        await manager.send_personal_message("Scraping process finished", websocket)
        logger.info("Scraping process finished")


@router.get("/api/scrape/status")
async def scrape_status() -> Dict[str, str]:
    """
    Endpoint to check the status of the scraper service.
    
    Returns:
        Dict[str, str]: Status information
    """
    return {"status": "Ready to scrape"}


# Session storage for remembering view counts
_session_store = {}
_current_session_id = None  # Will be set when results are fetched

# Try to import RabbitMQ libraries
try:
    import pika
    import json
    import uuid
    import os
    from pathlib import Path
    HAS_RABBITMQ = True
except ImportError:
    logger.warning("RabbitMQ libraries not available, falling back to mock data")
    HAS_RABBITMQ = False

# Function to load queue configuration
def load_rabbit_config():
    """Load RabbitMQ configuration from queue.json file"""
    try:
        # Try to locate the queue.json file
        config_paths = [
            os.path.join(os.path.dirname(__file__), '../../../data/rabbit/queue.json'),
            os.path.join(os.path.dirname(__file__), '../../../data/local/rabbit/queue.json'),
            os.path.join(os.path.dirname(__file__), '../../../data/local/queue.json')
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        
        # If not found, return default config
        logger.warning("RabbitMQ config not found, using defaults")
        return {
            "host": "localhost",
            "port": 5672,
            "vhost": "/",
            "queue": "messor.articles",
            "username": "guest",
            "password": "guest"
        }
    except Exception as e:
        logger.error(f"Error loading RabbitMQ config: {str(e)}")
        return None

# Function to fetch results from RabbitMQ
def fetch_from_rabbitmq():
    """Fetch the latest scraping results from RabbitMQ"""
    try:
        # Load RabbitMQ configuration
        config = load_rabbit_config()
        if not config:
            return None
            
        # Connect to RabbitMQ
        credentials = pika.PlainCredentials(config.get('username', 'guest'), config.get('password', 'guest'))
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=config.get('host', 'localhost'),
                port=config.get('port', 5672),
                virtual_host=config.get('vhost', '/'),
                credentials=credentials
            )
        )
        
        # Create a channel
        channel = connection.channel()
        
        # Declare the queue passively (doesn't create if doesn't exist)
        queue_name = config.get('queue', 'messor.articles')
        channel.queue_declare(queue=queue_name, passive=True)
        
        # Try to get a message
        method_frame, header_frame, body = channel.basic_get(queue=queue_name, auto_ack=True)
        
        # Close the connection
        connection.close()
        
        # Process the message if we got one
        if method_frame:
            data = json.loads(body.decode('utf-8'))
            return format_scrape_results(data)
        else:
            logger.info("No messages in the queue")
            return None
    except Exception as e:
        logger.error(f"Error fetching from RabbitMQ: {str(e)}")
        return None

# Function to format scraping results into the expected format
def format_scrape_results(raw_data):
    """Format raw scraping results into the expected API response format"""
    global _current_session_id
    
    try:
        # Generate a session ID if we don't have one yet
        if not _current_session_id:
            _current_session_id = f"session-{uuid.uuid4().hex[:8]}"
        
        # Extract the key information
        start_time = raw_data.get('data', {}).get('start_time', '')
        end_time = raw_data.get('data', {}).get('end_time', '')
        total_articles = raw_data.get('data', {}).get('total_articles', 0)
        failed_articles = raw_data.get('data', {}).get('failed_articles', 0)
        successful_articles = raw_data.get('data', {}).get('successful_articles', 0)
        duration = raw_data.get('data', {}).get('duration', 0)
        success_rate = raw_data.get('data', {}).get('success_rate', 0)
        outlet = raw_data.get('data', {}).get('outlet', 'Unknown')
        
        # Create a formatted result
        result = {
            "id": _current_session_id,
            "start_time": start_time,
            "end_time": end_time,
            "total_outlets_scraped": 1,  # Assuming one outlet per message
            "total_articles_scraped": total_articles,
            "overall_success_rate": success_rate,
            "duration": duration,
            "views": 0,
            "last_viewed": None,
            "results": [
                {
                    "outlet": {"name": outlet, "url": f"https://www.{outlet.lower().replace(' ', '')}.com", "type": "news"},
                    "total_articles": total_articles,
                    "successful_scrapes": successful_articles,
                    "failed_scrapes": failed_articles,
                    "duration": duration,
                    "errors": []
                }
            ]
        }
        
        return result
    except Exception as e:
        logger.error(f"Error formatting scrape results: {str(e)}")
        return None

# Try to read results from disk if RabbitMQ is not available
def read_results_from_disk():
    """Read scraping results from a JSON file on disk"""
    try:
        # Look for result files in common locations
        base_dirs = [
            os.path.join(os.path.dirname(__file__), '../../../data/scrapes'),
            os.path.join(os.path.dirname(__file__), '../../../data')
        ]
        
        for base_dir in base_dirs:
            if not os.path.exists(base_dir):
                continue
                
            # Find the most recent .json file
            json_files = list(Path(base_dir).glob('**/*.json'))
            if not json_files:
                continue
                
            # Sort by modification time (most recent first)
            latest_file = max(json_files, key=os.path.getmtime)
            
            # Read and parse the file
            with open(latest_file, 'r') as f:
                data = json.load(f)
                
            # Format the results
            result = format_scrape_results(data)
            if result:
                return result
    except Exception as e:
        logger.error(f"Error reading results from disk: {str(e)}")
    
    return None

@router.get("/api/scrape/results")
async def get_scraping_results() -> Dict[str, Any]:
    """
    Endpoint to get the results of the most recent scraping session.
    
    Returns:
        Dict[str, Any]: Session data including results
    """
    global _current_session_id, _session_store
    
    # Try to fetch results from RabbitMQ
    if HAS_RABBITMQ:
        result = fetch_from_rabbitmq()
        if result:
            # Store the result with its session ID
            _current_session_id = result["id"]
            _session_store[_current_session_id] = result
            return result
    
    # If no RabbitMQ result, try to read from disk
    result = read_results_from_disk()
    if result:
        # Store the result with its session ID
        _current_session_id = result["id"]
        _session_store[_current_session_id] = result
        return result
    
    # If we have a previously fetched result, return that
    if _current_session_id and _current_session_id in _session_store:
        return _session_store[_current_session_id]
    
    # If all else fails, return a mock result
    logger.warning("No real scraping results available, using mock data")
    _current_session_id = f"mock-session-{uuid.uuid4().hex[:8]}"
    _session_store[_current_session_id] = {
        "id": _current_session_id,
        "total_outlets_scraped": 5,
        "total_articles_scraped": 700,
        "overall_success_rate": 0.53,
        "duration": 432.47,
        "views": 0,
        "last_viewed": None,
        "results": [
            {
                "outlet": {"name": "ABC News", "url": "https://www.abcnews.com", "type": "news"},
                "total_articles": 700,
                "successful_scrapes": 368,
                "failed_scrapes": 332,
                "duration": 432.47,
                "errors": []
            }
        ]
    }
    
    return _session_store[_current_session_id]


@router.post("/api/scrape/session/{session_id}/view")
async def record_session_view(session_id: str) -> Dict[str, Any]:
    """
    Endpoint to record a view of a scraping session.
    
    Args:
        session_id: The ID of the session to record a view for
        
    Returns:
        Dict[str, Any]: Updated view count information
    """
    global _session_store
    
    # If no session store or session ID not found, return a default response
    if session_id not in _session_store:
        logger.warning(f"Session ID {session_id} not found in session store")
        # Return a default response to prevent errors
        return {
            "session_id": session_id,
            "views": 1,
            "last_viewed": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    
    # Increment the view count
    session = _session_store[session_id]
    if "views" not in session:
        session["views"] = 0
    session["views"] += 1
    session["last_viewed"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # Log for tracking
    logger.info(f"Recorded view for session {session_id}. Total views: {session['views']}")
    
    return {
        "session_id": session_id,
        "views": session["views"],
        "last_viewed": session["last_viewed"]
    }