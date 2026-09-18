import json
from llm_interpreter import interpret_notes

def main():
    tests = [
        ["Solar will drop to 20% from 1 PM to 3 PM."],
        ["Do not charge the battery between 2 PM and 4 PM."],
        ["Keep at least 120 kWh in reserve from 6 PM until 9 PM."],
        ["Cafeteria menu changes tomorrow."],
        ["Solar will drop to 20% from 1 PM to 3 PM.", "Do not charge the battery between 2 PM and 4 PM.", "Library extends hours next week."]
    ]
    
    for i, test in enumerate(tests, 1):
        print(f"--- Test Case {i} ---")
        print("Input:", json.dumps(test))
        output = interpret_notes(test)
        print("Output:")
        print(json.dumps(output, indent=2))
        print("\n" + "="*40 + "\n")

if __name__ == "__main__":
    main()
