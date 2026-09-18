import os
import json
from groq import Groq
from dotenv import load_dotenv
from guardrails import validate_all

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are an energy directive interpreter for a smart campus. You will receive operator notes. For EACH note, return exactly one JSON object. Return a JSON array with one entry per note, in note_index order 0..N-1.
Allowed directive_type and structured_adjustment:
- solar_reduction -> {"hours": [...], "factor": <0-1>}
- minimum_battery_reserve -> {"hours": [...], "minimum_energy_kwh": <number>}
- no_charge_window -> {"hours": [...]}
- no_discharge_window -> {"hours": [...]}
- max_grid_window -> {"hours": [...], "max_grid_kwh": <number>}
- no_op -> null

Rules:
1. One entry per note, note_index order 0..N-1.
2. no_op: applies=false, structured_adjustment=null.
3. Every other directive: applies=true.
4. hours = unique integers 0-23 ascending.
5. Windows: start-inclusive, end-exclusive. "1 PM to 3 PM" -> [13, 14].
6. solar_reduction factor = USABLE fraction remaining. 80% reduction -> 0.2.
7. If note doesn't affect today's energy schedule -> no_op.
8. Do NOT invent data or unsupported types. Return ONLY valid JSON array. No markdown fences."""

FEW_SHOT = """Example 1:
Input: ["Solar will drop to 20% from 1 PM to 3 PM.", "Cafeteria menu changes tomorrow."]
Output: [{"note_index":0,"applies":true,"directive_type":"solar_reduction","structured_adjustment":{"hours":[13,14],"factor":0.2},"explanation":"Solar reduced to 20%."},{"note_index":1,"applies":false,"directive_type":"no_op","structured_adjustment":null,"explanation":"Not related to energy."}]

Example 2:
Input: ["Do not charge the battery between 2 PM and 4 PM."]
Output: [{"note_index":0,"applies":true,"directive_type":"no_charge_window","structured_adjustment":{"hours":[14,15]},"explanation":"Charging disabled."}]

Example 3:
Input: ["Keep at least 120 kWh in reserve from 6 PM until 9 PM."]
Output: [{"note_index":0,"applies":true,"directive_type":"minimum_battery_reserve","structured_adjustment":{"hours":[18,19,20],"minimum_energy_kwh":120},"explanation":"Reserve required."}]"""

def call_llm(operator_notes: list[str], battery_info: dict = None) -> list[dict]:
    input_data = {"notes": operator_notes}
    if battery_info:
        input_data["battery_context"] = battery_info
    prompt = f"Input: {json.dumps(input_data)}\n\n{FEW_SHOT}\n\nNow interpret the Input."
    
    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        response_format={"type": "json_object"}
    )
    
    text = response.choices[0].message.content.strip()
    
    parsed = json.loads(text)
    if isinstance(parsed, dict):
        if len(parsed.keys()) == 1:
            key = list(parsed.keys())[0]
            if isinstance(parsed[key], list):
                return parsed[key]
        return [parsed]
    return parsed

def interpret_notes(operator_notes: list[str], battery_info: dict = None, max_retry: int = 2) -> list[dict]:
    for _ in range(max_retry + 1):
        try:
            llm_output = call_llm(operator_notes, battery_info)
            validated = validate_all(llm_output, len(operator_notes), battery_info=battery_info)
            if validated is not None:
                return validated
            else:
                print(f"Validation failed for: {llm_output}")
        except Exception as e:
            print(f"Exception: {e}")
            
    # Fallback
    fallback = []
    for i in range(len(operator_notes)):
        fallback.append({
            "note_index": i,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": None,
            "explanation": "Failed to parse or validate."
        })
    return fallback
