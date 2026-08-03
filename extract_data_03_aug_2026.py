import pdfplumber
import json
import re

def parse_days_hours_string(dh_string):
    """
    Parses day and hour strings like "T Th F 2", "M W 3 Th 9", "T 7 8".
    Returns a list of (Day, Hour) tuples.
    """
    tokens = dh_string.split()
    valid_days = {'M', 'T', 'W', 'Th', 'F', 'S'}
    
    current_days = []
    assignments = []
    last_was_number = False
    
    for token in tokens:
        if token in valid_days:
            if last_was_number:
                current_days = []
            current_days.append(token)
            last_was_number = False
        elif token.isdigit():
            hour = int(token)
            for day in current_days:
                assignments.append((day, hour))
            last_was_number = True
    
    return assignments

def detect_column_mapping(header_row):
    """
    Dynamically detect column positions from the table header row.
    Returns a dict with keys: course_no, course_title, sec, instructor, room, days_hours
    or None if this isn't a valid timetable header.
    """
    mapping = {}
    cleaned = [cell.strip().upper().replace("\n", " ") if cell else "" for cell in header_row]
    
    for i, cell in enumerate(cleaned):
        if "COURSE NO" in cell:
            mapping["course_no"] = i
        elif "COURSE TITLE" in cell:
            mapping["course_title"] = i
        elif cell == "SEC":
            mapping["sec"] = i
        elif "INSTRUCTOR" in cell:
            mapping["instructor"] = i
        elif cell == "ROOM":
            mapping["room"] = i
        elif "DAYS" in cell or "HOURS" in cell:
            mapping["days_hours"] = i
    
    # Must have at minimum room and days_hours to be useful
    if "room" in mapping and "days_hours" in mapping:
        return mapping
    return None

def is_header_row(row, mapping):
    """Check if a row is a header row (not data)."""
    cleaned = [cell.strip() if cell else "" for cell in row]
    
    # Check COM COD column (usually index 0)
    if cleaned and cleaned[0] and ("COM" in cleaned[0].upper() or "COD" in cleaned[0].upper()):
        return True
    
    # Check if course_no cell contains the header text
    if mapping and "course_no" in mapping and len(cleaned) > mapping["course_no"]:
        val = cleaned[mapping["course_no"]]
        if val and "COURSE" in val.upper():
            return True
            
    # Also check if any cell clearly says ROOM or DAYS & HOURS
    for cell in cleaned:
        cell_up = cell.upper().replace("\n", " ")
        if cell_up in ["COURSE NO.", "COURSE TITLE", "DAYS & HOURS"]:
            return True
    
    return False

def extract_rooms_from_cell(room_cell, valid_room_pattern):
    """
    Extract room numbers from a room cell.
    Handles formats like:
      - "1204"
      - "6107(F)\n6108(T Th)"  (multi-room with day annotations)
      - "1226 1227"
    Returns list of room numbers.
    """
    rooms = []
    # Split by newlines and spaces, then extract valid room numbers
    parts = re.split(r'[\s\n]+', room_cell)
    for part in parts:
        # Strip any parenthetical day annotations like "(F)" or "(T"
        clean = re.match(r'^(\d+)', part)
        if clean:
            room_num = clean.group(1)
            if valid_room_pattern.match(room_num):
                rooms.append(room_num)
    return rooms

def run_extraction():
    pdf_path = "Timetable_03_Aug_2026.pdf"
    print(f"Processing {pdf_path}...")
    
    room_usage = {}
    courses = []  # List of course objects
    
    # Building patterns
    # FD 1=1xxx, FD 2= 2xxx, FD 3= 3xxx, LTC = 5xxx, NAB = 6xxx
    valid_room_pattern = re.compile(r'^[12356]\d{3}$')
    
    # Track current course info for forward-filling
    current_course_no = ""
    current_course_title = ""
    current_instructor = ""
    
    # Maintain column mapping across pages for tables that continue without a repeated header
    current_mapping = None
    default_mapping = {
        "course_no": 1,
        "course_title": 2,
        "sec": 8,
        "instructor": 9,
        "room": 10,
        "days_hours": 11
    }
    
    with pdfplumber.open(pdf_path) as pdf:
        slot_count = 0
        course_count = 0
        skipped_tables = 0
        total_pages = len(pdf.pages)
        print(f"Total pages: {total_pages}")
        
        for i, page in enumerate(pdf.pages):
            if (i + 1) % 20 == 0 or i == 0 or (i + 1) == total_pages:
                print(f"Scanning page {i+1}/{total_pages}...")
            
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table[0]) < 10:
                    continue
                
                # Dynamically detect column mapping from header row
                mapping = None
                header_search_limit = min(3, len(table))  # Check first 3 rows for header
                for h_idx in range(header_search_limit):
                    mapping = detect_column_mapping(table[h_idx])
                    if mapping:
                        break
                
                if mapping:
                    current_mapping = mapping
                elif len(table[0]) >= 12:
                    # If this table has 12+ columns (timetable structure) but no header row
                    # (e.g. continuation from previous page like Page 95), reuse existing mapping or default
                    mapping = current_mapping or default_mapping
                else:
                    skipped_tables += 1
                    continue
                
                for row in table:
                    num_cols = len(row)
                    
                    # Clean all cells
                    cleaned = [cell.strip() if cell else "" for cell in row]
                    
                    # Skip header rows
                    if is_header_row(row, mapping):
                        continue
                    
                    # Extract fields based on column count
                    if num_cols > max(mapping.values()):
                        course_no = cleaned[mapping["course_no"]] if "course_no" in mapping else ""
                        course_title = cleaned[mapping["course_title"]] if "course_title" in mapping else ""
                        sec = cleaned[mapping["sec"]] if "sec" in mapping else ""
                        instructor = cleaned[mapping["instructor"]] if "instructor" in mapping else ""
                        room_raw = cleaned[mapping["room"]]
                        time_raw = cleaned[mapping["days_hours"]]
                    elif num_cols >= 10:
                        # Fallback: Row has fewer columns due to merged cells in pdfplumber
                        room_raw = ""
                        time_raw = ""
                        course_no = cleaned[1] if num_cols > 1 else ""
                        course_title = cleaned[2] if num_cols > 2 else ""
                        sec = ""
                        instructor = ""
                        
                        # Scan cells to find room (4-digit number) and time (day/hour pattern)
                        valid_days_set = {'M', 'T', 'W', 'Th', 'F', 'S'}
                        for ci in range(3, num_cols):
                            cell_val = cleaned[ci]
                            if not cell_val:
                                continue
                            first_word = cell_val.split()[0] if cell_val.split() else ""
                            if valid_room_pattern.match(first_word) and not room_raw:
                                room_raw = cell_val
                                continue
                            tokens = cell_val.split()
                            has_day = any(t in valid_days_set for t in tokens)
                            has_hour = any(t.isdigit() for t in tokens)
                            if has_day and has_hour and not time_raw:
                                time_raw = cell_val
                                continue
                            if re.match(r'^[LTP]\d+$', cell_val) and not sec:
                                sec = cell_val
                                continue
                            if len(cell_val) > 3 and any(c.isalpha() for c in cell_val) and not instructor:
                                if not re.match(r'^\d{2}/\d{2}', cell_val):
                                    instructor = cell_val
                    else:
                        continue
                    
                    # Clean newlines from instructor names
                    instructor = instructor.replace("\n", " ").strip()
                    
                    # Forward-fill course number and title
                    if course_no and not course_no.startswith("COURSE"):
                        current_course_no = course_no
                    if course_title and course_title not in ["COURSE TITLE", "Practical", "Tutorial"]:
                        current_course_title = course_title
                    if instructor and instructor not in ["INSTRUCTOR-IN-CHARGE / Instructor", "INSTRUCTOR-IN-CHARGE /", "Instructor"]:
                        current_instructor = instructor
                    
                    if not room_raw or not time_raw:
                        continue
                    
                    # Extract all room numbers from the cell
                    rooms = extract_rooms_from_cell(room_raw, valid_room_pattern)
                    if not rooms:
                        continue
                    
                    pairs = parse_days_hours_string(time_raw)
                    if not pairs:
                        continue
                    
                    # Use the first valid room as the primary room
                    room = rooms[0]
                    
                    # Add to room_usage for ALL rooms found in the slot
                    for r in rooms:
                        if r not in room_usage:
                            room_usage[r] = {d: [] for d in ['M', 'T', 'W', 'Th', 'F', 'S']}
                        for d, h in pairs:
                            if h not in room_usage[r][d]:
                                room_usage[r][d].append(h)
                                slot_count += 1
                    
                    # Build schedule dict for this entry
                    schedule = {}
                    for d, h in pairs:
                        if d not in schedule:
                            schedule[d] = []
                        if h not in schedule[d]:
                            schedule[d].append(h)
                    
                    # Sort hours in schedule
                    for d in schedule:
                        schedule[d] = sorted(schedule[d])
                    
                    # Add course entry
                    course_entry = {
                        "course_no": current_course_no,
                        "course_title": current_course_title,
                        "section": sec,
                        "instructor": current_instructor,
                        "room": room,
                        "schedule": schedule,
                        "raw_time": time_raw
                    }
                    courses.append(course_entry)
                    course_count += 1
    
    print(f"Extracted {slot_count} slots from {course_count} entries.")
    if skipped_tables:
        print(f"Skipped {skipped_tables} non-timetable tables.")
    
    # Save room_availability.json
    sorted_rooms = sorted(room_usage.keys())
    final_room_data = {}
    for r in sorted_rooms:
        final_room_data[r] = {}
        for d in ['M', 'T', 'W', 'Th', 'F', 'S']:
            final_room_data[r][d] = sorted(room_usage[r][d])
            
    with open("room_availability.json", "w") as f:
        json.dump(final_room_data, f, indent=2)
    print(f"Saved room_availability.json ({len(sorted_rooms)} rooms)")
    
    # Save courses.json
    with open("courses.json", "w", encoding="utf-8") as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)
    print(f"Saved courses.json ({len(courses)} entries)")

if __name__ == "__main__":
    run_extraction()
