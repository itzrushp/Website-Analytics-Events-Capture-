from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import BaseModel, ValidationError, field_validator
from datetime import datetime
from api.queue_handler import queue_handler
from api.models import db
from api.config import config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Pydantic model for event validation
class EventModel(BaseModel):
    site_id: str
    event_type: str
    path: str | None = None
    user_id: str | None = None
    timestamp: str

    @field_validator('site_id', 'event_type')
    @classmethod
    def validate_required_fields(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except Exception:
            raise ValueError('Invalid timestamp format. Use ISO 8601 format.')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        queue_length = queue_handler.get_queue_length()
        return jsonify({
            'status': 'healthy',
            'queue_length': queue_length
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/event', methods=['POST'])
def ingest_event():
    """
    Fast ingestion endpoint
    Validates and queues events without waiting for database write
    """
    try:
        # Get JSON data
        event_data = request.get_json()

        if not event_data:
            return jsonify({
                'success': False,
                'error': 'Invalid JSON body'
            }), 400

        # Validate using Pydantic
        try:
            validated_event = EventModel(**event_data)
        except ValidationError as e:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'details': e.errors()
            }), 400

        # Enqueue the event (async processing)
        queue_handler.enqueue(validated_event.model_dump())

        # Immediate success response
        return jsonify({
            'success': True,
            'message': 'Event received and queued for processing'
        }), 202

    except Exception as e:
        logger.error(f"Error in ingest_event: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """
    Reporting endpoint
    Returns aggregated statistics for a site
    """
    try:
        # Get query parameters
        site_id = request.args.get('site_id')
        date = request.args.get('date')  # Optional: YYYY-MM-DD format

        if not site_id:
            return jsonify({
                'success': False,
                'error': 'site_id is required'
            }), 400

        # Validate date format if provided
        if date:
            try:
                datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                }), 400

        # Get statistics from database
        stats = db.get_stats(site_id, date)

        # Build response
        response = {
            'site_id': site_id,
            'total_views': stats['total_views'],
            'unique_users': stats['unique_users'],
            'top_paths': stats['top_paths']
        }

        if date:
            response['date'] = date

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error in get_stats: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        'service': 'Analytics Ingestion Service',
        'version': '1.0.0',
        'endpoints': {
            'POST /event': 'Ingest analytics events',
            'GET /stats': 'Retrieve aggregated statistics',
            'GET /health': 'Health check'
        }
    }), 200

if __name__ == '__main__':
    # Initialize database schema
    try:
        db.init_schema()
        logger.info("Database schema initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    # Connect to queue
    try:
        queue_handler.connect()
        logger.info("Queue handler connected")
    except Exception as e:
        logger.error(f"Failed to connect to queue: {e}")

    # Run Flask app
    app.run(
        host=config.API_HOST,
        port=config.API_PORT,
        debug=True
    )
