# Website Analytics Service

A high-performance backend service for capturing and analyzing website analytics events with fast ingestion and real-time reporting capabilities.

## 🏗️ Architecture Overview

This system consists of three main components:

### 1. **Ingestion API** (Service 1)
- **Purpose**: Ultra-fast event ingestion
- **Technology**: Flask REST API
- **Strategy**: Accepts events and immediately queues them without blocking for database writes
- **Endpoint**: `POST /event`
- **Response Time**: < 5ms (returns before database write)

### 2. **Background Processor** (Service 2)
- **Purpose**: Asynchronous event processing
- **Technology**: Python worker process
- **Strategy**: Continuously polls Redis queue and writes events to PostgreSQL
- **Scalability**: Can run multiple worker instances for higher throughput

### 3. **Reporting API** (Service 3)
- **Purpose**: Aggregated analytics reporting
- **Technology**: Flask REST API with PostgreSQL queries
- **Endpoint**: `GET /stats`
- **Features**: Returns aggregated views, unique users, and top paths

### Architecture Decision: Why Redis?

**Redis was chosen as the message queue for the following reasons:**

1. **In-Memory Performance**: Redis operates entirely in memory, providing sub-millisecond latency for enqueue/dequeue operations
2. **Simplicity**: Built-in list data structures (LPUSH/BRPOP) provide FIFO queue behavior without additional complexity
3. **Reliability**: Supports persistence options (AOF/RDB) to prevent data loss
4. **Horizontal Scalability**: Can scale to millions of operations per second
5. **Producer-Consumer Pattern**: BRPOP provides blocking dequeue, making the worker efficient and responsive

**Alternative Considered**: RabbitMQ was considered but Redis was preferred for its simplicity and lower operational overhead for this use case.

## 📊 Database Schema

### Events Table

```sql
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    site_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    path VARCHAR(500),
    user_id VARCHAR(255),
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for optimized queries
CREATE INDEX idx_site_id ON events(site_id);
CREATE INDEX idx_timestamp ON events(timestamp);
CREATE INDEX idx_user_id ON events(user_id);
CREATE INDEX idx_site_timestamp ON events(site_id, timestamp);
```

**Schema Design Decisions:**

- **site_id**: Indexed for fast filtering by website
- **timestamp**: Indexed for date-range queries
- **user_id**: Indexed for unique user counting
- **Composite Index** (site_id, timestamp): Optimizes the most common query pattern
- **path**: Stored as VARCHAR(500) to accommodate long URLs

## 🚀 Quick Start

### Prerequisites

- **Docker** and **Docker Compose** installed
- **Git** installed
- Ports **5000**, **5432**, and **6379** available

### Option 1: Docker Setup (Recommended)

1. **Clone the repository**
```bash
git clone <repository-url>
cd analytics-service
```

2. **Create environment file**
```bash
cp .env.example .env
# Edit .env if you want to customize configuration
```

3. **Build and start all services**
```bash
docker-compose up --build
```

This will start:
- PostgreSQL database on port 5432
- Redis queue on port 6379
- API service on port 5000
- Background processor worker

4. **Verify the services are running**
```bash
curl http://localhost:5000/health
```

Expected response:
```json
{
  "status": "healthy",
  "queue_length": 0
}
```

### Option 2: Local Setup (Without Docker)

#### Step 1: Install Dependencies

1. **Install PostgreSQL**
```bash
# macOS
brew install postgresql
brew services start postgresql

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

2. **Install Redis**
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis
```

3. **Install Python dependencies**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Step 2: Configure Database

```bash
# Create database and user
psql postgres
CREATE DATABASE analytics_db;
CREATE USER analytics_user WITH PASSWORD 'analytics_password';
GRANT ALL PRIVILEGES ON DATABASE analytics_db TO analytics_user;
\q
```

#### Step 3: Configure Environment

```bash
cp .env.example .env
# Edit .env to match your local configuration
```

#### Step 4: Initialize Database Schema

```bash
python -c "from api.models import db; db.init_schema()"
```

#### Step 5: Start Services

Open **three terminal windows**:

**Terminal 1: Start API**
```bash
source venv/bin/activate
python -m api.app
```

**Terminal 2: Start Processor**
```bash
source venv/bin/activate
python -m processor.worker
```

**Terminal 3: Verify**
```bash
curl http://localhost:5000/health
```

## 📝 API Usage

### 1. Ingest Event

**Endpoint**: `POST /event`

**Request**:
```bash
curl -X POST http://localhost:5000/event \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": "site-abc-123",
    "event_type": "page_view",
    "path": "/pricing",
    "user_id": "user-xyz-789",
    "timestamp": "2025-11-15T14:30:01Z"
  }'
```

**Response** (202 Accepted):
```json
{
  "success": true,
  "message": "Event received and queued for processing"
}
```

**Validation Rules**:
- `site_id`: Required, non-empty string
- `event_type`: Required, non-empty string
- `timestamp`: Required, valid ISO 8601 format
- `path`: Optional string
- `user_id`: Optional string

### 2. Get Statistics

**Endpoint**: `GET /stats`

**Request (All-time stats)**:
```bash
curl "http://localhost:5000/stats?site_id=site-abc-123"
```

**Request (Specific date)**:
```bash
curl "http://localhost:5000/stats?site_id=site-abc-123&date=2025-11-15"
```

**Response** (200 OK):
```json
{
  "site_id": "site-abc-123",
  "date": "2025-11-15",
  "total_views": 1450,
  "unique_users": 212,
  "top_paths": [
    { "path": "/pricing", "views": 700 },
    { "path": "/blog/post-1", "views": 500 },
    { "path": "/", "views": 250 }
  ]
}
```

### 3. Health Check

**Endpoint**: `GET /health`

**Request**:
```bash
curl http://localhost:5000/health
```

**Response**:
```json
{
  "status": "healthy",
  "queue_length": 0
}
```

## 🧪 Testing

### Run Test Suite

```bash
# Install test dependencies
pip install pytest requests

# Make sure the services are running
docker-compose up -d

# Run tests
python -m pytest tests/test_api.py -v
```

### Manual Testing Script

```bash
# Send 100 test events
for i in {1..100}; do
  curl -X POST http://localhost:5000/event \
    -H "Content-Type: application/json" \
    -d "{
      \"site_id\": \"site-test-123\",
      \"event_type\": \"page_view\",
      \"path\": \"/page-$((i % 5))\",
      \"user_id\": \"user-$((i % 20))\",
      \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
    }" &
done

# Wait for processing (5 seconds)
sleep 5

# Get statistics
curl "http://localhost:5000/stats?site_id=site-test-123"
```

## 📁 Project Structure

```
analytics-service/
├── api/
│   ├── __init__.py
│   ├── app.py              # Flask API application
│   ├── models.py           # Database models and operations
│   ├── queue_handler.py    # Redis queue management
│   └── config.py           # Configuration management
├── processor/
│   ├── __init__.py
│   └── worker.py           # Background event processor
├── tests/
│   ├── __init__.py
│   └── test_api.py         # API test suite
├── docker-compose.yml      # Multi-container orchestration
├── Dockerfile              # Container image definition
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_HOST` | PostgreSQL host | localhost |
| `POSTGRES_PORT` | PostgreSQL port | 5432 |
| `POSTGRES_USER` | Database user | analytics_user |
| `POSTGRES_PASSWORD` | Database password | analytics_password |
| `POSTGRES_DB` | Database name | analytics_db |
| `REDIS_HOST` | Redis host | localhost |
| `REDIS_PORT` | Redis port | 6379 |
| `REDIS_DB` | Redis database number | 0 |
| `API_HOST` | API bind address | 0.0.0.0 |
| `API_PORT` | API port | 5000 |

## 📈 Performance Considerations

### Ingestion Endpoint Optimization

1. **No Database Blocking**: Events are queued immediately, returning success in < 5ms
2. **Input Validation**: Fast Pydantic validation before queuing
3. **Connection Pooling**: Redis connection reuse across requests

### Processor Optimization

1. **Batch Processing**: Can be extended to batch database inserts
2. **Horizontal Scaling**: Run multiple processor instances
3. **Error Handling**: Failed events can be moved to dead letter queue

### Database Optimization

1. **Composite Indexes**: Optimized for common query patterns
2. **Connection Pooling**: Reuses database connections
3. **Aggregation Queries**: Pre-aggregated stats for faster reporting

## 🐛 Troubleshooting

### API won't start

```bash
# Check if ports are available
lsof -i :5000
lsof -i :5432
lsof -i :6379

# Check Docker container logs
docker-compose logs api
```

### Events not being processed

```bash
# Check processor logs
docker-compose logs processor

# Check queue length
curl http://localhost:5000/health

# Restart processor
docker-compose restart processor
```

### Database connection errors

```bash
# Verify PostgreSQL is running
docker-compose ps

# Test database connection
docker-compose exec postgres psql -U analytics_user -d analytics_db -c "SELECT 1;"
```

## 🚢 Pushing to GitHub

```bash
# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Analytics service with fast ingestion"

# Add remote repository
git remote add origin https://github.com/yourusername/analytics-service.git

# Push to GitHub
git push -u origin main
```

## 🎯 Future Enhancements

1. **Batch Processing**: Process multiple events in single database transaction
2. **Data Partitioning**: Partition events table by date for better performance
3. **Caching Layer**: Add Redis caching for frequently accessed stats
4. **Real-time Dashboards**: WebSocket support for live analytics
5. **Data Retention**: Implement automated data archival/cleanup
6. **Monitoring**: Add Prometheus metrics and Grafana dashboards
7. **Authentication**: Add API key authentication
8. **Rate Limiting**: Implement request rate limiting


## 👤 Author
Built for technical assessment by Roshan Pandit
#   W e b s i t e - A n a l y t i c s - E v e n t s - C a p t u r e -  
 