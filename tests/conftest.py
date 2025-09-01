import pytest
import os
import sqlite3
from unittest.mock import Mock
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
import db_util

@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.app.config['TESTING'] = True
    app.app.config['DATABASE'] = ':memory:'
    
    with app.app.test_client() as client:
        with app.app.app_context():
            # Initialize test database
            db_util.setup_database()
            yield client

@pytest.fixture
def mock_cf_api():
    """Mock Cloudflare API client."""
    mock_api = Mock()
    mock_api._make_request.return_value = {
        'success': True,
        'result': []
    }
    return mock_api

@pytest.fixture
def sample_zone():
    """Sample zone data for testing."""
    return {
        'id': 'test-zone-id-123',
        'name': 'example.com',
        'status': 'active',
        'plan_name': 'Free Website',
        'account_id': 'test-account-id',
        'created_on': '2023-01-01T00:00:00Z',
        'modified_on': '2023-01-01T00:00:00Z'
    }

@pytest.fixture
def sample_dns_records():
    """Sample DNS records for testing."""
    return [
        {'type': 'A', 'name': 'example.com', 'content': '192.168.1.1'},
        {'type': 'MX', 'name': 'example.com', 'content': 'mail.example.com'},
        {'type': 'TXT', 'name': 'example.com', 'content': 'v=spf1 include:_spf.google.com ~all'},
        {'type': 'CNAME', 'name': 'www.example.com', 'content': 'example.com'}
    ]