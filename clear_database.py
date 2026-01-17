"""
Simple script to clear the vector database.
Run this script to remove all old data from ChromaDB.
"""

import requests
import json

def clear_database():
    """Clear the vector database via API."""
    url = "http://localhost:5000/api/clear-database"
    
    try:
        print("🔄 Clearing vector database...")
        response = requests.post(url)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"   {result.get('message', 'Database cleared')}")
            print("\n📝 Next steps:")
            print("   1. Upload your new file through the UI")
            print("   2. Process the file")
            print("   3. Query - answers will come from your new file only")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to the server.")
        print("   Make sure the Flask app is running (python app.py)")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    clear_database()
