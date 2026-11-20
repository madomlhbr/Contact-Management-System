#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import statistics
import sys
import tempfile
import time
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Callable, Optional


# ================================================================
# DATA STRUCTURES FROM CODING ASSIGNMENT 2 (same push/pop and FIFO logic)
# ================================================================
class UndoStack:
    """Array-backed Last-In, First-Out history (Coding Assignment 2)."""

    def __init__(self):
        self._items = []

    def push(self, item):
        self._items.append(deepcopy(item))

    def pop(self):
        return self._items.pop() if self._items else None

    def peek(self):
        return deepcopy(self._items[-1]) if self._items else None

    def __len__(self):
        return len(self._items)


class QueueNode:
    """One node in a singly linked list (Coding Assignment 2)."""

    def __init__(self, value):
        self.value = deepcopy(value)
        self.next = None


class RequestQueue:
    """Linked First-In, First-Out request queue (Coding Assignment 2)."""

    def __init__(self):
        self.front = None
        self.rear = None
        self.count = 0

    def enqueue(self, request):
        """Attach a new node at the rear: O(1) pointer work."""
        node = QueueNode(request)
        if self.rear is None:
            self.front = node
        else:
            self.rear.next = node
        self.rear = node
        self.count += 1

    def dequeue(self):
        """Remove and return the oldest request: O(1) pointer work."""
        if self.front is None:
            return None
        node = self.front
        self.front = node.next
        if self.front is None:
            self.rear = None
        self.count -= 1
        return deepcopy(node.value)

    def peek(self):
        return deepcopy(self.front.value) if self.front else None

    def to_list(self):
        out = []
        node = self.front
        while node is not None:
            out.append(deepcopy(node.value))
            node = node.next
        return out

    def __len__(self):
        return self.count


# ================================================================
# RECORD KEYS, VALIDATION AND TRANSPARENT INDUSTRY TAXONOMY
# ================================================================
# The first five aliases explicitly preserve CA2's original equivalents.
INDUSTRY_ALIASES = {
    "tech": "Technology",
    "it": "Technology",
    "technology": "Technology",
    "information technology": "Technology",
    "entrep": "Entrepreneurship",
    "entrepreneurship": "Entrepreneurship",
    "software": "Technology",
    "fintech": "Technology",
    "education": "Education",
    "academic": "Education",
    "school": "Education",
    "finance": "Finance",
    "financial services": "Finance",
    "banking": "Finance",
    "healthcare": "Healthcare",
    "health": "Healthcare",
    "medical": "Healthcare",
    "retail": "Retail",
    "commerce": "Retail",
    "food and beverage": "Food and Beverage",
    "f&b": "Food and Beverage",
    "hospitality": "Hospitality",
    "travel": "Travel and Tourism",
    "tourism": "Travel and Tourism",
    "transportation": "Transportation",
    "logistics": "Transportation",
    "media": "Media and Entertainment",
    "entertainment": "Media and Entertainment",
    "manufacturing": "Manufacturing",
}

# Used ONLY to suggest labels; the unmodified industry input is retained.
SUGGESTION_KEYWORDS = (
    ("Technology", ("software", "tech", "digital", "computer", "cloud", "app", "data")),
    ("Education", ("school", "university", "academy", "education", "learning")),
    ("Finance", ("bank", "finance", "insurance", "payment")),
    ("Healthcare", ("hospital", "health", "clinic", "medical")),
    ("Food and Beverage", ("coffee", "cafe", "restaurant", "food", "bakery")),
    ("Travel and Tourism", ("hotel", "tourism", "travel", "resort")),
    ("Transportation", ("logistics", "transport", "courier", "shipping")),
    ("Retail", ("retail", "store", "shop", "market")),
    ("Media and Entertainment", ("media", "studio", "film", "music")),
    ("Manufacturing", ("factory", "manufactur", "fabrication")),
)

FIELDNAMES = ("id", "company", "contact", "industry", "email", "notes")
CSV_EXPORT_FIELDS = FIELDNAMES + ("standardized_industry", "label_status")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SUFFIX_PATTERN = re.compile(
    r"(?:\s+(?:incorporated|inc|corp|corporation|company|co|ltd|llc))$"
)


def normalize_company(value: str) -> str:
    """Lowercase, remove punctuation/extra spaces and common terminal legal suffixes.

    Exact normalized matches are *possible* duplicates, not proof of one company.
    """
    name = re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
    name = re.sub(r"\s+", " ", name)
    old = None
    while name != old:
        old = name
        name = SUFFIX_PATTERN.sub("", name).strip()
    return name


def clean_text(value) -> str:
    return " ".join(str(value if value is not None else "").split())


def classify_industry(industry: str, company: str) -> tuple[str, str]:
    """Returns (display label, status), always retaining the original text.

    Fixed aliases are applied only to equivalent names; keyword hints are flagged
    for human review rather than silently treated as confirmed industries.
    """
    raw = clean_text(industry)
    lowered = raw.casefold()
    if lowered in INDUSTRY_ALIASES:
        label = INDUSTRY_ALIASES[lowered]
        return label, ("Standard" if lowered == label.casefold() else "Standardized")
    text_to_inspect = f"{raw} {company}".casefold()
    for category, keywords in SUGGESTION_KEYWORDS:
        if any(re.search(r"\b" + re.escape(word), text_to_inspect) for word in keywords):
            return category, "Suggested - review"
    if not raw:
        return "Unlabeled", "Missing - review"
    return "Unclassified", "Unrecognized - review"


def validate_record(source: dict) -> dict:
    """Validate and clean one logical company-contact record."""
    if not isinstance(source, dict):
        raise ValueError("Each record must be a dictionary/object.")
    result = {field: clean_text(source.get(field, "")) for field in FIELDNAMES if field != "id"}
    if not result["company"] or not result["contact"]:
        raise ValueError("Company and contact person are required.")
    if result["email"] and not EMAIL_PATTERN.fullmatch(result["email"]):
        raise ValueError("Email is not valid (leave blank when unknown).")
    return result


# ================================================================
# NEW ALGORITHM 1: RECURSIVE STABLE MERGE SORT
# ================================================================
def merge_sort(items: list, key: Callable = lambda x: x,
               reverse: bool = False, metrics: Optional[dict] = None) -> list:
    """Stable O(n log n) comparison sort; O(n) auxiliary memory.

    Equal keys always take the left element first, also in descending order.
    Does not use Python's built-in sorted()/list.sort() for sorting.
    """
    if metrics is not None:
        metrics.setdefault("comparisons", 0)

    def rec(seq):
        if len(seq) <= 1:
            return seq[:]
        half = len(seq) // 2
        left = rec(seq[:half])
        right = rec(seq[half:])
        result = []
        i = j = 0
        while i < len(left) and j < len(right):
            if metrics is not None:
                metrics["comparisons"] += 1
            lk, rk = key(left[i]), key(right[j])
            take_left = (lk >= rk) if reverse else (lk <= rk)
            if take_left:
                result.append(left[i]); i += 1
            else:
                result.append(right[j]); j += 1
        result.extend(left[i:])
        result.extend(right[j:])
        return result

    return rec(items)


# ================================================================
# NEW ALGORITHM 2: ITERATIVE AND RECURSIVE BINARY SEARCH
# ================================================================
def binary_search_iterative(ordered: list, target: str,
                            key: Callable = lambda x: x,
                            metrics: Optional[dict] = None) -> int:
    """Return one match index, or -1. Ordered list required. O(log n)."""
    low, high = 0, len(ordered) - 1
    while low <= high:
        mid = (low + high) // 2
        if metrics is not None:
            metrics["comparisons"] = metrics.get("comparisons", 0) + 1
        current = key(ordered[mid])
        if current == target:
            return mid
        if current < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1


def binary_search_recursive(ordered: list, target: str,
                            key: Callable = lambda x: x,
                            metrics: Optional[dict] = None) -> int:
    """Recursive variant of binary search. O(log n) time and call stack."""
    def rec(low, high):
        if low > high:
            return -1
        mid = (low + high) // 2
        if metrics is not None:
            metrics["comparisons"] = metrics.get("comparisons", 0) + 1
        current = key(ordered[mid])
        if current == target:
            return mid
        if current < target:
            return rec(mid + 1, high)
        return rec(low, mid - 1)
    return rec(0, len(ordered) - 1)


# ================================================================
# SUPPORTING ALGORITHMS FROM ORIGINAL PROPOSAL
# ================================================================
def quick_sort(items: list, key: Callable = lambda x: x,
               reverse: bool = False, metrics: Optional[dict] = None) -> list:
    """In-place 3-way partition quicksort on a defensive list copy.

    Median-position pivot; unstable. Expected O(n log n), worst O(n^2).
    Recursion memory expected O(log n), worst O(n).
    """
    a = items[:]
    if metrics is not None:
        metrics.setdefault("comparisons", 0)

    def rec(low, high):
        if low >= high:
            return
        pivot = key(a[(low + high) // 2])
        less, i, more = low, low, high
        while i <= more:
            if metrics is not None:
                metrics["comparisons"] += 1
            k = key(a[i])
            is_less = (k > pivot) if reverse else (k < pivot)
            is_more = (k < pivot) if reverse else (k > pivot)
            if is_less:
                a[less], a[i] = a[i], a[less]
                less += 1; i += 1
            elif is_more:
                a[more], a[i] = a[i], a[more]
                more -= 1
            else:
                i += 1
        # Recurse on the smaller region first; O(log n) pending frames typical.
        if (less - low) < (high - more):
            rec(low, less - 1)
            rec(more + 1, high)
        else:
            rec(more + 1, high)
            rec(low, less - 1)

    rec(0, len(a) - 1)
    return a


def linear_keyword_search(items: list, phrase: str) -> list:
    """Case-insensitive substring scan across the data fields: O(n) records."""
    needle = phrase.casefold().strip()
    if not needle:
        return []
    return [r for r in items if any(needle in str(r.get(f, "")).casefold()
                                     for f in FIELDNAMES if f != "id")]


def baseline_sort(items: list, method: str, key: Callable = lambda x: x,
                  metrics: Optional[dict] = None) -> list:
    """Bubble, insertion and selection sorts used ONLY in performance experiments."""
    a = items[:]
    count = 0
    n = len(a)
    if method == "bubble":
        for last in range(n - 1, 0, -1):
            changed = False
            for j in range(last):
                count += 1
                if key(a[j]) > key(a[j + 1]):
                    a[j], a[j + 1] = a[j + 1], a[j]
                    changed = True
            if not changed:
                break
    elif method == "insertion":
        for i in range(1, n):
            value = a[i]
            j = i - 1
            while j >= 0:
                count += 1
                if key(a[j]) <= key(value):
                    break
                a[j + 1] = a[j]
                j -= 1
            a[j + 1] = value
    elif method == "selection":
        for i in range(n):
            smallest = i
            for j in range(i + 1, n):
                count += 1
                if key(a[j]) < key(a[smallest]):
                    smallest = j
            a[i], a[smallest] = a[smallest], a[i]
    else:
        raise ValueError("Unknown baseline sort: " + method)
    if metrics is not None:
        metrics["comparisons"] = metrics.get("comparisons", 0) + count
    return a


# ================================================================
# CONTACT SYSTEM (array of records + queue + stack + name-index cache)
# ================================================================
class ContactSystem:
    """One-user, in-memory company directory with optional JSON persistence."""

    def __init__(self):
        self.records = []                  # Array/list of record dictionaries
        self.requests = RequestQueue()     # Reused linked FIFO queue from CA2
        self.undo_history = UndoStack()    # Reused LIFO stack from CA2
        self.next_id = 1
        self._name_index = None            # Rebuild after changes; warm O(log n) lookup
        self.last_index_comparisons = 0

    def _invalidate_index(self):
        self._name_index = None

    def _get_index(self):
        if self._name_index is None:
            meter = {}
            self._name_index = merge_sort(
                self.records, key=lambda r: normalize_company(r["company"]),
                metrics=meter,
            )
            self.last_index_comparisons = meter["comparisons"]
        return self._name_index

    def enqueue(self, kind: str, payload: Optional[dict] = None,
                record_id: Optional[int] = None) -> None:
        """Original CA2 enqueue algorithm: stage requests, oldest runs first."""
        if kind not in ("add", "edit", "delete"):
            raise ValueError("Request type must be add, edit, or delete.")
        if kind in ("add", "edit"):
            payload = validate_record(payload or {})
        if kind in ("edit", "delete"):
            if not isinstance(record_id, int) or record_id <= 0:
                raise ValueError("A positive integer record ID is required.")
        self.requests.enqueue({"kind": kind, "payload": payload, "id": record_id})

    def _locate(self, record_id: int) -> int:
        for idx, rec in enumerate(self.records):
            if rec["id"] == record_id:
                return idx
        return -1

    def process_next(self) -> Optional[dict]:
        """Original CA2 FIFO dequeue, followed by one validated CRUD operation.

        The queue is not rolled back by undo; only completed database edits are.
        Invalid/unavailable queued commands return an error without a history item.
        """
        request = self.requests.dequeue()
        if request is None:
            return None
        kind, payload, rid = request["kind"], request["payload"], request["id"]
        if kind == "add":
            record = dict(payload, id=self.next_id)
            self.next_id += 1
            self.records.append(record)
            self.undo_history.push({"kind": "remove", "id": record["id"]})
            self._invalidate_index()
            return {"ok": True, "message": f"Added #{record['id']}: {record['company']}", "id": record["id"]}
        index = self._locate(rid)
        if index < 0:
            return {"ok": False, "message": f"Record #{rid} not found; request skipped."}
        if kind == "edit":
            previous = deepcopy(self.records[index])
            self.records[index] = dict(payload, id=rid)
            self.undo_history.push({"kind": "restore", "record": previous, "index": index})
            self._invalidate_index()
            return {"ok": True, "message": f"Updated record #{rid}."}
        removed = self.records.pop(index)
        self.undo_history.push({"kind": "insert", "record": removed, "index": index})
        self._invalidate_index()
        return {"ok": True, "message": f"Deleted record #{rid}."}

    def process_all(self) -> list:
        outcomes = []
        while len(self.requests):
            outcomes.append(self.process_next())
        return outcomes

    def undo(self) -> str:
        """Reverse exactly the last successful add/edit/delete: LIFO."""
        action = self.undo_history.pop()
        if action is None:
            return "Nothing to undo."
        kind = action["kind"]
        if kind == "remove":
            index = self._locate(action["id"])
            if index >= 0:
                self.records.pop(index)
        elif kind == "restore":
            index = self._locate(action["record"]["id"])
            if index < 0:
                self.records.insert(min(action["index"], len(self.records)), action["record"])
            else:
                self.records[index] = action["record"]
        elif kind == "insert":
            self.records.insert(min(action["index"], len(self.records)), action["record"])
        self._invalidate_index()
        return "Undid last successful database change."

    def view(self, field="company", reverse=False, algorithm="merge") -> list:
        """Return a sorted view; do not disturb canonical insertion/ID order."""
        if field not in ("company", "contact", "industry", "email"):
            raise ValueError("Field must be company, contact, industry, or email.")
        if field == "company":
            key = lambda r: (normalize_company(r["company"]), r["company"].casefold())
        elif field == "industry":
            key = lambda r: (classify_industry(r["industry"], r["company"])[0].casefold(),
                             normalize_company(r["company"]))
        else:
            key = lambda r: (r[field].casefold(), normalize_company(r["company"]))
        if algorithm == "merge":
            return merge_sort(self.records, key=key, reverse=reverse)
        if algorithm == "quick":
            return quick_sort(self.records, key=key, reverse=reverse)
        raise ValueError("Algorithm must be merge or quick.")

    def exact_search(self, company: str, recursive=False) -> list:
        """Warm-cache exact lookup is O(log n + k) for k duplicate matches.

        Cold lookup first builds its sorted index in O(n log n) time.
        """
        target = normalize_company(company)
        if not target:
            return []
        index = self._get_index()
        key = lambda r: normalize_company(r["company"])
        finder = binary_search_recursive if recursive else binary_search_iterative
        pos = finder(index, target, key=key)
        if pos < 0:
            return []
        low = pos
        while low > 0 and key(index[low - 1]) == target:
            low -= 1
        high = pos + 1
        while high < len(index) and key(index[high]) == target:
            high += 1
        return index[low:high]

    def keyword_search(self, keyword: str) -> list:
        return linear_keyword_search(self.records, keyword)

    def duplicate_groups(self) -> list:
        """Merge sort normalized company keys + compare adjacent neighbors."""
        ordered = merge_sort(self.records, key=lambda r: normalize_company(r["company"]))
        groups = []
        i = 0
        while i < len(ordered):
            j = i + 1
            while (j < len(ordered) and
                   normalize_company(ordered[j]["company"]) == normalize_company(ordered[i]["company"])):
                j += 1
            if j - i > 1 and normalize_company(ordered[i]["company"]):
                groups.append(ordered[i:j])
            i = j
        return groups

    def industry_groups(self) -> list:
        """Label-based grouping after stable merge sorting; O(n log n)."""
        ordered = self.view("industry")
        result = []
        for record in ordered:
            label, status = classify_industry(record["industry"], record["company"])
            if not result or result[-1][0] != label:
                result.append((label, []))
            result[-1][1].append((record, status))
        return result

    def review_flags(self) -> list:
        return [(r, *classify_industry(r["industry"], r["company"]))
                for r in self.records
                if "review" in classify_industry(r["industry"], r["company"])[1]]

    def snapshot(self) -> dict:
        return {"schema_version": 1, "records": deepcopy(self.records)}

    def save_json(self, path) -> None:
        """Save committed records to JSON; pending requests/undo intentionally session-only."""
        filename = Path(path)
        filename.parent.mkdir(parents=True, exist_ok=True)
        tmp = filename.with_name(filename.name + ".tmp")
        tmp.write_text(json.dumps(self.snapshot(), indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(filename)

    def load_json(self, path) -> int:
        """Load a prior snapshot (or a JSON list) into a fresh session, atomically."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        rows = data.get("records") if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise ValueError("JSON must contain a records list.")
        clean_rows = []
        seen = set()
        next_candidate = 1
        for original in rows:
            row = validate_record(original)
            candidate = original.get("id")
            # Preserve unique positive integer IDs when present.
            if isinstance(candidate, int) and candidate > 0 and candidate not in seen:
                rid = candidate
            else:
                while next_candidate in seen:
                    next_candidate += 1
                rid = next_candidate
            seen.add(rid)
            clean_rows.append(dict(row, id=rid))
        self.records = clean_rows
        self.next_id = max(seen, default=0) + 1
        self.requests = RequestQueue()
        self.undo_history = UndoStack()
        self._invalidate_index()
        return len(self.records)

    def import_csv(self, path) -> int:
        """Validate all CSV rows first, then append via the same FIFO queue algorithm.

        Accepted headers: company/company_name/organization,
        contact/contact_person/contact_name, industry/industry_type, email, notes.
        If one row is invalid, no row is enqueued or imported.
        """
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV needs a header row.")
            names = {str(k).lower().strip(): k for k in reader.fieldnames}
            def pick(row, *alternatives):
                for option in alternatives:
                    if option in names:
                        return row.get(names[option], "")
                return ""
            prepared = []
            for line, row in enumerate(reader, start=2):
                try:
                    prepared.append(validate_record({
                        "company": pick(row, "company", "company_name", "organization", "organization_name"),
                        "contact": pick(row, "contact", "contact_person", "contact_name", "person"),
                        "industry": pick(row, "industry", "industry_type", "sector"),
                        "email": pick(row, "email", "email_address"),
                        "notes": pick(row, "notes", "remarks"),
                    }))
                except ValueError as exc:
                    raise ValueError(f"CSV line {line}: {exc}") from exc
        # Do not silently execute other pending interactive requests during import.
        if len(self.requests):
            raise ValueError("Process pending requests before importing a CSV.")
        for row in prepared:
            self.enqueue("add", row)
        self.process_all()
        return len(prepared)

    def export_csv(self, path) -> int:
        filename = Path(path)
        filename.parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_EXPORT_FIELDS)
            writer.writeheader()
            for row in self.view("company"):
                label, status = classify_industry(row["industry"], row["company"])
                writer.writerow(dict(row, standardized_industry=label, label_status=status))
        return len(self.records)


# ================================================================
# DEMONSTRATION AND CONSOLE USER INTERFACE
# ================================================================
DEMO_RECORDS = [
    ("Northstar Tech Inc.", "Alex Rivera", "Tech", "alex@northstar.example", "Software partnership"),
    ("Blue Harbor Cafe", "Jamie Cruz", "F&B", "jamie@blueharbor.example", "Campus event"),
    ("Summit Learning Corp.", "Kai Santos", "Education", "kai@summit.example", "Seminar"),
    ("Northstar Technology", "Morgan Lee", "IT", "morgan@northstar.example", "Not necessarily a duplicate"),
    ("Northstar Tech", "Taylor Lim", "Information Technology", "taylor@northstar.example", "Review same-name entry"),
    ("Silverline Bank Co.", "Sam Reyes", "Banking", "sam@silverline.example", "Sponsorship"),
    ("Metro Health Clinic", "Dana Yu", "", "dana@metrohealth.example", "Industry is missing"),
    ("Orbit Media Studio", "Eli Torres", "Media", "eli@orbit.example", "Production"),
    ("Pacific Logistics Ltd.", "Robin Ong", "Logistics", "robin@pacific.example", "Supplier"),
    ("BrightSeed Ventures", "Noel Tan", "Entrepreneurship", "noel@brightseed.example", "Startup community"),
    ("Blue Harbor Cafe Inc", "Casey Navarro", "Food and Beverage", "casey@blueharbor.example", "Potential duplicate"),
    ("Coastal Green Initiative", "Avery Gomez", "Sustainability", "avery@coastal.example", "Needs manual taxonomy review"),
]


def seed_demo(system: ContactSystem) -> None:
    for company, contact, industry, email, notes in DEMO_RECORDS:
        system.enqueue("add", {"company": company, "contact": contact,
                               "industry": industry, "email": email, "notes": notes})
    system.process_all()


def tabulate(records: list, limit: Optional[int] = 25) -> str:
    """Print small readable records table without third-party libraries."""
    display = records if limit is None else records[:limit]
    header = f"{'ID':>4}  {'COMPANY':<29}  {'CONTACT':<19}  {'INDUSTRY LABEL':<22}  STATUS"
    out = [header, "-" * len(header)]
    for row in display:
        label, status = classify_industry(row["industry"], row["company"])
        out.append(f"{row['id']:>4}  {row['company'][:29]:<29}  {row['contact'][:19]:<19}  "
                   f"{label[:22]:<22}  {status}")
    if limit is not None and len(records) > limit:
        out.append(f"... plus {len(records) - limit} more records")
    if not records:
        out.append("(no records)")
    return "\n".join(out)


def run_demo() -> None:
    app = ContactSystem()
    print("=" * 77)
    print("MSYS 30 FINAL PROJECT - FICTIONAL COMPANY CONTACT DEMONSTRATION")
    print("=" * 77)
    print("Enqueue 12 ADD requests, then process oldest first (Coding Assignment 2).")
    seed_demo(app)
    print(f"Processed: {len(app.records)} records; pending queue: {len(app.requests)}")
    print("\nALGORITHM 1 - STABLE MERGE SORT BY COMPANY")
    print(tabulate(app.view("company"), limit=6))
    print("\nALGORITHM 2 - BINARY SEARCH ('blue harbor cafe')")
    print(tabulate(app.exact_search("blue harbor cafe", recursive=True), limit=None))
    print("\nLINEAR KEYWORD SEARCH ('sponsor')")
    print(tabulate(app.keyword_search("sponsor"), limit=None))
    print("\nDUPLICATE-REVIEW GROUPS (normalized name, not automatic deletion)")
    groups = app.duplicate_groups()
    for group in groups:
        print(" - " + " | ".join(f"#{r['id']} {r['company']}" for r in group))
    print("Flagged groups:", len(groups))
    print("\nUNLABELED / UNRECOGNIZED INDUSTRIES")
    for record, label, status in app.review_flags():
        print(f" - #{record['id']}: '{record['industry']}' -> {label} [{status}]")
    print("\nUNDO LAST COMPLETED CHANGE")
    app.enqueue("delete", record_id=2)
    print(app.process_next()["message"])
    print(app.undo())
    print("Record #2 restored:", app._locate(2) >= 0)
    print("\nNo actual organization's private contact database was used.")


def ask_record(existing=None):
    existing = existing or {}
    fields = (("company", "Company name"), ("contact", "Contact person"),
              ("industry", "Industry (may be blank)"), ("email", "Email (may be blank)"),
              ("notes", "Notes (may be blank)"))
    row = {}
    for name, label in fields:
        old = existing.get(name, "")
        hint = f" [{old}]" if old else ""
        raw = input(label + hint + ": ").strip()
        row[name] = raw if raw else old
    return validate_record(row)


def interactive(app, data_path: Path) -> None:
    """Console menu; all changes use the FIFO request-processing flow."""
    if data_path.exists():
        try:
            print(f"Loaded {app.load_json(data_path)} records from {data_path}.")
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            print("Existing data could not be loaded:", exc)
            print("No changes have been made to that file.")
    menu = """
 1. View records                         2. Queue ADD request
 3. Queue EDIT request                   4. Queue DELETE request
 5. Show pending FIFO queue              6. Process NEXT queued request
 7. Process ALL queued requests          8. Undo last completed change
 9. Exact company BINARY SEARCH         10. Keyword LINEAR SEARCH
11. Industry group view                 12. Possible duplicate report
13. Industry labels needing review      14. Import CSV
15. Export CSV                          16. Sorting benchmark
17. Save JSON now                       0. Save and exit
"""
    while True:
        print("\n" + "=" * 77)
        print(f"EXTERNAL RELATIONS CONTACT SYSTEM | {len(app.records)} records | "
              f"{len(app.requests)} queued | {len(app.undo_history)} undo actions")
        print(menu)
        choice = input("Choose: ").strip()
        try:
            if choice == "0":
                app.save_json(data_path)
                print("Saved committed records to", data_path)
                break
            if choice == "1":
                field = input("Sort field [company/contact/industry/email] (default company): ").strip() or "company"
                desc = input("Descending? [y/N]: ").strip().lower() == "y"
                algo = input("Sort algorithm [merge/quick] (default merge): ").strip() or "merge"
                print(tabulate(app.view(field, reverse=desc, algorithm=algo), limit=30))
            elif choice == "2":
                app.enqueue("add", ask_record())
                print("ADD request queued; choose 6 or 7 to apply it.")
            elif choice in ("3", "4"):
                rid = int(input("Record ID: ").strip())
                if choice == "3":
                    pos = app._locate(rid)
                    if pos < 0:
                        print("Not found."); continue
                    app.enqueue("edit", ask_record(app.records[pos]), record_id=rid)
                else:
                    app.enqueue("delete", record_id=rid)
                print("Request queued; choose 6 or 7 to apply it.")
            elif choice == "5":
                for position, request in enumerate(app.requests.to_list(), start=1):
                    print(f"  {position}. {request['kind'].upper()} - "
                          f"ID {request['id'] or '(new)'}")
                if not len(app.requests):
                    print("Queue is empty.")
            elif choice == "6":
                result = app.process_next()
                print(result["message"] if result else "Queue is empty.")
            elif choice == "7":
                results = app.process_all()
                for result in results:
                    print(result["message"])
                if not results:
                    print("Queue is empty.")
            elif choice == "8":
                print(app.undo())
            elif choice == "9":
                name = input("Exact company name: ")
                recur = input("Recursive binary search? [y/N]: ").lower() == "y"
                print(tabulate(app.exact_search(name, recursive=recur), limit=None))
            elif choice == "10":
                print(tabulate(app.keyword_search(input("Search keyword: ")), limit=30))
            elif choice == "11":
                for label, records in app.industry_groups():
                    print(f"\n{label} ({len(records)})")
                    for row, status in records:
                        print(f"  #{row['id']} {row['company']} - {status}")
            elif choice == "12":
                groups = app.duplicate_groups()
                for i, group in enumerate(groups, 1):
                    print(f"Group {i}:", "; ".join(f"#{r['id']} {r['company']}" for r in group))
                print(f"{len(groups)} possible-duplicate group(s), not automatically merged.")
            elif choice == "13":
                for row, label, status in app.review_flags():
                    print(f"#{row['id']} {row['company']}: '{row['industry']}' -> {label} ({status})")
            elif choice == "14":
                path = input("CSV to import: ").strip()
                print(f"Imported {app.import_csv(path)} records.")
            elif choice == "15":
                path = input("CSV export path: ").strip()
                print(f"Exported {app.export_csv(path)} records.")
            elif choice == "16":
                benchmark((100, 300, 600), trials=3)
            elif choice == "17":
                app.save_json(data_path)
                print("Saved to", data_path)
            else:
                print("Choose one of the listed options.")
        except (ValueError, OSError, csv.Error) as exc:
            print("Cannot complete operation:", exc)
        except (EOFError, KeyboardInterrupt):
            print("\nInterrupted. Unsaved changes remain in memory.")
            return


# ================================================================
# REPRODUCIBLE SORTING BENCHMARKS AND COMPLEXITY EVIDENCE
# ================================================================
def benchmark(sizes=(100, 300, 600), trials=5, csv_path=None) -> list:
    """Run every sort on identical shuffled lists for each seed/size.

    Return mean record comparisons + median elapsed milliseconds across trials.
    Machine timings vary. Use comparisons to support scalable asymptotic claims.
    """
    algorithms = ("merge", "quick", "bubble", "insertion", "selection")
    results = []
    print("\nSORTING BENCHMARK (random distinct numeric keys; reproducible seeds)")
    print(f"{'N':>6} {'ALGORITHM':<12} {'MEDIAN MS':>12} {'MEAN COMPARES':>16} {'TRIALS':>8}")
    for n in sizes:
        if n < 0 or n > 5000:
            raise ValueError("Benchmark size must be between 0 and 5,000.")
        raw_samples = []
        for trial in range(trials):
            values = list(range(n))
            random.Random(1009 + n * 13 + trial).shuffle(values)
            raw_samples.append(values)
        for algorithm in algorithms:
            durations = []
            compares = []
            for original in raw_samples:
                stats = {}
                start = time.perf_counter_ns()
                if algorithm == "merge":
                    actual = merge_sort(original, metrics=stats)
                elif algorithm == "quick":
                    actual = quick_sort(original, metrics=stats)
                else:
                    actual = baseline_sort(original, algorithm, metrics=stats)
                elapsed = (time.perf_counter_ns() - start) / 1_000_000
                if actual != sorted(original):
                    raise AssertionError(f"{algorithm} produced an incorrect result")
                durations.append(elapsed)
                compares.append(stats["comparisons"])
            result = {
                "n": n, "algorithm": algorithm,
                "median_ms": round(statistics.median(durations), 4),
                "mean_comparisons": round(statistics.mean(compares), 1),
                "trials": trials,
            }
            results.append(result)
            print(f"{n:>6} {algorithm:<12} {result['median_ms']:>12.4f} "
                  f"{result['mean_comparisons']:>16.1f} {trials:>8}")
    if csv_path:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=tuple(results[0]))
            writer.writeheader()
            writer.writerows(results)
        print("Saved results to", csv_path)
    return results


def benchmark_search(n=10000, queries=1000) -> dict:
    """Compare per-query comparisons in a pre-sorted index vs linear scan.

    Build cost of sorted name index is explicitly excluded and reported separately.
    """
    records = [{"company": f"Company {i:06d}"} for i in range(n)]
    targets = [f"Company {((j * 97) % n):06d}" for j in range(queries)]
    binary_checks = 0
    linear_checks = 0
    for target in targets:
        m = {}
        found = binary_search_iterative(records, target, key=lambda x: x["company"], metrics=m)
        if found < 0:
            raise AssertionError("Binary search test did not find an existing key")
        binary_checks += m["comparisons"]
        for row in records:
            linear_checks += 1
            if row["company"] == target:
                break
    return {"records": n, "queries": queries,
            "binary_comparisons": binary_checks,
            "linear_comparisons": linear_checks,
            "binary_mean": binary_checks / queries,
            "linear_mean": linear_checks / queries}


# ================================================================
# EMBEDDED UNIT/INTEGRATION TESTS; NO EXTRA DEPENDENCIES
# ================================================================
class ContactSystemTests(unittest.TestCase):
    def setUp(self):
        self.app = ContactSystem()
        seed_demo(self.app)

    def test_fifo_order(self):
        q = RequestQueue()
        for letter in "ABC":
            q.enqueue(letter)
        self.assertEqual([q.dequeue(), q.dequeue(), q.dequeue(), q.dequeue()],
                         ["A", "B", "C", None])

    def test_fifo_rear_reset(self):
        q = RequestQueue()
        q.enqueue(1); self.assertEqual(q.dequeue(), 1)
        self.assertIsNone(q.rear)
        q.enqueue(2); self.assertEqual(q.dequeue(), 2)

    def test_stack_last_in_first_out(self):
        stack = UndoStack()
        stack.push(1); stack.push(2)
        self.assertEqual((stack.pop(), stack.pop(), stack.pop()), (2, 1, None))

    def test_merge_sort_and_stability(self):
        rows = [(2, "A"), (1, "B"), (2, "C"), (1, "D")]
        self.assertEqual(merge_sort(rows, key=lambda x: x[0]),
                         [(1, "B"), (1, "D"), (2, "A"), (2, "C")])

    def test_merge_sort_reverse_stability(self):
        rows = [(2, "A"), (1, "B"), (2, "C")]
        self.assertEqual(merge_sort(rows, key=lambda x: x[0], reverse=True),
                         [(2, "A"), (2, "C"), (1, "B")])

    def test_quicksort_correct_with_duplicates(self):
        original = [8, 2, 2, 9, 0, 1, 7, 8, 3]
        self.assertEqual(quick_sort(original), sorted(original))
        self.assertEqual(quick_sort(original, reverse=True), sorted(original, reverse=True))

    def test_all_baselines_correct(self):
        for method in ("bubble", "insertion", "selection"):
            with self.subTest(method=method):
                self.assertEqual(baseline_sort([7, 0, -3, 7, 5], method), [-3, 0, 5, 7, 7])

    def test_binary_search_iterative_hit_miss(self):
        self.assertNotEqual(binary_search_iterative([1, 2, 3], 2), -1)
        self.assertEqual(binary_search_iterative([1, 2, 3], 4), -1)

    def test_binary_search_recursive_hit_miss(self):
        self.assertNotEqual(binary_search_recursive([1, 2, 3], 2), -1)
        self.assertEqual(binary_search_recursive([], 1), -1)

    def test_normalization_suffix_case(self):
        self.assertEqual(normalize_company("  Blue Harbor Cafe, INC. "),
                         normalize_company("blue harbor cafe"))

    def test_distinct_company_name_not_automatically_matched(self):
        self.assertNotEqual(normalize_company("Northstar Technology"),
                            normalize_company("Northstar Tech"))

    def test_csv_label_alias(self):
        self.assertEqual(classify_industry("IT", "Example Co")[0], "Technology")
        self.assertEqual(classify_industry("Tech", "Example Co")[1], "Standardized")

    def test_unknown_industry_flagged_not_overwritten(self):
        label, status = classify_industry("Sustainability", "Unrelated Initiative")
        self.assertEqual(label, "Unclassified")
        self.assertIn("review", status)

    def test_industry_missing_flag(self):
        self.assertIn("review", classify_industry("", "Nondescript Ventures")[1])

    def test_exact_search_and_all_duplicate_names(self):
        self.assertEqual(len(self.app.exact_search("blue harbor cafe")), 2)
        self.assertEqual(len(self.app.exact_search("BLUE HARBOR CAFE, INC.", recursive=True)), 2)
        self.assertEqual(self.app.exact_search("unlisted venture"), [])

    def test_keyword_linear_search(self):
        found = self.app.keyword_search("seminar")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["company"], "Summit Learning Corp.")

    def test_duplicate_report_no_automatic_merge(self):
        groups = self.app.duplicate_groups()
        self.assertEqual(len(groups), 2)
        self.assertTrue(all(len(group) == 2 for group in groups))
        self.assertEqual(len(self.app.records), 12)

    def test_add_delete_undo(self):
        self.app.enqueue("add", {"company": "Test LLC", "contact": "Test Contact"})
        rid = self.app.process_next()["id"]
        self.assertNotEqual(self.app._locate(rid), -1)
        self.app.undo()
        self.assertEqual(self.app._locate(rid), -1)
        self.app.enqueue("delete", record_id=1)
        self.app.process_next()
        self.assertEqual(self.app._locate(1), -1)
        self.app.undo()
        self.assertNotEqual(self.app._locate(1), -1)

    def test_edit_undo_and_index_invalidated(self):
        self.app.exact_search("northstar tech")
        self.app.enqueue("edit", {"company": "Renamed Inc", "contact": "New Person"}, 1)
        self.app.process_next()
        self.assertEqual(len(self.app.exact_search("renamed")), 1)
        self.app.undo()
        self.assertEqual(len(self.app.exact_search("northstar tech")), 2)

    def test_queue_invalid_id_does_not_add_undo(self):
        n = len(self.app.undo_history)
        self.app.enqueue("delete", record_id=999999)
        response = self.app.process_next()
        self.assertFalse(response["ok"])
        self.assertEqual(len(self.app.undo_history), n)

    def test_blank_required_field_rejected(self):
        with self.assertRaises(ValueError):
            self.app.enqueue("add", {"company": "", "contact": "Test"})

    def test_bad_email_rejected(self):
        with self.assertRaises(ValueError):
            validate_record({"company": "A", "contact": "B", "email": "wrong-at-example"})

    def test_csv_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            filename = Path(d) / "output.csv"
            self.assertEqual(self.app.export_csv(filename), 12)
            target = ContactSystem()
            self.assertEqual(target.import_csv(filename), 12)
            self.assertEqual(len(target.records), 12)
            self.assertEqual(len(target.exact_search("blue harbor cafe")), 2)

    def test_bad_csv_import_atomic(self):
        with tempfile.TemporaryDirectory() as d:
            filename = Path(d) / "bad.csv"
            filename.write_text("company,contact,email\nGood,Person,good@example.com\nBad,Person,bad\n")
            before = len(self.app.records)
            with self.assertRaises(ValueError):
                self.app.import_csv(filename)
            self.assertEqual(len(self.app.records), before)
            self.assertEqual(len(self.app.requests), 0)

    def test_json_roundtrip_and_unique_ids(self):
        with tempfile.TemporaryDirectory() as d:
            filename = Path(d) / "contacts.json"
            self.app.save_json(filename)
            copy_app = ContactSystem()
            self.assertEqual(copy_app.load_json(filename), 12)
            self.assertEqual(len(copy_app.exact_search("blue harbor cafe")), 2)
            copy_app.enqueue("add", {"company": "New", "contact": "Person"})
            self.assertGreater(copy_app.process_next()["id"], 12)

    def test_view_sort_does_not_change_storage_order(self):
        original_ids = [r["id"] for r in self.app.records]
        self.app.view("company")
        self.app.view("industry", reverse=True, algorithm="quick")
        self.assertEqual([r["id"] for r in self.app.records], original_ids)

    def test_benchmark_sorts_accurate(self):
        data = [8, 1, 4, 2]
        for algo in ("merge", "quick", "bubble", "insertion", "selection"):
            output = (merge_sort(data) if algo == "merge" else
                      quick_sort(data) if algo == "quick" else baseline_sort(data, algo))
            self.assertEqual(output, sorted(data))

    def test_large_random_sort(self):
        data = list(range(2000))
        random.Random(77).shuffle(data)
        self.assertEqual(merge_sort(data), sorted(data))
        self.assertEqual(quick_sort(data), sorted(data))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--gui", action="store_true", help="Open themed desktop interface (Tkinter)")
    mode.add_argument("--demo", action="store_true", help="Run a safe console demo using fictional records")
    mode.add_argument("--self-test", action="store_true", help="Run the embedded unit/integration tests")
    mode.add_argument("--benchmark", action="store_true", help="Compare five sorting algorithms")
    mode.add_argument("--benchmark-search", action="store_true", help="Compare searching operations")
    parser.add_argument("--data", default="contact_records.json", help="JSON file for interactive persistence")
    parser.add_argument("--benchmark-csv", default=None, help="Optional output CSV for --benchmark")
    parser.add_argument("--gui-demo", action="store_true", help="Seed fictional demo contacts in --gui mode")
    args = parser.parse_args()
    if args.gui:
        try:
            from contact_gui import launch_gui
            launch_gui(args.data, demo=args.gui_demo)
        except (ImportError, RuntimeError) as exc:
            parser.exit(2, f"Cannot launch GUI: {exc}\nInstall Python with Tkinter and use a desktop display.\n")
    elif args.gui_demo:
        parser.error("--gui-demo must be combined with --gui")
    elif args.demo:
        run_demo()
    elif args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(ContactSystemTests))
        sys.exit(0 if result.wasSuccessful() else 1)
    elif args.benchmark:
        benchmark(csv_path=args.benchmark_csv)
    elif args.benchmark_search:
        print("BINARY VERSUS LINEAR SEARCH (sorted index build excluded)")
        for k, v in benchmark_search().items():
            print(f"{k}: {v}")
    else:
        interactive(ContactSystem(), Path(args.data))


if __name__ == "__main__":
    main()
