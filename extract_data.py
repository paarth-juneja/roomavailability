
import pdfplumber
import json
import re

def extract_timetable_data(pdf_path):
    print(f"Processing {pdf_path}...")
    
    room_usage = {}  # { "ROOM_NO": { "M": [1, 2], "T": [3] } }
    
    # Building patterns
    # FD 1=1xxx, FD 2= 2xxx, FD 3= 3xxx, LTC = 5xxx, NAB = 6xxx
    # We will just check if first digit is 1, 2, 3, 5, 6 and length is 4.
    valid_room_pattern = re.compile(r'^[12356]\d{3}$')
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Total pages: {total_pages}")
        
        # We start looking for data from page 6 where "COM COD" header usually starts appearing reliably,
        # or we can process all pages and filter by header existence.
        # Based on previous inspection, header found on page 6.
        
        for i, page in enumerate(pdf.pages):
            if i % 10 == 0:
                print(f"Scanning page {i+1}...")
            
            tables = page.extract_tables()
            
            for table in tables:
                # Basic check if it's a valid data table
                # Header row usually contains "COM COD", "COURSE NO." etc.
                # But headers might be repeated or not. We just look for rows with data.
                
                # Table structure from PDF inspection:
                # Col 0: COM COD (often empty if continued)
                # Col 1: COURSE NO
                # Col 2: COURSE TITLE
                # Col 6: SEC
                # Col 8: ROOM
                # Col 9: DAYS & HOURS
                
                # Note: pdfplumber table extraction might have None for empty cells
                # We need to handle column indices carefully.
                
                # Check if this table has enough columns
                if not table or len(table[0]) < 9:
                    continue
                
                for row in table:
                    # Clean the row
                    cleaned_row = [cell.strip() if cell else "" for cell in row]
                    
                    # Columns based on visual inspection of Page 21 output:
                    # 0: COM COD
                    # 1: COURSE NO
                    # 2: COURSE TITLE
                    # ...
                    # 8: ROOM (index 8 seems to be room based on "1126", "1194" etc in previous output)
                    # 9: DAYS & HOURS
                    
                    room_cell = cleaned_row[8]
                    days_hours_cell = cleaned_row[9]
                    
                    # Check if room is valid
                    # Room might contain multiple rooms? Usually one per row.
                    # Sometimes room is empty.
                    
                    if not room_cell:
                        continue
                        
                    # Handle multiple rooms if separated by space/comma? 
                    # Usually "1231"
                    
                    room_candidate = room_cell.split()[0] if room_cell else ""
                    if not valid_room_pattern.match(room_candidate):
                        continue
                    
                    if not days_hours_cell:
                        continue
                        
                    # Parse days and hours
                    # Format examples: "T Th F 2", "M 9", "T 7 8", "M W 2 T 9"
                    
                    # Logic: 
                    # Tokenize by space
                    # Keep track of current days buffer
                    # If token is Day (M, T, W, Th, F, S), add to buffer
                    # If token is Number, add this number to all days in buffer
                    
                    # Wait, "M W 2" means M at 2, W at 2.
                    # "T 7 8" means T at 7 and 8.
                    # "M W 2 T 9" means M at 2, W at 2, T at 9.
                    
                    tokens = days_hours_cell.split()
                    current_days = []
                    
                    valid_days = {'M', 'T', 'W', 'Th', 'F', 'S'}
                    
                    for token in tokens:
                        if token in valid_days:
                            current_days.append(token)
                        elif token.isdigit():
                            hour = int(token)
                            # Apply to all current days
                            # BUT, if we have "M W 2 T 9", at '2' we apply to M, W.
                            # Then we hit 'T'. Should we clear M, W? Yes.
                            # Because '9' only applies to 'T'.
                            
                            # However, consider "T 7 8".
                            # T -> current_days=[T]
                            # 7 -> T: [7]
                            # 8 -> T: [8] (current_days still [T]?)
                            
                            # The rule usually is: Days apply until new days appear?
                            # Or: Numbers apply to immediately preceding chain of days?
                            
                            # Case "T 7 8": T applies to 7. Does it apply to 8? Yes.
                            # Case "M W 2 T 9": M W apply to 2. T applies to 9.
                            
                            # Algorithm:
                            # 1. Gather Days.
                            # 2. When Number encountered, apply to gathered Days.
                            # 3. Keep gathered Days?
                            #    If next is Number, yes (T 7 8).
                            #    If next is Day, no (M W 2 T...).
                            
                            # So, we just keep current_days. 
                            # If we encounter a Day, AND the previous token was a number, we probably clear previous days?
                            # Actually, simpler: 
                            # Iterate tokens.
                            # If Day -> append to current_days list.
                            # If Number -> apply time to all days in current_days.
                            #   Crucial: If we see a Day, should we clear the list FIRST?
                            #   In "M W 2", we see M, then W. List = [M, W]. Then 2. Add 2 to M and W.
                            #   Then "T 9". We see T. Should we clear [M, W]? Yes.
                            #   Because T is a new group.
                            #   
                            #   So: If token is Day:
                            #       If previous_token_was_number: Clear current_days.
                            #       Append Day.
                            
                            # Let's trace "T 7 8":
                            # T -> [T]. prev_was_num=False.
                            # 7 -> Add 7 to T. prev_was_num=True.
                            # 8 -> [T] valid. Add 8 to T. prev_was_num=True.
                            
                            # Trace "M W 2 T 9":
                            # M -> [M].
                            # W -> [M, W].
                            # 2 -> Add 2 to M, W. prev_was_num=True.
                            # T -> prev_was_num=True -> Clear. [T].
                            # 9 -> Add 9 to T.
                            
                            # Looks correct.
                            
                            pass 
                        else:
                            # Could be tutorial/practical notation or parens?
                            pass

    # Actually implementing the logic inside the loop is messy, let's process carefully
    
    # We re-iterate cleanly
    pass

def parse_days_hours_string(dh_string):
    # Returns list of (Day, Hour) tuples
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

def run_extraction():
    pdf_path = "Timetable.pdf"
    
    # Init room usage with empty slots
    # But we don't know all rooms yet. We build dynamically.
    room_usage = {}
    
    valid_room_pattern = re.compile(r'^[12356]\d{3}$')
    
    with pdfplumber.open(pdf_path) as pdf:
        count = 0
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table[0]) < 9:
                    continue
                
                for row in table:
                    # Safety check
                    if len(row) < 10: 
                         # Some rows might be shorter? 
                         # Usually pdfplumber makes rectangular tables, filling None
                         pass
                    
                    # Columns index might vary if there are fewer columns detected
                    # We rely on previous inspection that index 8 is room, 9 is time.
                    try:
                        room_raw = row[8]
                        time_raw = row[9]
                    except IndexError:
                        continue
                        
                    if not room_raw or not time_raw:
                        continue
                    
                    room_raw = room_raw.strip()
                    time_raw = time_raw.strip()
                    
                    # Sometimes room has extra chars? "1231"
                    # Just take first word
                    room_parts = room_raw.split()
                    if not room_parts: continue
                    room = room_parts[0]
                    
                    if not valid_room_pattern.match(room):
                        continue
                    
                    pairs = parse_days_hours_string(time_raw)
                    
                    if room not in room_usage:
                        room_usage[room] = {d: [] for d in ['M', 'T', 'W', 'Th', 'F', 'S']}
                    
                    for d, h in pairs:
                        if h not in room_usage[room][d]:
                            room_usage[room][d].append(h)
                            count += 1
    
    print(f"Extracted {count} slots.")
    
    # Sort rooms and hours
    sorted_rooms = sorted(room_usage.keys())
    final_data = {}
    for r in sorted_rooms:
        final_data[r] = {}
        for d in ['M', 'T', 'W', 'Th', 'F', 'S']:
            final_data[r][d] = sorted(room_usage[r][d])
            
    with open("room_availability.json", "w") as f:
        json.dump(final_data, f, indent=2)
        
    print("Saved room_availability.json")

if __name__ == "__main__":
    run_extraction()
