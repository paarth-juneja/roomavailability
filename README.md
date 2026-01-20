# BITS Pilani Room Availability & Course Search

This project provides a web-based tool to find available empty classrooms and search for course schedules at BITS Pilani (Pilani Campus), based on data extracted from the official Timetable PDF.

**Live Websites:** [https://roomavailability.vercel.app/](https://roomavailability.vercel.app/) or [https://bitsroom.vercel.app/](https://bitsroom.vercel.app/)

## 🚀 Features

*   **Find Available Rooms:** Instantly locate empty classrooms by selecting a specific **Building** (FD 1, FD 2, FD 3, LTC, NAB), **Day**, and **Hour**.
*   **Course Search:** Search for any course by **Course Number** (e.g., "CS F111") or **Title** (e.g., "Probability").
*   **Detailed Schedules:** View complete details for a course, including section numbers, instructors, rooms, and weekly timing slots.
*   **Mobile-Friendly:** Responsive design that works well on phones and desktops.

## 🛠️ How It Works

The system consists of two main parts:
1.  **Data Extraction (`extract_data.py`):** A Python script uses `pdfplumber` to parse the university's `Timetable.pdf`. It intelligently identifies course codes, titles, instructors, rooms, and timing patterns (e.g., "M W 2", "T 7 8") to generate structured JSON data.
2.  **Web Interface (`index.html` & `script.js`):** A lightweight, client-side web application that reads the generated JSON files (`room_availability.json` and `courses.json`) to provide fast, interactive search and filtering without needing a backend server.

## 📂 File Structure

*   `index.html`: The main user interface for the web tool.
*   `script.js`: Handles logic for searching, filtering, and displaying results.
*   `style.css`: Modern styling for the application.
*   `extract_data.py`: Python automation script to convert `Timetable.pdf` into JSON data.
*   `inspect_pdf.py`: (Optional) Helper utility to inspect raw PDF data for debugging extraction logic.
*   `room_availability.json`: Generated database of room usage per hour.
*   `courses.json`: Generated database of all courses and their details.

## 🔧 Setup & Usage

### Prerequisites
*   Python 3.x
*   Basic web browser

### 1. Install Dependencies
You need `pdfplumber` to run the extraction script.
```bash
pip install pdfplumber
```

### 2. Prepare Data
Place your `Timetable.pdf` file in the root directory of the project.

### 3. Generate Database
Run the extraction script to process the PDF and create the JSON data files.
```bash
python extract_data.py
```
*You will see output indicating the number of pages scanned and slots extracted.*

### 4. Launch the App
Simply open `index.html` in your web browser.
```bash
# Example (macOS)
open index.html

# Example (Windows)
start index.html
```

## 📝 Notes
*   The extraction logic is tuned for the specific format of BITS Pilani timetables. If the PDF format changes significantly, `extract_data.py` may need updates (specifically the column indices and Regex patterns).
*   The "Hour" system maps standard class hours (e.g., Hour 1 = 8:00 AM - 9:00 AM).
