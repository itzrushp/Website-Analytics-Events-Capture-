import psycopg2
from psycopg2.extras import RealDictCursor
from api.config import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.conn = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(
                host=config.POSTGRES_HOST,
                port=config.POSTGRES_PORT,
                database=config.POSTGRES_DB,
                user=config.POSTGRES_USER,
                password=config.POSTGRES_PASSWORD
            )
            logger.info("Database connection established")
            return self.conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def init_schema(self):
        """Initialize database schema"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Create events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id SERIAL PRIMARY KEY,
                    site_id VARCHAR(255) NOT NULL,
                    event_type VARCHAR(100) NOT NULL,
                    path VARCHAR(500),
                    user_id VARCHAR(255),
                    timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_site_timestamp (site_id, timestamp),
                    INDEX idx_site_date (site_id, DATE(timestamp))
                );
            """)

            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_site_id ON events(site_id);
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp);
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_id ON events(user_id);
            """)

            conn.commit()
            logger.info("Database schema initialized successfully")
            cursor.close()

        except Exception as e:
            logger.error(f"Schema initialization error: {e}")
            raise
        finally:
            self.close()

    def insert_event(self, event_data):
        """Insert a single event into the database"""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO events (site_id, event_type, path, user_id, timestamp)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                event_data['site_id'],
                event_data['event_type'],
                event_data.get('path'),
                event_data.get('user_id'),
                event_data['timestamp']
            ))

            conn.commit()
            cursor.close()

        except Exception as e:
            logger.error(f"Error inserting event: {e}")
            raise
        finally:
            self.close()

    def get_stats(self, site_id, date=None):
        """Get aggregated statistics for a site"""
        try:
            conn = self.connect()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Build query based on whether date is provided
            if date:
                query = """
                    SELECT 
                        COUNT(*) as total_views,
                        COUNT(DISTINCT user_id) as unique_users
                    FROM events
                    WHERE site_id = %s 
                    AND DATE(timestamp) = %s
                """
                cursor.execute(query, (site_id, date))
            else:
                query = """
                    SELECT 
                        COUNT(*) as total_views,
                        COUNT(DISTINCT user_id) as unique_users
                    FROM events
                    WHERE site_id = %s
                """
                cursor.execute(query, (site_id,))

            result = cursor.fetchone()

            # Get top paths
            if date:
                path_query = """
                    SELECT path, COUNT(*) as views
                    FROM events
                    WHERE site_id = %s 
                    AND DATE(timestamp) = %s
                    AND path IS NOT NULL
                    GROUP BY path
                    ORDER BY views DESC
                    LIMIT 10
                """
                cursor.execute(path_query, (site_id, date))
            else:
                path_query = """
                    SELECT path, COUNT(*) as views
                    FROM events
                    WHERE site_id = %s
                    AND path IS NOT NULL
                    GROUP BY path
                    ORDER BY views DESC
                    LIMIT 10
                """
                cursor.execute(path_query, (site_id,))

            top_paths = cursor.fetchall()
            cursor.close()

            return {
                'total_views': result['total_views'] if result else 0,
                'unique_users': result['unique_users'] if result else 0,
                'top_paths': [dict(row) for row in top_paths]
            }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            raise
        finally:
            self.close()

db = Database()
