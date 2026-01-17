import json

# Read the test results
with open('faq_test_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find all issues
issues = [r for r in data if r.get('has_error') or r.get('is_empty') or r.get('has_formatting_issues')]

print(f"Total questions: {len(data)}")
print(f"Questions with issues: {len(issues)}")
print(f"  - Errors: {sum(1 for r in data if r.get('has_error'))}")
print(f"  - Empty: {sum(1 for r in data if r.get('is_empty'))}")
print(f"  - Formatting issues: {sum(1 for r in data if r.get('has_formatting_issues'))}")
print("\n" + "="*80)
print("ISSUES FOUND:")
print("="*80)

for i, r in enumerate(issues[:20], 1):  # Show first 20
    print(f"\n{i}. Q: {r['question']}")
    if r.get('has_error'):
        print(f"   ERROR: {r.get('error', 'Unknown')}")
    if r.get('is_empty'):
        print(f"   ISSUE: Empty or too short")
    if r.get('has_formatting_issues'):
        print(f"   FORMATTING ISSUES: {', '.join(r.get('issues', []))}")
    print(f"   Answer: {r['answer'][:200]}...")

