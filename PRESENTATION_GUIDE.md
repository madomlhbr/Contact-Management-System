# MSYS 30 presentation and live demonstration (12–14 minutes)

| Time | Speaker focus | Show / explain |
|---|---|---|
| 0:00–1:30 | Problem and goals | Messy contact records, inconsistent industry labels and duplicate entries |
| 1:30–3:00 | Architecture | Python list of contact records; separate domain logic and Tkinter interface; linked request queue and undo stack |
| 3:00–5:00 | Desktop walkthrough | Run `python MSYS30_External_Relations_Contact_System.py --gui --gui-demo`; show 12 fictional contacts, sorting and filter modes |
| 5:00–6:30 | New algorithm: merge sort | Stable recursive divide-and-conquer, O(n log n) sorting, adjacent comparisons for duplicates |
| 6:30–8:00 | New algorithm: binary search | Normalized exact lookup in sorted cached index, O(log n) warm query; distinction from keyword linear search |
| 8:00–10:00 | FIFO + LIFO demo | Add a fictional contact, stage edit/delete, process in order, undo most recent change |
| 10:00–11:15 | Data quality and I/O | Industry label review, duplicate candidates, CSV import, JSON save and export; discuss validation |
| 11:15–12:30 | Correctness and efficiency | Run `--self-test`; show benchmark CSV and complexity table |
| 12:30–14:00 | Limitations and questions | Local single-user program, no real contact records, no automated merging; future authenticated multi-user system |

**Before presenting:** install Python with Tkinter and test a graphical desktop. Run the demo using `--data demo_contacts.json` so real records are never overwritten. Avoid committing the generated JSON file.

**Possible questions**: Why merge sort instead of quicksort? What happens before the first binary search? How do you ensure FIFO and LIFO order? What causes a record to be flagged as a possible duplicate? What if one imported CSV row is malformed? What are the worst-case sorting bounds?
