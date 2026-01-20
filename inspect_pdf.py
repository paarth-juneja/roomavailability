
import pdfplumber

def inspect_first_page(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) > 20:
            page_num = 20
            page = pdf.pages[page_num]
            print(f"--- INSPECTING PAGE {page_num + 1} ---")
            text = page.extract_text()
            print("--- TEXT EXTRACTION ---")
            print(text[:2000])
            print("\n--- TABLE EXTRACTION ---")
            tables = page.extract_tables()
            if tables:
                for j, table in enumerate(tables):
                    print(f"Table {j}:")
                    for row in table[:20]: # Print more rows
                        print(row)
            else:
                print("No tables found.")
        else:
            print("PDF shorter than 20 pages.")

if __name__ == "__main__":
    inspect_first_page("Timetable.pdf")
