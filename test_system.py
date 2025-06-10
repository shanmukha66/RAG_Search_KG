#!/usr/bin/env python3
"""
Test script to verify the complete RAG Search system with monitoring
"""

import time
import json
import requests
from threading import Thread

def test_server_health():
    """Test if server is responsive"""
    try:
        response = requests.get('http://localhost:5001/health', timeout=5)
        print(f"✅ Health check: HTTP {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Services: {len(data.get('checks', {}))} health checks")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("❌ Server not running")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_monitoring_endpoints():
    """Test monitoring endpoints"""
    endpoints = [
        ('/system/status', 'System Status'),
        ('/system/metrics', 'System Metrics'),
        ('/system/errors', 'Error Statistics'),
    ]
    
    for endpoint, name in endpoints:
        try:
            response = requests.get(f'http://localhost:5001{endpoint}', timeout=5)
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} {name}: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {name} failed: {e}")

def test_search_functionality():
    """Test basic search functionality"""
    try:
        payload = {
            'query': 'test search query',
            'session_id': 'test-session-123'
        }
        response = requests.post(
            'http://localhost:5001/search',
            json=payload,
            timeout=10
        )
        status = "✅" if response.status_code == 200 else "❌"
        print(f"{status} Search functionality: HTTP {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Vector results: {len(data.get('vector_results', []))}")
            print(f"   Graph results: {len(data.get('graph_results', []))}")
            print(f"   AI response: {'Generated' if data.get('ai_response') else 'None'}")
    except Exception as e:
        print(f"❌ Search test failed: {e}")

def start_test_server():
    """Start the Flask server in a separate thread"""
    from app import app, initialize_services
    
    print("🚀 Initializing services...")
    success = initialize_services()
    if not success:
        print("❌ Service initialization failed!")
        return False
    
    print("✅ Services initialized successfully!")
    print("🌐 Starting Flask server on http://localhost:5001...")
    
    # Start server in a thread
    server_thread = Thread(target=lambda: app.run(host='0.0.0.0', port=5001, debug=False))
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for server to start
    time.sleep(3)
    return True

def main():
    print("🧪 RAG Search System Test Suite")
    print("=" * 50)
    
    # Check if server is already running
    if not test_server_health():
        print("\n🚀 Starting test server...")
        if not start_test_server():
            return
        
        # Wait for server to be ready
        print("⏳ Waiting for server to be ready...")
        for i in range(10):
            if test_server_health():
                break
            time.sleep(1)
        else:
            print("❌ Server failed to start properly")
            return
    
    print("\n🏥 Testing Monitoring Endpoints...")
    test_monitoring_endpoints()
    
    print("\n🔍 Testing Search Functionality...")
    test_search_functionality()
    
    print("\n✅ Test suite completed!")
    print("💡 You can now open http://localhost:5000 in your browser")

if __name__ == "__main__":
    main() 