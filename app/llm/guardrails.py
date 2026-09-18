def validate_hours(hours) -> bool:
    if not isinstance(hours, list) or not hours:
        return False
    if not all(isinstance(h, int) for h in hours):
        return False
    if len(set(hours)) != len(hours):
        return False
    if sorted(hours) != hours:
        return False
    if not all(0 <= h <= 23 for h in hours):
        return False
    return True

def validate_one(entry, note_index, total_notes, battery_info=None) -> dict | None:
    if not isinstance(entry, dict):
        return None
    
    required_keys = {"note_index", "applies", "directive_type", "structured_adjustment", "explanation"}
    if not required_keys.issubset(entry.keys()):
        return None
        
    if entry.get("note_index") != note_index:
        return None
        
    directive_type = entry.get("directive_type")
    valid_directives = {
        "solar_reduction", 
        "minimum_battery_reserve", 
        "no_charge_window", 
        "no_discharge_window", 
        "max_grid_window", 
        "no_op"
    }
    
    if directive_type not in valid_directives:
        return None
        
    if directive_type == "no_op":
        if entry.get("applies") is not False:
            return None
        if entry.get("structured_adjustment") is not None:
            return None
    else:
        if entry.get("applies") is not True:
            return None
        
        sa = entry.get("structured_adjustment")
        if not isinstance(sa, dict):
            return None
            
        if "hours" not in sa or not validate_hours(sa["hours"]):
            return None
            
        if directive_type == "solar_reduction":
            if "factor" not in sa:
                return None
            factor = sa["factor"]
            if not isinstance(factor, (int, float)) or not (0 <= factor <= 1):
                return None
                
        elif directive_type == "minimum_battery_reserve":
            if "minimum_energy_kwh" not in sa:
                return None
            minimum_energy_kwh = sa["minimum_energy_kwh"]
            if not isinstance(minimum_energy_kwh, (int, float)) or minimum_energy_kwh < 0:
                return None
            if battery_info and "capacity_kwh" in battery_info:
                if minimum_energy_kwh > battery_info["capacity_kwh"]:
                    sa["minimum_energy_kwh"] = battery_info["capacity_kwh"]
                
        elif directive_type == "max_grid_window":
            if "max_grid_kwh" not in sa:
                return None
            max_grid_kwh = sa["max_grid_kwh"]
            if not isinstance(max_grid_kwh, (int, float)) or max_grid_kwh < 0:
                return None
                
    # Return cleaned dict
    return {
        "note_index": entry["note_index"],
        "applies": entry["applies"],
        "directive_type": entry["directive_type"],
        "structured_adjustment": entry["structured_adjustment"],
        "explanation": entry["explanation"]
    }

def validate_all(llm_output, total_notes, battery_info=None) -> list | None:
    if not isinstance(llm_output, list):
        return None
    if len(llm_output) != total_notes:
        return None
        
    cleaned_list = []
    for i, entry in enumerate(llm_output):
        cleaned = validate_one(entry, i, total_notes, battery_info)
        if cleaned is None:
            return None
        cleaned_list.append(cleaned)
        
    return cleaned_list
