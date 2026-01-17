"""
Diagnostic script to test file processing and database status.
Run this to check if files are being processed correctly.
"""

import requests
import json
import sys

API_URL = "http://localhost:5000/api"

def check_health():
    """Check if API is running."""
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            print("✅ API is running")
            return True
        else:
            print(f"❌ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print(f"   Make sure the Flask server is running on {API_URL}")
        return False

def check_database_stats():
    """Check database statistics."""
    try:
        response = requests.get(f"{API_URL}/database-stats")
        if response.status_code == 200:
            data = response.json()
            stats = data.get('stats', {})
            total_chunks = stats.get('total_chunks', 0)
            print(f"\n📊 Database Statistics:")
            print(f"   Total chunks: {total_chunks}")
            print(f"   Loaded files: {data.get('loaded_files_count', 0)}")
            if total_chunks == 0:
                print("   ⚠️  Database is empty! Files need to be processed.")
            elif total_chunks < 10:
                print(f"   ⚠️  Database has very few chunks ({total_chunks}). File may not be fully processed.")
            return total_chunks > 0, total_chunks
        else:
            print(f"❌ Failed to get database stats: {response.status_code}")
            return False, 0
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False, 0

def list_files(folder_path=None):
    """List available files."""
    try:
        if folder_path:
            response = requests.post(f"{API_URL}/files/list", json={'folder_path': folder_path})
        else:
            # Use default path from settings
            response = requests.get(f"{API_URL}/settings")
            settings = response.json()
            folder_path = settings.get('files_folder_path', '')
            response = requests.post(f"{API_URL}/files/list", json={'folder_path': folder_path})
        
        if response.status_code == 200:
            data = response.json()
            files = data.get('files', [])
            print(f"\n📁 Files in folder ({data.get('folder_path', 'N/A')}):")
            if files:
                for i, file_info in enumerate(files, 1):
                    filename = file_info.get('filename', 'Unknown')
                    print(f"   {i}. {filename}")
                return [f.get('path') for f in files]
            else:
                print("   No files found")
                return []
        else:
            print(f"❌ Failed to list files: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error listing files: {e}")
        return []

def process_file(file_path):
    """Process a single file."""
    try:
        print(f"\n⚙️  Processing file: {file_path}")
        response = requests.post(
            f"{API_URL}/files/process",
            json={
                'file_paths': [file_path],
                'process_all_sheets': True
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            total_processed = data.get('total_processed', 0)
            
            print(f"   Processed: {total_processed} file(s)")
            for result in results:
                status = result.get('status', 'unknown')
                message = result.get('message', '')
                if status == 'success':
                    print(f"   ✅ {result.get('file')}: {message}")
                else:
                    print(f"   ❌ {result.get('file')}: {message}")
                    if 'traceback' in result:
                        print(f"      Error details: {result['traceback'][:200]}...")
            
            return total_processed > 0
        else:
            print(f"   ❌ Processing failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ Error processing file: {e}")
        return False

def test_query(query_text):
    """Test a query."""
    try:
        print(f"\n🔍 Testing query: '{query_text}'")
        response = requests.post(
            f"{API_URL}/query",
            json={'query': query_text}
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get('answer', 'No answer')
            print(f"   ✅ Answer: {answer[:300]}...")
            return True
        else:
            print(f"   ❌ Query failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error message: {error_data.get('error', 'Unknown error')}")
                if 'answer' in error_data:
                    print(f"   Answer: {error_data.get('answer', '')[:200]}")
            except:
                print(f"   Response text: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ Error querying: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main diagnostic flow."""
    print("=" * 60)
    print("RAG System Diagnostic Tool")
    print("=" * 60)
    
    # Step 1: Check API health
    if not check_health():
        sys.exit(1)
    
    # Step 2: Check database stats
    has_data, total_chunks = check_database_stats()
    
    # Step 3: List files
    file_paths = list_files()
    
    if not file_paths:
        print("\n⚠️  No files found. Please check the folder path in settings.")
        sys.exit(1)
    
    # Step 4: Process first file if database is empty or has too few chunks
    if not has_data or total_chunks < 10:
        if total_chunks < 10 and total_chunks > 0:
            print(f"\n⚠️  Database has only {total_chunks} chunks (expected many more).")
            print("   This suggests incomplete processing. Re-processing file...")
        else:
            print("\n📝 Database is empty. Processing first file...")
        
        if process_file(file_paths[0]):
            # Re-check stats
            print("\n📊 Re-checking database after processing...")
            check_database_stats()
        else:
            print("\n❌ File processing failed. Check server logs for details.")
            sys.exit(1)
    
    # Step 5: Test query
    test_query("What are all the column names in this file?")
    
    print("\n" + "=" * 60)
    print("Diagnostic complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
