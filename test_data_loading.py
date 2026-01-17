"""
Diagnostic script to test data loading and retrieval.
Run this to verify that data is properly loaded and can be retrieved.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag_pipeline import RAGPipeline
from rag_ingestion import RAGIngestion
import pandas as pd

def test_data_loading():
    """Test if data can be loaded and retrieved."""
    print("=" * 60)
    print("Data Loading and Retrieval Diagnostic Test")
    print("=" * 60)
    
    # Initialize RAG pipeline
    print("\n1. Initializing RAG pipeline...")
    try:
        rag_pipeline = RAGPipeline(
            embedding_model="all-MiniLM-L6-v2",
            db_path="./chroma_db",
            collection_name="excel_data"
        )
        print("✅ RAG pipeline initialized")
    except Exception as e:
        print(f"❌ Error initializing RAG pipeline: {e}")
        return False
    
    # Check database stats
    print("\n2. Checking database stats...")
    try:
        stats = rag_pipeline.get_stats()
        total_chunks = stats.get('total_chunks', 0)
        print(f"   Total chunks in database: {total_chunks}")
        
        if total_chunks == 0:
            print("   ⚠️  Database is empty!")
            print("   Please process at least one file first.")
            return False
        else:
            print("   ✅ Database has data")
    except Exception as e:
        print(f"   ❌ Error checking stats: {e}")
        return False
    
    # Test retrieval with a simple query
    print("\n3. Testing retrieval with query: 'column names'...")
    try:
        test_query = "column names"
        result = rag_pipeline.query(test_query, n_results=5)
        
        retrieved_chunks = result.get('retrieved_chunks', [])
        answer = result.get('answer', '')
        has_context = result.get('has_context', False)
        
        print(f"   Chunks retrieved: {len(retrieved_chunks)}")
        print(f"   Has context: {has_context}")
        
        if retrieved_chunks:
            print("   ✅ Retrieval is working")
            print(f"   First chunk preview: {retrieved_chunks[0].get('content', '')[:150]}...")
        else:
            print("   ⚠️  No chunks retrieved despite database having data")
            print("   This may indicate an embedding mismatch issue")
        
        if answer and "not available" not in answer.lower():
            print(f"   ✅ Answer generated: {answer[:200]}...")
        else:
            print(f"   ⚠️  Answer indicates no data: {answer[:200]}...")
            
    except Exception as e:
        print(f"   ❌ Error testing retrieval: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test with another query
    print("\n4. Testing retrieval with query: 'What are all the column names in this file?'...")
    try:
        test_query = "What are all the column names in this file?"
        result = rag_pipeline.query(test_query, n_results=10)
        
        retrieved_chunks = result.get('retrieved_chunks', [])
        answer = result.get('answer', '')
        
        print(f"   Chunks retrieved: {len(retrieved_chunks)}")
        
        if retrieved_chunks:
            print(f"   First chunk content preview (first 500 chars):")
            print(f"   {retrieved_chunks[0].get('content', '')[:500]}...")
        
        if answer and "not available" not in answer.lower():
            print(f"   ✅ Answer:")
            print(f"   {answer}")
        else:
            print(f"   ⚠️  Answer: {answer[:300]}...")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check sample chunks directly
    print("\n5. Checking sample chunks from database...")
    try:
        all_data = rag_pipeline.retrieval.collection.get()
        if all_data['ids']:
            print(f"   Found {len(all_data['ids'])} chunks in database")
            print(f"   Sample chunk 1 (first 200 chars):")
            print(f"   {all_data['documents'][0][:200]}...")
            print(f"   Sample chunk 1 metadata:")
            print(f"   {all_data['metadatas'][0] if all_data['metadatas'] else 'No metadata'}")
        else:
            print("   ⚠️  No chunks found in database")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Diagnostic test complete!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    test_data_loading()
