import os
import sys
import time
import requests
import argparse
from typing import List, Dict, Any

# Default Cloud Run URLs (can be overridden via arguments)
DEFAULT_BACKEND_URL = "https://data-agent-search-backend-579392983172.europe-west1.run.app"
DEFAULT_AGENT_URL = "https://data-agent-service-579392983172.europe-west1.run.app"

# Exemplary user queries to test
TEST_QUERIES = [
    "Find me a cheap apartment in Zurich",
    "Show me luxury houses in Geneva with at least 3 bedrooms",
    "Are there any properties with a lake view under 2k?",
    "I need a modern studio in Bern"
]

# Database backends to test
BACKENDS = ["alloydb", "cloudsql_pg", "spanner"]

def print_header(title: str):
    print(f"\n{'=' * 80}")
    print(f" {title}")
    print(f"{'=' * 80}")

def test_search_endpoint(base_url: str, query: str, backend: str) -> bool:
    """Tests the /api/search endpoint."""
    url = f"{base_url}/api/search"
    payload = {
        "query": query,
        "backend": backend
    }
    
    print(f"Testing /api/search | Backend: {backend:<12} | Query: '{query}'")
    
    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=30)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            num_results = len(data.get("listings", []))
            print(f"  ✅ SUCCESS ({elapsed:.2f}s) - Found {num_results} listings")
            return True
        else:
            print(f"  ❌ FAILED ({elapsed:.2f}s) - Status: {response.status_code}")
            print(f"     Response: {response.text[:200]}")
            return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ❌ ERROR ({elapsed:.2f}s) - {str(e)}")
        return False

def test_chat_endpoint(base_url: str, message: str, backend: str) -> bool:
    """Tests the /chat endpoint (Agent Service)."""
    url = f"{base_url}/chat"
    payload = {
        "message": message,
        "session_id": f"test_session_{int(time.time())}",
        "backend": backend
    }
    
    print(f"Testing /chat       | Backend: {backend:<12} | Message: '{message}'")
    
    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=60)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            response_text = data.get("response", "")
            print(f"  ✅ SUCCESS ({elapsed:.2f}s) - Agent replied: '{response_text[:60]}...'")
            return True
        else:
            print(f"  ❌ FAILED ({elapsed:.2f}s) - Status: {response.status_code}")
            print(f"     Response: {response.text[:200]}")
            return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ❌ ERROR ({elapsed:.2f}s) - {str(e)}")
        return False

def test_history_endpoint(base_url: str, backend: str) -> bool:
    """Tests the /api/history endpoint."""
    url = f"{base_url}/api/history"
    payload = {
        "backend": backend,
        "filters": []
    }
    
    print(f"Testing /api/history| Backend: {backend:<12}")
    
    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=10)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            num_rows = len(data.get("rows", []))
            print(f"  ✅ SUCCESS ({elapsed:.2f}s) - Retrieved {num_rows} history records")
            return True
        else:
            print(f"  ❌ FAILED ({elapsed:.2f}s) - Status: {response.status_code}")
            print(f"     Response: {response.text[:200]}")
            return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ❌ ERROR ({elapsed:.2f}s) - {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test Cloud Run endpoints for Property Search Data Agents")
    parser.add_argument("--backend-url", type=str, default=DEFAULT_BACKEND_URL, help="Base URL for the backend service")
    parser.add_argument("--agent-url", type=str, default=DEFAULT_AGENT_URL, help="Base URL for the agent service")
    args = parser.parse_args()

    print_header("Starting Endpoint Tests")
    print(f"Backend URL: {args.backend_url}")
    print(f"Agent URL:   {args.agent_url}")
    
    total_tests = 0
    passed_tests = 0

    # 1. Test /api/search endpoint
    print_header("Testing /api/search Endpoint")
    for backend in BACKENDS:
        for query in TEST_QUERIES:
            total_tests += 1
            if test_search_endpoint(args.backend_url, query, backend):
                passed_tests += 1

    # 2. Test /chat endpoint
    print_header("Testing /chat Endpoint (Agent Service)")
    for backend in BACKENDS:
        for query in TEST_QUERIES[:2]: # Test only first 2 queries to save time
            total_tests += 1
            if test_chat_endpoint(args.agent_url, query, backend):
                passed_tests += 1

    # 3. Test /api/history endpoint
    print_header("Testing /api/history Endpoint")
    for backend in BACKENDS:
        total_tests += 1
        if test_history_endpoint(args.backend_url, backend):
            passed_tests += 1

    # Summary
    print_header("Test Summary")
    print(f"Total Tests:  {total_tests}")
    print(f"Passed Tests: {passed_tests}")
    print(f"Failed Tests: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed successfully!")
        sys.exit(0)
    else:
        print("\n⚠️ Some tests failed. Check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
