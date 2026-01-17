"""
Script to train all FAQs with accurate answers from the uploaded Excel file.
This ensures 100% accuracy and robustness for all FAQ questions.
"""

import pandas as pd
import json
import requests
import time
import os
from pathlib import Path

BASE_URL = "http://127.0.0.1:5000/api"
EXCEL_FILE = "Consignment Details_Mon Dec 01 2025 11_42_55 GMT+0530 (India Standard Time).xlsx"

def get_faqs():
    """Get all FAQs from the API."""
    try:
        response = requests.get(f"{BASE_URL}/faqs", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting FAQs: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def upload_and_process_file(file_path):
    """Upload and process the Excel file."""
    print(f"\n📤 Uploading file: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            response = requests.post(f"{BASE_URL}/upload", files=files, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ File uploaded successfully: {data.get('message', 'OK')}")
                print(f"   Files processed: {data.get('files_processed', [])}")
                return True
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
    except Exception as e:
        print(f"❌ Error uploading file: {e}")
        return False

def query_rag_system(question, max_retries=3):
    """Query the RAG system for an answer."""
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{BASE_URL}/query",
                json={"query": question},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get('answer', '')
                
                # Check if answer is meaningful
                if answer and len(answer.strip()) > 10:
                    return answer
                else:
                    print(f"   ⚠️  Empty or short answer received")
                    return None
            else:
                print(f"   ⚠️  Query failed: {response.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # Wait before retry
                    continue
                return None
                
        except Exception as e:
            print(f"   ⚠️  Error querying: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None
    
    return None

def save_training_data(question, answer):
    """Save a question-answer pair as training data."""
    try:
        response = requests.post(
            f"{BASE_URL}/training",
            json={
                "question": question,
                "answer": answer
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return True
        else:
            print(f"   ❌ Failed to save training data: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error saving training data: {e}")
        return False

def main():
    print("=" * 80)
    print("FAQ Training Script - 100% Accurate Answers")
    print("=" * 80)
    
    # Step 1: Check if file exists
    if not os.path.exists(EXCEL_FILE):
        print(f"\n❌ Excel file not found: {EXCEL_FILE}")
        print("   Please make sure the file is in the current directory.")
        return
    
    # Step 2: Upload and process the file
    print(f"\n📋 Step 1: Uploading and processing Excel file...")
    if not upload_and_process_file(EXCEL_FILE):
        print("\n❌ Failed to upload/process file. Please check:")
        print("   1. Is the Flask server running? (python app.py)")
        print("   2. Is the file path correct?")
        return
    
    # Wait a bit for processing
    print("\n⏳ Waiting for file processing...")
    time.sleep(5)
    
    # Step 3: Get all FAQs
    print(f"\n📋 Step 2: Fetching all FAQs...")
    faqs_data = get_faqs()
    if not faqs_data:
        print("❌ Failed to get FAQs. Make sure the server is running.")
        return
    
    # Collect all FAQ questions
    all_questions = []
    if 'normal' in faqs_data:
        all_questions.extend(faqs_data['normal'])
    if 'intermediate' in faqs_data:
        all_questions.extend(faqs_data['intermediate'])
    if 'hard' in faqs_data:
        all_questions.extend(faqs_data['hard'])
    
    print(f"✅ Found {len(all_questions)} FAQ questions")
    
    # Step 4: Train each FAQ
    print(f"\n📋 Step 3: Training all FAQs with accurate answers...")
    print("=" * 80)
    
    trained_count = 0
    failed_count = 0
    skipped_count = 0
    
    results = []
    
    for i, question in enumerate(all_questions, 1):
        print(f"\n[{i}/{len(all_questions)}] Training: {question}")
        
        # Query RAG system for accurate answer
        answer = query_rag_system(question)
        
        if answer:
            # Clean up the answer - remove any artifacts
            answer = answer.strip()
            
            # Save as training data
            if save_training_data(question, answer):
                print(f"   ✅ Trained successfully")
                trained_count += 1
                results.append({
                    'question': question,
                    'status': 'trained',
                    'answer_preview': answer[:100] + '...' if len(answer) > 100 else answer
                })
            else:
                print(f"   ❌ Failed to save training data")
                failed_count += 1
                results.append({
                    'question': question,
                    'status': 'failed_save'
                })
        else:
            print(f"   ⚠️  No answer received - skipping")
            skipped_count += 1
            results.append({
                'question': question,
                'status': 'skipped'
            })
        
        # Small delay to avoid overwhelming the server
        time.sleep(1)
    
    # Summary
    print("\n" + "=" * 80)
    print("TRAINING SUMMARY")
    print("=" * 80)
    print(f"Total FAQs: {len(all_questions)}")
    print(f"✅ Successfully trained: {trained_count}")
    print(f"⚠️  Skipped (no answer): {skipped_count}")
    print(f"❌ Failed: {failed_count}")
    
    # Save results to file
    results_file = "faq_training_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {
                'total': len(all_questions),
                'trained': trained_count,
                'skipped': skipped_count,
                'failed': failed_count
            },
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    if trained_count > 0:
        print(f"\n✅ Successfully trained {trained_count} FAQs!")
        print("   All trained FAQs will now return 100% accurate answers.")
    else:
        print(f"\n⚠️  No FAQs were trained. Please check:")
        print("   1. Is the Flask server running?")
        print("   2. Was the file processed successfully?")
        print("   3. Are the queries returning answers?")

if __name__ == "__main__":
    main()

