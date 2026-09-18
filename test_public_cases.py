import json
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "app", "llm"))
from app.llm.llm_interpreter import interpret_notes

def main():
    file_path = "app/llm/public_class.json"
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return
        
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    cases = data.get("cases", [])
    print(f"Loaded {len(cases)} cases. Starting tests...\n")
    
    passed = 0
    for case in cases:
        case_id = case["id"]
        notes = case["input"]["operator_notes"]
        battery_info = case["input"].get("battery")
        expected_interpretation = case["expected_output"]["directive_interpretation"]
        
        print(f"--- Testing {case_id} ---")
        print(f"Notes: {notes}")
        try:
            result = interpret_notes(notes, battery_info=battery_info)
            print("Result generated successfully.")
            
            # Simple check to see if the directive types match
            expected_types = [item["directive_type"] for item in expected_interpretation]
            result_types = [item["directive_type"] for item in result]
            
            if expected_types == result_types:
                print("[PASS] Match: Directive types are correct.")
                passed += 1
            else:
                print(f"[FAIL] Mismatch: Expected {expected_types}, got {result_types}")
                
        except Exception as e:
            print(f"[FAIL] Error during interpretation: {e}")
            
        print("="*40 + "\n")
        
    print(f"--- Summary ---")
    print(f"Passed: {passed}/{len(cases)} cases.")

if __name__ == "__main__":
    main()
