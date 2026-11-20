import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from importlib import import_module
import sys
_gui = import_module("[BuenoMalhabour]_MSYS30A_FinalProject_contact gui")
sys.modules["contact_gui"] = _gui  # Keep existing mock.patch targets usable.
ContactDashboard = _gui.ContactDashboard


class GuiSmokeTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.data = Path(self.tempdir.name) / 'contacts.json'
        self.root = tk.Tk()
        self.dashboard = ContactDashboard(self.root, self.data, demo=True)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.tempdir.cleanup()

    def test_demo_and_binary_search(self):
        self.assertEqual(len(self.dashboard.table.get_children()), 12)
        self.dashboard.search_var.set('blue harbor cafe')
        self.dashboard.search_type.set('Exact company (binary)')
        self.dashboard.search()
        self.assertEqual(len(self.dashboard.table.get_children()), 2)

    def test_fifo_undo_and_persistence(self):
        self.dashboard.app.enqueue('add', {'company':'Test Alpha','contact':'Test Person'})
        self.dashboard.app.enqueue('delete', record_id=1)
        self.dashboard.process_next()
        self.assertEqual(len(self.dashboard.app.records), 13)
        self.dashboard.process_next()
        self.assertEqual(len(self.dashboard.app.records), 12)
        self.dashboard.undo()
        self.assertEqual(len(self.dashboard.app.records), 13)
        self.assertTrue(self.dashboard.save())
        loaded = ContactDashboard(tk.Toplevel(self.root), self.data)
        self.assertEqual(len(loaded.app.records), 13)
        loaded.root.destroy()

    def test_queue_blocks_save_and_bad_csv_import_atomic(self):
        self.dashboard.app.enqueue('add', {'company':'Queued','contact':'Person'})
        with patch('contact_gui.messagebox.showwarning') as mocked:
            self.assertFalse(self.dashboard.save())
            mocked.assert_called_once()
        self.assertFalse(self.data.exists())
        self.dashboard.process_next()
        bad = Path(self.tempdir.name) / 'bad.csv'
        bad.write_text('company,contact\nGood,Person\nBad,\n', encoding='utf-8')
        before = len(self.dashboard.app.records)
        with patch('contact_gui.filedialog.askopenfilename', return_value=str(bad)):
            with patch('contact_gui.messagebox.showerror') as mocked:
                self.dashboard.import_csv()
                mocked.assert_called_once()
        self.assertEqual(len(self.dashboard.app.records), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
