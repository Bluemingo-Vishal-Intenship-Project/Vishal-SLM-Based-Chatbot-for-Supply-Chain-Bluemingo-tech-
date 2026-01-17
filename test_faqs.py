"""
Test script to check all FAQ questions and their answers
Run this to identify formatting issues and faulty answers
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000/api"

# Get all FAQs
def get_faqs():
    try:
        response = requests.get(f"{BASE_URL}/faqs")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting FAQs: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

# Test a query
def test_query(question):
    try:
        response = requests.post(
            f"{BASE_URL}/query",
            json={"query": question},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Status {response.status_code}", "text": response.text}
    except Exception as e:
        return {"error": str(e)}

# Main testing function
def main():
    print("=" * 80)
    print("FAQ Answer Testing Script")
    print("=" * 80)
    print()
    
    # Get FAQs
    print("Fetching FAQs...")
    faqs_data = get_faqs()
    if not faqs_data:
        print("Failed to get FAQs. Make sure the server is running.")
        return
    
    # Collect all FAQ questions
    all_questions = []
    if 'normal' in faqs_data:
        all_questions.extend(faqs_data['normal'])
    if 'intermediate' in faqs_data:
        all_questions.extend(faqs_data['intermediate'])
    if 'hard' in faqs_data:
        all_questions.extend(faqs_data['hard'])
    
    print(f"Found {len(all_questions)} FAQ questions to test")
    print()
    
    # Test each question
    results = []
    for i, question in enumerate(all_questions, 1):
        print(f"[{i}/{len(all_questions)}] Testing: {question}")
        
        result = test_query(question)
        
        # Analyze the answer
        answer = result.get('answer', '')
        has_error = 'error' in result
        is_empty = not answer or len(answer.strip()) < 10
        has_formatting_issues = False
        issues = []
        
        if answer:
            # Check for formatting issues
            if 'bro' in answer.lower() or 'how are you' in answer.lower():
                has_formatting_issues = True
                issues.append("Contains casual text (bro, how are you)")
            
            if re.search(r'\d+\.?\d*[a-zA-Z]', answer) or re.search(r'[a-zA-Z]\d+\.?\d*', answer):
                has_formatting_issues = True
                issues.append("Number-letter concatenation without space")
            
            if answer.count('\n') < 2 and len(answer) > 100:
                has_formatting_issues = True
                issues.append("Long answer without proper line breaks")
            
            if '**Answer:**' in answer and '**Details:**' not in answer:
                has_formatting_issues = True
                issues.append("Has Answer header but no Details section")
        
        results.append({
            'question': question,
            'answer': answer[:200] + '...' if len(answer) > 200 else answer,
            'full_answer': answer,
            'has_error': has_error,
            'is_empty': is_empty,
            'has_formatting_issues': has_formatting_issues,
            'issues': issues,
            'is_trained': result.get('is_trained', False),
            'is_edited': result.get('is_edited', False)
        })
        
        # Print result summary
        if has_error:
            print(f"  ❌ ERROR: {result.get('error', 'Unknown error')}")
        elif is_empty:
            print(f"  ⚠️  EMPTY or too short answer")
        elif has_formatting_issues:
            print(f"  ⚠️  FORMATTING ISSUES: {', '.join(issues)}")
        else:
            print(f"  ✅ OK")
        
        # Small delay to avoid overwhelming the server
        time.sleep(0.5)
        print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    total = len(results)
    errors = sum(1 for r in results if r['has_error'])
    empty = sum(1 for r in results if r['is_empty'])
    formatting_issues = sum(1 for r in results if r['has_formatting_issues'])
    ok = total - errors - empty - formatting_issues
    
    print(f"Total questions tested: {total}")
    print(f"✅ OK: {ok}")
    print(f"⚠️  Empty/Short: {empty}")
    print(f"⚠️  Formatting Issues: {formatting_issues}")
    print(f"❌ Errors: {errors}")
    print()
    
    # List questions with issues
    if formatting_issues > 0 or errors > 0 or empty > 0:
        print("QUESTIONS WITH ISSUES:")
        print("-" * 80)
        for r in results:
            if r['has_error'] or r['is_empty'] or r['has_formatting_issues']:
                print(f"\nQ: {r['question']}")
                if r['has_error']:
                    print(f"  Error: {r.get('error', 'Unknown')}")
                if r['is_empty']:
                    print(f"  Issue: Empty or too short answer")
                if r['has_formatting_issues']:
                    print(f"  Issues: {', '.join(r['issues'])}")
                print(f"  Answer preview: {r['answer'][:150]}...")
    
    # Save detailed results to file
    with open('faq_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nDetailed results saved to: faq_test_results.json")

if __name__ == "__main__":
    import re
    main()

