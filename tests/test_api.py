import pytest
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:5000"

def test_health_check():
    """Test health check endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'

def test_ingest_event_success():
    """Test successful event ingestion"""
    event = {
        "site_id": "site-test-123",
        "event_type": "page_view",
        "path": "/test-page",
        "user_id": "user-test-456",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    response = requests.post(f"{BASE_URL}/event", json=event)
    assert response.status_code == 202
    data = response.json()
    assert data['success'] == True

def test_ingest_event_missing_required():
    """Test event ingestion with missing required fields"""
    event = {
        "path": "/test-page",
        "user_id": "user-test-456"
    }

    response = requests.post(f"{BASE_URL}/event", json=event)
    assert response.status_code == 400
    data = response.json()
    assert data['success'] == False

def test_ingest_event_invalid_timestamp():
    """Test event ingestion with invalid timestamp"""
    event = {
        "site_id": "site-test-123",
        "event_type": "page_view",
        "timestamp": "invalid-timestamp"
    }

    response = requests.post(f"{BASE_URL}/event", json=event)
    assert response.status_code == 400
    data = response.json()
    assert data['success'] == False

def test_get_stats():
    """Test statistics retrieval"""
    # First, ingest some events
    for i in range(5):
        event = {
            "site_id": "site-stats-test",
            "event_type": "page_view",
            "path": f"/page-{i % 2}",
            "user_id": f"user-{i % 3}",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        requests.post(f"{BASE_URL}/event", json=event)

    # Wait for processing
    time.sleep(3)

    # Get stats
    response = requests.get(f"{BASE_URL}/stats?site_id=site-stats-test")
    assert response.status_code == 200
    data = response.json()
    assert 'total_views' in data
    assert 'unique_users' in data
    assert 'top_paths' in data

def test_get_stats_missing_site_id():
    """Test stats endpoint without site_id"""
    response = requests.get(f"{BASE_URL}/stats")
    assert response.status_code == 400
    data = response.json()
    assert data['success'] == False

def test_get_stats_with_date():
    """Test stats retrieval with date filter"""
    today = datetime.utcnow().strftime('%Y-%m-%d')

    response = requests.get(f"{BASE_URL}/stats?site_id=site-test-123&date={today}")
    assert response.status_code == 200
    data = response.json()
    assert 'date' in data
    assert data['date'] == today

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
