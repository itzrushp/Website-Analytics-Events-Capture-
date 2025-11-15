import redis
import json
import logging
from api.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueueHandler:
    def __init__(self):
        self.redis_client = None
        self.queue_name = 'analytics_events'

    def connect(self):
        """Establish Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established")
            return self.redis_client
        except Exception as e:
            logger.error(f"Redis connection error: {e}")
            raise

    def enqueue(self, event_data):
        """Add event to the queue"""
        try:
            if not self.redis_client:
                self.connect()

            # Serialize event data to JSON
            event_json = json.dumps(event_data)

            # Push to Redis list (LPUSH for FIFO with RPOP)
            self.redis_client.lpush(self.queue_name, event_json)
            logger.info(f"Event enqueued: {event_data.get('site_id')}")

            return True
        except Exception as e:
            logger.error(f"Error enqueuing event: {e}")
            raise

    def dequeue(self, timeout=1):
        """Remove and return event from the queue"""
        try:
            if not self.redis_client:
                self.connect()

            # BRPOP blocks until an item is available or timeout
            result = self.redis_client.brpop(self.queue_name, timeout=timeout)

            if result:
                _, event_json = result
                event_data = json.loads(event_json)
                logger.info(f"Event dequeued: {event_data.get('site_id')}")
                return event_data

            return None
        except Exception as e:
            logger.error(f"Error dequeuing event: {e}")
            return None

    def get_queue_length(self):
        """Get current queue length"""
        try:
            if not self.redis_client:
                self.connect()

            return self.redis_client.llen(self.queue_name)
        except Exception as e:
            logger.error(f"Error getting queue length: {e}")
            return 0

    def close(self):
        """Close Redis connection"""
        if self.redis_client:
            self.redis_client.close()
            logger.info("Redis connection closed")

queue_handler = QueueHandler()
