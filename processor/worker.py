import time
import logging
from api.queue_handler import queue_handler
from api.models import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventProcessor:
    def __init__(self):
        self.running = False

    def start(self):
        """Start the event processor"""
        self.running = True
        logger.info("Event processor started")

        try:
            while self.running:
                try:
                    # Dequeue event from Redis
                    event = queue_handler.dequeue(timeout=1)

                    if event:
                        # Process and insert into database
                        self.process_event(event)
                    else:
                        # No event available, wait a bit
                        time.sleep(0.1)

                except KeyboardInterrupt:
                    logger.info("Processor interrupted by user")
                    self.stop()
                    break
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
                    # Continue processing despite errors
                    time.sleep(1)

        finally:
            self.cleanup()

    def process_event(self, event):
        """Process a single event"""
        try:
            logger.info(f"Processing event for site: {event.get('site_id')}")

            # Insert into database
            db.insert_event(event)

            logger.info(f"Event processed successfully: {event.get('site_id')}")

        except Exception as e:
            logger.error(f"Failed to process event: {e}")
            # In production, you might want to:
            # - Retry the event
            # - Move to a dead letter queue
            # - Send alerts
            raise

    def stop(self):
        """Stop the processor gracefully"""
        logger.info("Stopping event processor...")
        self.running = False

    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up processor resources")
        queue_handler.close()

if __name__ == '__main__':
    processor = EventProcessor()

    try:
        # Initialize database schema if needed
        db.init_schema()
        logger.info("Database schema verified")

        # Connect to queue
        queue_handler.connect()
        logger.info("Queue connection established")

        # Start processing
        processor.start()

    except Exception as e:
        logger.error(f"Processor startup failed: {e}")
        raise
