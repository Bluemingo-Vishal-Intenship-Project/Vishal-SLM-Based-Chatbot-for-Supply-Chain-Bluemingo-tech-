"""
Quick test script for the chatbot API
Run this to verify all endpoints are working
"""

import requests
import json

BASE_URL = "http://localhost:5000/api"

def test_endpoint(name, method, endpoint, data=None):
    """Test an API endpoint"""
    try:
        url = f"{BASE_URL}{endpoint}"
        print(f"\n{'='*50}")
        print(f"Testing: {name}")
        print(f"URL: {url}")
        print(f"Method: {method}")
        
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=5)
        else:
            print(f"❌ Unknown method: {method}")
            return False
        
        print(f"Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            try:
                result = response.json()
                print(f"✅ Success!")
                print(f"Response: {json.dumps(result, indent=2)[:200]}...")
                return True
            except:
                print(f"✅ Success! (No JSON response)")
                return True
        else:
            print(f"❌ Failed!")
            print(f"Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error - Is the server running?")
        print(f"   Start server with: python app.py")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    print("\n" + "="*50)
    print("Chatbot API Test Suite")
    print("="*50)
    
    results = []
    
    # Test health endpoint
    results.append(("Health Check", test_endpoint("Health Check", "GET", "/health")))
    
    # Test greet endpoint
    results.append(("Greet", test_endpoint("Greet", "GET", "/greet")))
    
    # Test autocomplete
    results.append(("Autocomplete", test_endpoint("Autocomplete", "POST", "/autocomplete", {"query": "what is"})))
    
    # Test FAQs
    results.append(("FAQs", test_endpoint("FAQs", "GET", "/faqs")))
    
    # Test settings
    results.append(("Get Settings", test_endpoint("Get Settings", "GET", "/settings")))
    
    # Test query (might fail if no data loaded)
    results.append(("Query", test_endpoint("Query", "POST", "/query", {"query": "What are the column names?"})))
    
    # Summary
    print("\n" + "="*50)
    print("Test Summary")
    print("="*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your chatbot API is ready!")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        print("   Make sure:")
        print("   1. Server is running: python app.py")
        print("   2. All dependencies are installed: pip install -r requirements.txt")
        print("   3. Files are processed (for query tests)")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")







