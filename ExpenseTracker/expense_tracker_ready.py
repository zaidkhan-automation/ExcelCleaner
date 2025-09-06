# expense_tracker_ready.py
import os
import csv
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import json
import traceback
import sys

# -> try to import matplotlib (optional). If missing, disable charts gracefully.
try:
    import matplotlib.pyplot as plt
    PLOTTING_AVAILABLE = True
except Exception:
    plt = None
    PLOTTING_AVAILABLE = False

# Put files next to this script, not dependent on current working dir
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

APP_NAME = "ExpenseTracker"
DATA_FILE = os.path.join(BASE_DIR, "expenses.csv")
LOG_FILE = os.path.join(BASE_DIR, "tracker_log.txt")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULT_CATEGORIES = ["Food", "Transport", "Rent", "Utilities", "Shopping", "Health", "Other"]

# ---- Utilities ----
def log(msg):
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{t}] {msg}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        # If logging fails, print to console so we can debug
        print("LOG WRITE FAILED:", line)

def ensure_files():
    try:
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["date", "category", "amount", "note"])
            log("Created new data file.")
        os.makedirs(BACKUP_DIR, exist_ok=True)
        if not os.path.exists(CONFIG_FILE):
            cfg = {"categories": DEFAULT_CATEGORIES}
            with open(CONFIG_FILE, "w", encoding='utf-8') as f:
                json.dump(cfg, f, indent=2)
            log("Created default config file.")
    except Exception as e:
        print("Error ensuring files:", e)
        log(f"Error ensuring files: {e}")

def read_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"categories": DEFAULT_CATEGORIES}

def backup_data():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"expenses_backup_{ts}.csv")
    try:
        shutil.copy2(DATA_FILE, dest)
        log(f"Backup created: {dest}")
        return dest
    except Exception as e:
        log(f"Backup failed: {e}")
        return None

def add_expense_row(date, category, amount, note):
    try:
        with open(DATA_FILE, "a", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([date, category, amount, note])
        log(f"Added expense: {date}, {category}, {amount}, {note}")
    except Exception as e:
        log(f"Add failed: {e}")
        raise

def read_expenses():
    rows = []
    if not os.path.exists(DATA_FILE):
        return rows
    try:
        with open(DATA_FILE, "r", newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
    except Exception as e:
        log(f"Read expenses failed: {e}")
    return rows

def import_csv(path):
    try:
        with open(path, "r", newline='', encoding='utf-8') as fr, open(DATA_FILE, "a", newline='', encoding='utf-8') as fw:
            reader = csv.reader(fr)
            writer = csv.writer(fw)
            first = True
            for row in reader:
                if first:
                    first = False
                    if row and row[0].lower().strip() == "date":
                        continue
                if len(row) >= 3:
                    # ensure 4 columns
                    while len(row) < 4:
                        row.append("")
                    writer.writerow(row[:4])
        log(f"Imported CSV: {path}")
        return True
    except Exception as e:
        log(f"Import failed: {e}")
        return False

# ---- GUI App ----
class ExpenseApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("900x520")
        cfg = read_config()
        self.categories = cfg.get("categories", DEFAULT_CATEGORIES)

        # Left panel: inputs
        left = tk.Frame(root, padx=10, pady=10)
        left.pack(side="left", fill="y")

        tk.Label(left, text="Date (YYYY-MM-DD)").pack(anchor='w')
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        tk.Entry(left, textvariable=self.date_var, width=22).pack()

        tk.Label(left, text="Category").pack(anchor='w', pady=(8,0))
        self.cat_var = tk.StringVar(value=self.categories[0] if self.categories else "")
        self.cat_combo = ttk.Combobox(left, textvariable=self.cat_var, values=self.categories, width=20)
        self.cat_combo.pack()

        tk.Label(left, text="Amount").pack(anchor='w', pady=(8,0))
        self.amt_var = tk.StringVar()
        tk.Entry(left, textvariable=self.amt_var, width=22).pack()

        tk.Label(left, text="Note").pack(anchor='w', pady=(8,0))
        self.note_var = tk.StringVar()
        tk.Entry(left, textvariable=self.note_var, width=22).pack()

        tk.Button(left, text="Add Expense", width=20, command=self.on_add).pack(pady=(12,6))
        tk.Button(left, text="Backup Data", width=20, command=self.on_backup).pack(pady=4)
        tk.Button(left, text="Import CSV", width=20, command=self.on_import).pack(pady=4)
        tk.Button(left, text="Export CSV", width=20, command=self.on_export).pack(pady=4)

        # Chart button: disabled if matplotlib not available
        self.chart_btn = tk.Button(left, text="Show Summary Chart", width=20, command=self.on_summary)
        if not PLOTTING_AVAILABLE:
            self.chart_btn.config(state="disabled", text="Chart (install matplotlib)")
        self.chart_btn.pack(pady=6)

        tk.Label(left, text="Settings:", pady=10).pack(anchor='w')
        tk.Button(left, text="Edit Categories", width=20, command=self.edit_categories).pack(pady=2)

        # Right panel: table and search
        right = tk.Frame(root, padx=10, pady=10)
        right.pack(side="right", fill="both", expand=True)

        top_search = tk.Frame(right)
        top_search.pack(fill="x", pady=(0,6))
        tk.Label(top_search, text="Search").pack(side="left")
        self.search_var = tk.StringVar()
        tk.Entry(top_search, textvariable=self.search_var, width=30).pack(side="left", padx=6)
        tk.Button(top_search, text="Go", command=self.on_search).pack(side="left")
        tk.Button(top_search, text="Clear", command=self.refresh_table).pack(side="left", padx=6)

        cols = ("date","category","amount","note")
        self.tree = ttk.Treeview(right, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c.capitalize(), command=lambda _c=c: self.sort_by(_c, False))
            self.tree.column(c, anchor='w', width=120)
        self.tree.pack(fill="both", expand=True)

        vsb = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")

        # load data
        self.refresh_table()

    def on_add(self):
        d = self.date_var.get().strip()
        c = self.cat_var.get().strip()
        a = self.amt_var.get().strip()
        n = self.note_var.get().strip()
        if not d or not c or not a:
            messagebox.showwarning("Missing", "Please enter date, category and amount.")
            return
        try:
            float(a)
        except:
            messagebox.showerror("Invalid", "Amount must be a number.")
            return
        try:
            add_expense_row(d, c, a, n)
        except Exception as e:
            messagebox.showerror("Error", f"Couldn't add expense: {e}")
            return
        self.refresh_table()
        self.amt_var.set(""); self.note_var.set("")
        messagebox.showinfo("Added", "Expense added successfully.")

    def refresh_table(self, filtered_rows=None):
        for i in self.tree.get_children():
            self.tree.delete(i)
        rows = filtered_rows if filtered_rows is not None else read_expenses()
        for r in rows:
            self.tree.insert("", "end", values=(r.get('date',''), r.get('category',''), r.get('amount',''), r.get('note','')))

    def on_backup(self):
        path = backup_data()
        if path:
            messagebox.showinfo("Backup", f"Backup created:\n{path}")
        else:
            messagebox.showerror("Backup", "Backup failed. See log.")

    def on_import(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files",".csv"), ("All files",".*")])
        if path:
            ok = import_csv(path)
            if ok:
                self.refresh_table()
                messagebox.showinfo("Import", "CSV imported successfully.")
            else:
                messagebox.showerror("Import", "Import failed. See log.")

    def on_export(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV files","*.csv")])
        if path:
            rows = read_expenses()
            try:
                with open(path, "w", newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=["date","category","amount","note"])
                    writer.writeheader()
                    for r in rows:
                        writer.writerow(r)
                log(f"Exported CSV: {path}")
                messagebox.showinfo("Exported", f"Exported to {path}")
            except Exception as e:
                log(f"Export failed: {e}")
                messagebox.showerror("Export failed", str(e))

    def on_summary(self):
        if not PLOTTING_AVAILABLE:
            messagebox.showinfo("Not available", "Charts are disabled because matplotlib is not installed.")
            return
        rows = read_expenses()
        if not rows:
            messagebox.showinfo("No data", "No expenses to summarize.")
            return
        summary = {}
        for r in rows:
            cat = r.get('category','')
            try:
                amt = float(r.get('amount', 0))
            except:
                continue
            summary[cat] = summary.get(cat, 0) + amt
        categories = list(summary.keys())
        amounts = [summary[c] for c in categories]
        if not categories:
            messagebox.showinfo("No data", "No expenses to summarize.")
            return
        try:
            plt.figure(figsize=(6,4))
            plt.pie(amounts, labels=categories, autopct='%1.1f%%')
            plt.title("Expense share by category")
            plt.tight_layout()
            plt.show()
        except Exception as e:
            log(f"Chart failed: {e}")
            messagebox.showerror("Chart failed", str(e))

    def on_search(self):
        q = self.search_var.get().strip().lower()
        if not q:
            self.refresh_table()
            return
        rows = read_expenses()
        filtered = []
        for r in rows:
            if q in r.get('date','').lower() or q in r.get('category','').lower() or q in r.get('note','').lower() or q in r.get('amount',''):
                filtered.append(r)
        self.refresh_table(filtered)

    def edit_categories(self):
        top = tk.Toplevel(self.root)
        top.title("Edit Categories")
        top.geometry("300x300")
        lst = tk.Listbox(top)
        lst.pack(fill="both", expand=True, padx=8, pady=8)
        for c in self.categories:
            lst.insert("end", c)
        ent = tk.Entry(top)
        ent.pack(fill="x", padx=8, pady=4)
        def add_cat():
            val = ent.get().strip()
            if val:
                lst.insert("end", val); ent.delete(0, "end")
        def remove_cat():
            sel = lst.curselection()
            if sel:
                lst.delete(sel[0])
        def save():
            new = [lst.get(i) for i in range(lst.size())]
            cfg = {"categories": new}
            try:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
                self.categories = new
                self.cat_combo['values'] = new
                if new:
                    self.cat_var.set(new[0])
                top.destroy()
                log("Updated categories.")
            except Exception as e:
                messagebox.showerror("Save failed", str(e))
        tk.Button(top, text="Add", command=add_cat).pack(side="left", padx=6, pady=6)
        tk.Button(top, text="Remove", command=remove_cat).pack(side="left", padx=6, pady=6)
        tk.Button(top, text="Save", command=save).pack(side="right", padx=6, pady=6)

    def sort_by(self, col, descending):
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        try:
            data = [(float(item[0]), item[1]) for item in data]
        except:
            pass
        data.sort(reverse=descending)
        for index, (val, k) in enumerate(data):
            self.tree.move(k, '', index)
        self.tree.heading(col, command=lambda: self.sort_by(col, not descending))


if __name__ == "__main__":
    try:
        ensure_files()
        log("App started.")
        print("DEBUG: starting GUI...")   # visible debug message in terminal
        root = tk.Tk()
        app = ExpenseApp(root)
        root.mainloop()
        log("App closed.")
    except Exception:
        # show a friendly error dialog and print the traceback to console & log file
        tb = traceback.format_exc()
        print(tb)
        log("Unhandled exception:\n" + tb)
        try:
            # try to show a messagebox (if tkinter available)
            messagebox.showerror("Unhandled error", f"An unexpected error occurred. See console and tracker_log.txt.\n\n{traceback.format_exc(limit=1)}")
        except Exception:
            pass
        sys.exit(1)