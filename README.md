# ContactFlow — External Relations Contact Management System

**MSYS 30 | Data Structures & Algorithms | Ateneo de Manila University**  
**Project:** Efficient Sorting, Searching, and Labeling of Company Records

ContactFlow is a local, single-user Python system for organizing partner companies, contact people, and industries. Its new **Tkinter desktop dashboard** uses the five-color palette supplied for the project. The CLI and algorithms remain available for reproducible assessment.

## Desktop user interface

Launch on a computer with **Python 3.9+ and Tkinter** (no third-party Python dependencies):

```bash
python MSYS30_External_Relations_Contact_System.py --gui
```

Launch a safe visual demo with fictional contacts:

```bash
python MSYS30_External_Relations_Contact_System.py --gui --gui-demo --data demo_contacts.json
```

> Windows: open PowerShell or Terminal in this repository folder. Use `py` instead of `python` if needed. Install Python with Tkinter if your Python distribution does not include it. The desktop window requires a graphical display (not GitHub's browser or an ordinary cloud terminal).

The five colors are navy `#0E3B5C`, plum `#5E4F6D`, mauve `#9F6671`, coral `#D8897B`, and peach `#F4AC7B`.

### Using the dashboard

1. **Directory**: view and sort contacts by company, contact, industry, or email. Choose merge sort or quicksort, ascending or descending.
2. **Search**: select **Exact company (binary)** for normalized company-name matches, or **Keyword (linear)** for matches across record fields.
3. **Add/edit/delete**: select or create a record; the change is staged in the linked **FIFO request queue**, rather than immediately applied.
4. **Request queue**: select **Process next** or **Process all** to apply changes in order. Use **Undo** to reverse the most recently completed change with the LIFO stack.
5. **Sidebar reports**: display industry groups, possible duplicate company names, and labels needing review. Suspected duplicates are **not automatically removed**, and uncertain labels are **not silently confirmed**.
6. **Import/export**: CSV import validates all rows first; a malformed record cancels the whole import. Save to a local JSON file; use CSV export to share a copy of the directory.
7. **Algorithm lab**: read time/space complexity explanations and run an optional sorting benchmark (results appear in the launch terminal).

Keyboard shortcuts: **Ctrl+S** save, **Ctrl+N** add, **Ctrl+F** search focus, **Ctrl+Z** undo, **Delete** queue deletion for a selected row.

## Algorithms and data structures

| Component | Application | Complexity |
|---|---|---|
| Merge sort (recursive, stable) | Sorting, duplicate detection, grouping, exact search index | O(n log n) time, O(n) auxiliary space |
| Binary search (iterative and recursive) | Exact normalized company lookup on a sorted index | O(log n) warm search; initial index building costs O(n log n) |
| Linear search | Keyword lookup across fields | O(n) |
| Quick sort | Alternative directory sort | O(n log n) average, O(n²) worst |
| Linked queue (FIFO) | Stage/add/process edit requests | O(1) enqueue and dequeue pointer work |
| Array-backed stack (LIFO) | Undo completed changes | O(1) push/pop for bounded entries |
| Python list (dynamic array) | Canonical record storage | O(1) indexed read, O(n) middle insertion/deletion |
| Bubble / insertion / selection sort | Baseline comparisons only | O(n²) average/worst |

**Important:** normalized-name duplicate detection identifies *possible* duplicates for manual review. Company records and CSV data may contain personal information; the provided example file uses fictional names and `.example` email domains. **Never commit real contact lists or generated `contact_records.json` to this public repository.** This is not a hosted, authenticated CRM.

## Other commands

```bash
# Original numbered terminal interface
python MSYS30_External_Relations_Contact_System.py --data contact_records.json

# Text demo
python MSYS30_External_Relations_Contact_System.py --demo

# Existing 28 algorithm/unit tests
python MSYS30_External_Relations_Contact_System.py --self-test

# CLI performance tests
python MSYS30_External_Relations_Contact_System.py --benchmark --benchmark-csv benchmark_new.csv
python MSYS30_External_Relations_Contact_System.py --benchmark-search

# Desktop smoke tests (on Linux CI, Xvfb is used)
python -m unittest -v test_gui.py
```

## Files

- `MSYS30_External_Relations_Contact_System.py` — domain logic, search/sort algorithms, CLI, tests, benchmarks, and `--gui` integration
- `contact_gui.py` — five-color desktop GUI with directory, form validation, FIFO queue, reporting, and algorithm tab
- `test_gui.py` — GUI smoke tests for search, CRUD queue, undo, persistence, and validation
- `MSYS30_fictional_contacts_sample.csv` — synthetic test contacts only
- `MSYS30_benchmark_results.csv` — captured example benchmark results; measured on one environment, not universal timings
- `MSYS30_Final_Project_Paper.pdf` / `.docx` — formal submission paper and editable document
- `PRESENTATION_GUIDE.md` — suggested 12–14 minute presentation/demo walkthrough

## Safety and limitations

The program is designed as a **local class-project prototype**: no multi-user synchronization, login/access control, hosted database, fuzzy matching, or machine learning. Pending requests and undo history are in-memory session state; JSON saves committed records only. Save before exit, and keep private contact files outside this repository.

## Project requirements cross-check

| Instructor requirement | Evidence |
|---|---|
| Practical information-system problem | Contact directory and industry standardization |
| Interface, I/O, error handling, overall architecture | Tkinter dashboard, modal forms, CSV/JSON, validation, separated domain/UI modules |
| At least two algorithms and two structures | Merge sort, binary search, linked queue, stack, array/list |
| Testing and debugging | 28 core automated tests plus GUI smoke tests, GitHub Actions workflow |
| Time and space complexity | Algorithm lab and project paper |
| Documentation and code snippets | README and project report |
| 10–15 minute presentation | `PRESENTATION_GUIDE.md` |

## Team

Dylan Bueno and Amado Malhabour.
