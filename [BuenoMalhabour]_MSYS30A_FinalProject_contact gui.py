"""Accessible Tkinter desktop interface for the MSYS 30 Contact Management System.

Requires Python 3 with Tkinter (included in common desktop Python installs).
All record changes go through ContactSystem's existing FIFO queue. This module
only presents data and handles user interaction; it does not reimplement sorts.
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from MSYS30_External_Relations_Contact_System import (
    ContactSystem, classify_industry, benchmark, normalize_company, seed_demo,
)

# Color swatches supplied for the final project: navy, plum, mauve, coral, peach.
NAVY = '#0e3b5c'
PLUM = '#5e4f6d'
MAUVE = '#9f6671'
CORAL = '#d8897b'
PEACH = '#f4ac7b'
WHITE = '#ffffff'
INK = '#243649'
MUTED = '#607287'
PALE = '#f6f3f5'
BORDER = '#e5e0e7'


class RecordDialog(tk.Toplevel):
    """Modal, validated editor; queues the request without applying it."""
    FIELDS = (('company', 'Company *'), ('contact', 'Contact person *'),
              ('industry', 'Industry'), ('email', 'Email'), ('notes', 'Notes'))

    def __init__(self, parent, current=None):
        super().__init__(parent)
        self.result = None
        self.title('Edit contact' if current else 'Add company contact')
        self.configure(bg=PALE)
        self.resizable(False, False)
        self.transient(parent)
        self.inputs = {}
        wrapper = tk.Frame(self, bg=PALE, padx=24, pady=22)
        wrapper.pack(fill='both', expand=True)
        tk.Label(wrapper, text='Contact details', bg=PALE, fg=NAVY,
                 font=('Segoe UI', 16, 'bold')).grid(row=0, column=0, columnspan=2,
                                                  sticky='w', pady=(0, 14))
        for index, (field, title) in enumerate(self.FIELDS, 1):
            tk.Label(wrapper, text=title, bg=PALE, fg=INK,
                     font=('Segoe UI', 10)).grid(row=index, column=0, sticky='w', pady=7)
            value = tk.StringVar(value=(current or {}).get(field, ''))
            entry = ttk.Entry(wrapper, textvariable=value, width=42)
            entry.grid(row=index, column=1, sticky='ew', padx=(16, 0), pady=7)
            self.inputs[field] = value
            if index == 1:
                entry.focus_set()
        tk.Label(wrapper, text='* Required. Requests are staged until processed.',
                 bg=PALE, fg=MUTED, font=('Segoe UI', 9)).grid(
                     row=6, column=0, columnspan=2, sticky='w', pady=(10, 8))
        buttons = tk.Frame(wrapper, bg=PALE)
        buttons.grid(row=7, column=0, columnspan=2, sticky='e', pady=(10, 0))
        ttk.Button(buttons, text='Cancel', command=self.destroy).pack(side='left', padx=6)
        ttk.Button(buttons, text='Queue request', style='Accent.TButton',
                   command=self._submit).pack(side='left')
        self.bind('<Escape>', lambda _: self.destroy())
        self.bind('<Return>', lambda _: self._submit())
        self.grab_set()
        self.wait_window()

    def _submit(self):
        from MSYS30_External_Relations_Contact_System import validate_record
        try:
            self.result = validate_record({key: variable.get()
                                           for key, variable in self.inputs.items()})
        except ValueError as exc:
            messagebox.showerror('Check contact details', str(exc), parent=self)
            return
        self.destroy()


class ContactDashboard:
    """Single-user dashboard with keyboard-friendly CRUD, search and reports."""

    def __init__(self, root, data_path='contact_records.json', demo=False):
        self.root = root
        self.data_path = Path(data_path)
        self.app = ContactSystem()
        self.unsaved = False
        self.current_view = 'all'
        self.root.title('ContactFlow | External Relations')
        self.root.geometry('1190x760')
        self.root.minsize(900, 600)
        self.root.configure(bg=PALE)
        self._style()
        self._layout()
        if demo:
            seed_demo(self.app)
            self.unsaved = True
            self._notify('Demo loaded with 12 fictional contacts. Save to retain changes.')
        elif self.data_path.exists():
            try:
                count = self.app.load_json(self.data_path)
                self._notify(f'Loaded {count} records from {self.data_path.name}.')
            except (ValueError, OSError) as exc:
                messagebox.showerror('Data file was not loaded', str(exc), parent=self.root)
        self.refresh()
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.bind('<Control-s>', lambda _: self.save())
        self.root.bind('<Control-n>', lambda _: self.add_record())
        self.root.bind('<Control-z>', lambda _: self.undo())
        self.root.bind('<Control-f>', lambda _: self.search_entry.focus_set())
        self.root.bind('<Delete>', lambda _: self.delete_record())

    def _style(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('TFrame', background=PALE)
        style.configure('TLabel', background=PALE, foreground=INK,
                        font=('Segoe UI', 10))
        style.configure('TEntry', padding=7)
        style.configure('TCombobox', padding=5)
        style.configure('TButton', font=('Segoe UI', 10), padding=(12, 8),
                        background=WHITE, foreground=NAVY, bordercolor=BORDER)
        style.map('TButton', background=[('active', '#ece7ee')])
        style.configure('Accent.TButton', background=CORAL, foreground=NAVY,
                        bordercolor=CORAL, font=('Segoe UI', 10, 'bold'))
        style.map('Accent.TButton', background=[('active', PEACH)])
        style.configure('Treeview', rowheight=35, font=('Segoe UI', 10),
                        background=WHITE, foreground=INK, fieldbackground=WHITE,
                        bordercolor=BORDER)
        style.configure('Treeview.Heading', background=PLUM, foreground=WHITE,
                        relief='flat', font=('Segoe UI', 10, 'bold'))
        style.map('Treeview', background=[('selected', MAUVE)],
                  foreground=[('selected', WHITE)])
        style.configure('TNotebook', background=PALE, borderwidth=0)
        style.configure('TNotebook.Tab', font=('Segoe UI', 10, 'bold'),
                        padding=(18, 10), background='#e8e1e9', foreground=NAVY)
        style.map('TNotebook.Tab', background=[('selected', WHITE)])

    def _nav_button(self, parent, text, action):
        button = tk.Button(parent, text=text, command=action, anchor='w',
                           font=('Segoe UI', 11), fg=WHITE, bg=NAVY,
                           activebackground=PLUM, activeforeground=WHITE,
                           borderwidth=0, padx=20, pady=11, cursor='hand2')
        button.pack(fill='x', padx=10, pady=3)
        return button

    def _layout(self):
        rail = tk.Frame(self.root, bg=NAVY, width=218)
        rail.pack(side='left', fill='y')
        rail.pack_propagate(False)
        tk.Label(rail, text='CONTACTFLOW', bg=NAVY, fg=PEACH,
                 font=('Segoe UI', 18, 'bold')).pack(anchor='w', padx=22, pady=(29, 1))
        tk.Label(rail, text='EXTERNAL RELATIONS', bg=NAVY, fg=WHITE,
                 font=('Segoe UI', 9)).pack(anchor='w', padx=22, pady=(0, 30))
        for label, callback in (
            ('All contacts', lambda: self.show_view('all')),
            ('Industry groups', lambda: self.show_view('industry')),
            ('Possible duplicates', lambda: self.show_view('duplicates')),
            ('Review labels', lambda: self.show_view('review')),
            ('Pending requests', lambda: self.tabs.select(self.queue_tab)),
            ('Algorithm lab', lambda: self.tabs.select(self.lab_tab)),
        ):
            self._nav_button(rail, label, callback)
        tk.Label(rail, text='MSYS 30  •  Data Structures', bg=NAVY, fg='#ddd0e1',
                 font=('Segoe UI', 9), wraplength=180).pack(
                     side='bottom', padx=16, pady=22)
        content = tk.Frame(self.root, bg=PALE, padx=24, pady=20)
        content.pack(side='left', fill='both', expand=True)
        tk.Label(content, text='Company contacts', fg=NAVY, bg=PALE,
                 font=('Segoe UI', 24, 'bold')).pack(anchor='w')
        tk.Label(content, text='Organize partnerships, standardize industries, and find contacts faster.',
                 fg=MUTED, bg=PALE, font=('Segoe UI', 10)).pack(anchor='w', pady=(1, 16))
        stats = tk.Frame(content, bg=PALE)
        stats.pack(fill='x', pady=(0, 12))
        self.stats = {}
        for index, (name, color) in enumerate((('Contacts', NAVY), ('Queued', PLUM),
                                               ('Possible duplicates', MAUVE),
                                               ('Labels to review', CORAL))):
            card = tk.Frame(stats, bg=WHITE, highlightbackground=BORDER,
                            highlightthickness=1, padx=13, pady=11)
            card.grid(row=0, column=index, sticky='nsew', padx=(0, 10 if index < 3 else 0))
            stats.grid_columnconfigure(index, weight=1)
            tk.Label(card, text=name, bg=WHITE, fg=MUTED,
                     font=('Segoe UI', 9)).pack(anchor='w')
            v = tk.Label(card, text='0', bg=WHITE, fg=color,
                         font=('Segoe UI', 21, 'bold'))
            v.pack(anchor='w')
            self.stats[name] = v
        toolbar = tk.Frame(content, bg=PALE)
        toolbar.pack(fill='x', pady=(0, 12))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=27)
        self.search_entry.pack(side='left', padx=(0, 7))
        self.search_entry.bind('<Return>', lambda _: self.search())
        self.search_type = tk.StringVar(value='Keyword (linear)')
        ttk.Combobox(toolbar, state='readonly', width=19, textvariable=self.search_type,
                     values=('Keyword (linear)', 'Exact company (binary)')).pack(side='left', padx=4)
        ttk.Button(toolbar, text='Search', command=self.search).pack(side='left', padx=4)
        ttk.Button(toolbar, text='Clear', command=self.reset_search).pack(side='left', padx=4)
        ttk.Button(toolbar, text='+ Add contact', style='Accent.TButton',
                   command=self.add_record).pack(side='right')
        self.tabs = ttk.Notebook(content)
        self.tabs.pack(fill='both', expand=True)
        self.records_tab = ttk.Frame(self.tabs)
        self.queue_tab = ttk.Frame(self.tabs)
        self.lab_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.records_tab, text='Directory')
        self.tabs.add(self.queue_tab, text='Request queue')
        self.tabs.add(self.lab_tab, text='Algorithm lab')
        self._records_layout()
        self._queue_layout()
        self._lab_layout()
        bottom = tk.Frame(content, bg=PALE)
        bottom.pack(fill='x', pady=(12, 0))
        for text, cmd in (('Import CSV', self.import_csv), ('Export CSV', self.export_csv),
                          ('Save (Ctrl+S)', self.save)):
            ttk.Button(bottom, text=text, command=cmd).pack(side='left', padx=(0, 8))
        self.status = tk.Label(bottom, bg=PALE, fg=MUTED, anchor='e',
                               font=('Segoe UI', 9), wraplength=500)
        self.status.pack(side='right', fill='x', expand=True)

    def _records_layout(self):
        bar = tk.Frame(self.records_tab, bg=PALE)
        bar.pack(fill='x', pady=(12, 8))
        self.view_heading = tk.Label(bar, text='All contacts', bg=PALE, fg=NAVY,
                                     font=('Segoe UI', 13, 'bold'))
        self.view_heading.pack(side='left')
        self.reverse = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text='Descending', variable=self.reverse,
                        command=self.refresh).pack(side='right', padx=6)
        self.sort_algorithm = tk.StringVar(value='merge')
        ttk.Combobox(bar, state='readonly', width=8, textvariable=self.sort_algorithm,
                     values=('merge', 'quick')).pack(side='right', padx=5)
        self.sort_field = tk.StringVar(value='company')
        ttk.Combobox(bar, state='readonly', width=12, textvariable=self.sort_field,
                     values=('company', 'contact', 'industry', 'email')).pack(side='right', padx=5)
        ttk.Button(bar, text='Apply sort', command=self.reset_search).pack(side='right', padx=5)
        frame = tk.Frame(self.records_tab, bg=PALE)
        frame.pack(fill='both', expand=True)
        columns = ('id', 'company', 'contact', 'industry', 'email', 'status')
        self.table = ttk.Treeview(frame, columns=columns, show='headings', selectmode='browse')
        widths = (54, 200, 142, 120, 178, 128)
        for field, width in zip(columns, widths):
            self.table.heading(field, text=field.replace('_', ' ').title())
            self.table.column(field, width=width, minwidth=55, stretch=field != 'id')
        scroller = ttk.Scrollbar(frame, orient='vertical', command=self.table.yview)
        self.table.configure(yscrollcommand=scroller.set)
        self.table.pack(side='left', fill='both', expand=True)
        scroller.pack(side='right', fill='y')
        self.table.bind('<Double-1>', lambda _: self.edit_record())
        actions = tk.Frame(self.records_tab, bg=PALE)
        actions.pack(fill='x', pady=(10, 0))
        ttk.Button(actions, text='Edit selected', command=self.edit_record).pack(side='left', padx=(0, 7))
        ttk.Button(actions, text='Queue deletion', command=self.delete_record).pack(side='left')
        ttk.Button(actions, text='Undo last change', command=self.undo).pack(side='right')

    def _queue_layout(self):
        tk.Label(self.queue_tab, text='FIFO request processing', bg=PALE, fg=NAVY,
                 font=('Segoe UI', 15, 'bold')).pack(anchor='w', pady=(16, 5))
        tk.Label(self.queue_tab, text='Edits are queued first. The oldest request executes first; undo reverses the newest completed change.',
                 bg=PALE, fg=MUTED, wraplength=700).pack(anchor='w', pady=(0, 12))
        self.queue_table = ttk.Treeview(self.queue_tab, columns=('position', 'operation', 'id', 'company'),
                                        show='headings', height=11)
        for col, width in (('position', 90), ('operation', 120), ('id', 100), ('company', 350)):
            self.queue_table.heading(col, text=col.title())
            self.queue_table.column(col, width=width)
        self.queue_table.pack(fill='both', expand=True)
        row = tk.Frame(self.queue_tab, bg=PALE)
        row.pack(fill='x', pady=14)
        ttk.Button(row, text='Process next', style='Accent.TButton',
                   command=self.process_next).pack(side='left', padx=(0, 8))
        ttk.Button(row, text='Process all', command=self.process_all).pack(side='left')
        ttk.Button(row, text='Undo last change', command=self.undo).pack(side='right')

    def _lab_layout(self):
        tk.Label(self.lab_tab, text='Algorithms & complexity', bg=PALE, fg=NAVY,
                 font=('Segoe UI', 15, 'bold')).pack(anchor='w', pady=(16, 10))
        details = (
            'Merge sort  ·  O(n log n) time, O(n) extra space  ·  primary stable directory sort\n\n'
            'Binary search  ·  O(log n) warm-cache lookup, O(1) iterative space  ·  exact company match\n\n'
            'Linked FIFO queue  ·  O(1) enqueue/dequeue pointer work  ·  preserves request order\n\n'
            'LIFO stack  ·  O(1) push/pop for bounded history entries  ·  undo completed changes\n\n'
            'Quick sort  ·  O(n log n) average, O(n²) worst  ·  alternative directory sort\n\n'
            'Linear search  ·  O(n)  ·  keyword matching across fields\n\n'
            'Bubble / insertion / selection  ·  O(n²) average/worst  ·  benchmark baselines\n\n'
            'Exact lookup builds a sorted index in O(n log n) on first use or after edits.\n'
            'Benchmark times depend on the computer and dataset; see CSV results.'
        )
        tk.Label(self.lab_tab, text=details, justify='left', bg=WHITE, fg=INK,
                 font=('Segoe UI', 10), padx=20, pady=20, anchor='nw',
                 wraplength=780).pack(fill='x', pady=(0, 12))
        ttk.Button(self.lab_tab, text='Run sorting benchmark (100–600 records)',
                   style='Accent.TButton', command=self.run_benchmark).pack(anchor='w')

    def _notify(self, message):
        if hasattr(self, 'status'):
            self.status.configure(text=message)

    def _selected(self):
        selection = self.table.selection()
        if not selection:
            messagebox.showinfo('Select a record', 'Select a row from the directory first.',
                                parent=self.root)
            return None
        record_id = int(self.table.item(selection[0], 'values')[0])
        index = self.app._locate(record_id)
        return self.app.records[index] if index >= 0 else None

    def refresh(self, rows=None, heading=None):
        if rows is None:
            if self.current_view == 'duplicates':
                ids = {r['id'] for group in self.app.duplicate_groups() for r in group}
                rows = [r for r in self.app.view(self.sort_field.get(), self.reverse.get(), self.sort_algorithm.get())
                        if r['id'] in ids]
                heading = 'Possible duplicates • manual review only'
            elif self.current_view == 'review':
                ids = {r['id'] for r, _, _ in self.app.review_flags()}
                rows = [r for r in self.app.view(self.sort_field.get(), self.reverse.get(), self.sort_algorithm.get())
                        if r['id'] in ids]
                heading = 'Unlabeled / unrecognized industries'
            else:
                rows = self.app.view(self.sort_field.get(), self.reverse.get(), self.sort_algorithm.get())
                heading = 'Grouped by industry' if self.current_view == 'industry' else 'All contacts'
                if self.current_view == 'industry':
                    rows = self.app.view('industry', self.reverse.get(), 'merge')
        self.view_heading.configure(text=heading or 'Search results')
        self.table.delete(*self.table.get_children())
        for rec in rows:
            label, status = classify_industry(rec['industry'], rec['company'])
            self.table.insert('', 'end', values=(rec['id'], rec['company'], rec['contact'],
                                                 label, rec['email'], status))
        self.queue_table.delete(*self.queue_table.get_children())
        for n, req in enumerate(self.app.requests.to_list(), 1):
            company = (req.get('payload') or {}).get('company', '')
            self.queue_table.insert('', 'end', values=(n, req['kind'].upper(), req.get('id') or 'New', company))
        for field, value in (('Contacts', len(self.app.records)), ('Queued', len(self.app.requests)),
                             ('Possible duplicates', len(self.app.duplicate_groups())),
                             ('Labels to review', len(self.app.review_flags()))):
            self.stats[field].configure(text=str(value))

    def show_view(self, view):
        self.current_view = view
        self.tabs.select(self.records_tab)
        self.refresh()

    def search(self):
        phrase = self.search_var.get().strip()
        if not phrase:
            messagebox.showinfo('Search', 'Enter a company name or keyword.', parent=self.root)
            return
        if self.search_type.get().startswith('Exact'):
            rows = self.app.exact_search(phrase)
            description = 'Binary search (exact normalized company name)'
        else:
            rows = self.app.keyword_search(phrase)
            description = 'Linear keyword search'
        self.current_view = 'all'
        self.refresh(rows=rows, heading=f'{description} • {len(rows)} result(s)')
        self.tabs.select(self.records_tab)
        self._notify(f'{len(rows)} result(s) for “{phrase}”.')

    def reset_search(self):
        self.search_var.set('')
        self.current_view = 'all'
        self.refresh()

    def add_record(self):
        dialog = RecordDialog(self.root)
        if dialog.result:
            self.app.enqueue('add', dialog.result)
            self.refresh()
            self.tabs.select(self.queue_tab)
            self._notify('ADD queued. Process next/all to apply changes.')

    def edit_record(self):
        rec = self._selected()
        if rec is None:
            return
        dialog = RecordDialog(self.root, rec)
        if dialog.result:
            self.app.enqueue('edit', dialog.result, record_id=rec['id'])
            self.refresh()
            self.tabs.select(self.queue_tab)
            self._notify(f'EDIT #{rec["id"]} queued.')

    def delete_record(self):
        rec = self._selected()
        if rec and messagebox.askyesno('Queue deletion',
                                      f'Queue deletion of “{rec["company"]}”?\nIt will not be deleted until processed.',
                                      parent=self.root):
            self.app.enqueue('delete', record_id=rec['id'])
            self.refresh()
            self.tabs.select(self.queue_tab)
            self._notify(f'DELETE #{rec["id"]} queued.')

    def process_next(self):
        outcome = self.app.process_next()
        if outcome is None:
            self._notify('The request queue is empty.')
        else:
            self.unsaved = self.unsaved or outcome['ok']
            self._notify(outcome['message'])
            if not outcome['ok']:
                messagebox.showwarning('Request skipped', outcome['message'], parent=self.root)
        self.refresh()

    def process_all(self):
        outcomes = self.app.process_all()
        if not outcomes:
            self._notify('The request queue is empty.')
        else:
            self.unsaved = self.unsaved or any(x['ok'] for x in outcomes)
            errors = [x['message'] for x in outcomes if not x['ok']]
            self._notify(f'Processed {len(outcomes)} requests ({len(errors)} skipped).')
            if errors:
                messagebox.showwarning('Some requests were skipped', '\n'.join(errors[:10]), parent=self.root)
        self.refresh()

    def undo(self):
        result = self.app.undo()
        if result.startswith('Undid'):
            self.unsaved = True
        self._notify(result)
        self.refresh()

    def import_csv(self):
        path = filedialog.askopenfilename(title='Import contacts CSV',
                                          filetypes=[('CSV files', '*.csv')], parent=self.root)
        if not path:
            return
        try:
            count = self.app.import_csv(path)
            self.unsaved = self.unsaved or count > 0
            self.refresh()
            self._notify(f'Imported {count} records from {Path(path).name}.')
        except (ValueError, OSError) as exc:
            messagebox.showerror('Import failed; nothing imported', str(exc), parent=self.root)

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension='.csv',
                                            filetypes=[('CSV files', '*.csv')],
                                            title='Export contacts CSV', parent=self.root)
        if path:
            try:
                count = self.app.export_csv(path)
                self._notify(f'Exported {count} contacts to {Path(path).name}.')
            except (OSError, ValueError) as exc:
                messagebox.showerror('Export failed', str(exc), parent=self.root)

    def save(self):
        if len(self.app.requests):
            messagebox.showwarning('Pending requests',
                                   'Process or review queued changes before saving.\nOnly completed changes are saved.',
                                   parent=self.root)
            return False
        try:
            self.app.save_json(self.data_path)
            self.unsaved = False
            self._notify(f'Saved {len(self.app.records)} contacts to {self.data_path}.')
            return True
        except OSError as exc:
            messagebox.showerror('Save failed', str(exc), parent=self.root)
            return False

    def run_benchmark(self):
        try:
            report = benchmark(sizes=(100, 300, 600), trials=3)
            messagebox.showinfo('Benchmark complete',
                                f'Completed {len(report)} benchmark rows.\n'
                                'Results are printed in the launch terminal.\n'
                                'Use --benchmark-csv for export.', parent=self.root)
        except Exception as exc:
            messagebox.showerror('Benchmark error', str(exc), parent=self.root)

    def close(self):
        if len(self.app.requests) and not messagebox.askyesno(
                'Pending requests', 'Queued changes have not been processed and will be lost. Exit?',
                parent=self.root):
            return
        if self.unsaved:
            result = messagebox.askyesnocancel('Save changes?',
                                               'Save completed changes before exiting?', parent=self.root)
            if result is None:
                return
            if result and not self.save():
                return
        self.root.destroy()


def launch_gui(data_path='contact_records.json', demo=False):
    """Start GUI only on demand; importing this module never opens a window."""
    root = tk.Tk()
    ContactDashboard(root, data_path=data_path, demo=demo)
    root.mainloop()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='ContactFlow desktop GUI')
    parser.add_argument('--data', default='contact_records.json')
    parser.add_argument('--demo', action='store_true')
    args = parser.parse_args()
    launch_gui(args.data, args.demo)
