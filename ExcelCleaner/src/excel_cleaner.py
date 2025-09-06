# excel_cleaner.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os

class ExcelCleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Excel Data Cleaner")
        self.df = None
        self.filepath = None

        self._build_ui()

    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=12)
        frm.grid(sticky="nsew")

        # Load file
        ttk.Button(frm, text="Load Excel/CSV", command=self.load_file).grid(row=0, column=0, sticky="w")
        self.loaded_label = ttk.Label(frm, text="No file loaded")
        self.loaded_label.grid(row=0, column=1, sticky="w", padx=8)

        # Preview area
        ttk.Label(frm, text="Preview (first 10 rows):").grid(row=1, column=0, columnspan=2, sticky="w", pady=(10,0))
        self.preview_text = tk.Text(frm, width=100, height=15)
        self.preview_text.grid(row=2, column=0, columnspan=4, pady=(0,10))

        # Cleaning options
        ttk.Button(frm, text="Auto Clean (dup, strip, parse dates)", command=self.auto_clean).grid(row=3, column=0, sticky="w")
        ttk.Button(frm, text="Fill Missing (numeric mean)", command=self.fill_numeric_mean).grid(row=3, column=1, sticky="w", padx=6)
        ttk.Button(frm, text="Drop Duplicates", command=self.drop_duplicates).grid(row=3, column=2, sticky="w", padx=6)
        ttk.Button(frm, text="Export Cleaned (Excel)", command=self.export_cleaned).grid(row=3, column=3, sticky="w", padx=6)

        # Status area
        self.status = ttk.Label(frm, text="Status: Ready")
        self.status.grid(row=4, column=0, columnspan=4, sticky="w", pady=(8,0))

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files",".xlsx;.xls"), ("CSV files","*.csv")])
        if not path:
            return
        self.filepath = path
        try:
            if path.lower().endswith(".csv"):
                df = pd.read_csv(path)
            else:
                df = pd.read_excel(path, engine="openpyxl")
        except Exception as e:
            messagebox.showerror("Error", f"Could not read file: {e}")
            return
        self.df = df
        self.loaded_label.config(text=os.path.basename(path))
        self.show_preview()
        self.status.config(text=f"Loaded {len(df)} rows, {len(df.columns)} columns")

    def show_preview(self):
        if self.df is None:
            return
        self.preview_text.delete("1.0", tk.END)
        preview = self.df.head(10).to_string()
        self.preview_text.insert(tk.END, preview)

    def auto_clean(self):
        if self._need_df(): return
        before = len(self.df)
        # 1. strip whitespace for object columns
        obj_cols = self.df.select_dtypes(include=['object']).columns
        for c in obj_cols:
            try:
                self.df[c] = self.df[c].astype(str).str.strip()
            except Exception:
                pass
        # 2. drop completely empty columns
        self.df.dropna(axis=1, how='all', inplace=True)
        # 3. try parse datetimes for columns that look like dates
        for c in self.df.columns:
            if self.df[c].dtype == object:
                sample = self.df[c].dropna().astype(str).head(5)
                if sample.str.match(r'\d{4}-\d{1,2}-\d{1,2}').any() or sample.str.match(r'\d{1,2}/\d{1,2}/\d{2,4}').any():
                    try:
                        self.df[c] = pd.to_datetime(self.df[c], errors='coerce', infer_datetime_format=True)
                    except Exception:
                        pass
        after = len(self.df)
        self.show_preview()
        self.status.config(text=f"Auto-clean done (rows before: {before}, after: {after})")

    def drop_duplicates(self):
        if self._need_df(): return
        before = len(self.df)
        self.df.drop_duplicates(inplace=True)
        after = len(self.df)
        self.show_preview()
        self.status.config(text=f"Dropped duplicates: {before-after} rows removed")

    def fill_numeric_mean(self):
        if self._need_df(): return
        num_cols = self.df.select_dtypes(include=['number']).columns
        for c in num_cols:
            if self.df[c].isna().any():
                mean_val = self.df[c].mean()
                self.df[c].fillna(mean_val, inplace=True)
        self.show_preview()
        self.status.config(text="Filled numeric missing values with column mean")

    def export_cleaned(self):
        if self._need_df(): return
        default_name = "cleaned_" + (os.path.basename(self.filepath) if self.filepath else "data.xlsx")
        save_path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                                 initialfile=default_name,
                                                 filetypes=[("Excel file",".xlsx"), ("CSV file",".csv")])
        if not save_path:
            return
        try:
            if save_path.lower().endswith(".csv"):
                self.df.to_csv(save_path, index=False)
            else:
                self.df.to_excel(save_path, index=False, engine="openpyxl")
            self.status.config(text=f"Saved cleaned file to {save_path}")
            messagebox.showinfo("Exported", f"Cleaned file saved:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file: {e}")

    def _need_df(self):
        if self.df is None:
            messagebox.showwarning("No file", "Please load a file first.")
            return True
        return False

if __name__ == "__main__":
    root = tk.Tk()
    app = ExcelCleanerApp(root)
    root.mainloop()