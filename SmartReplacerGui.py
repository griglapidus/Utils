import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import shutil
import os
import sys
from pathlib import Path
from collections import defaultdict
import threading

# --- CONFIGURATION ---
IGNORE_FILENAME = "SmartReplacer_IgnoreDirs.txt"

SYSTEM_JUNK = {
    'Thumbs.db', 'ehthumbs.db', 'Desktop.ini', 
    '.DS_Store', '.localized'
}

class ConflictDialog:
    def __init__(self, parent, filename, paths):
        self.top = tk.Toplevel(parent)
        self.top.title("Filename Conflict Detected")
        self.top.geometry("600x400")
        self.top.transient(parent)
        self.top.grab_set()
        
        self.selected_path = None
        
        msg = f"File '{filename}' was found in multiple locations.\nSelect the file you want to replace, or click 'Skip'."
        tk.Label(self.top, text=msg, justify="left", padx=10, pady=10).pack(anchor="w")

        list_frame = tk.Frame(self.top)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar_y = tk.Scrollbar(list_frame, orient="vertical")
        scrollbar_x = tk.Scrollbar(list_frame, orient="horizontal")
        
        self.listbox = tk.Listbox(list_frame, 
                                  yscrollcommand=scrollbar_y.set, 
                                  xscrollcommand=scrollbar_x.set,
                                  selectmode=tk.SINGLE)
        
        scrollbar_y.config(command=self.listbox.yview)
        scrollbar_x.config(command=self.listbox.xview)
        
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")
        self.listbox.pack(side="left", fill="both", expand=True)

        for p in paths:
            self.listbox.insert(tk.END, str(p))

        btn_frame = tk.Frame(self.top)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(btn_frame, text="Skip this file", command=self.on_skip).pack(side="left")
        tk.Button(btn_frame, text="Replace selected", command=self.on_replace, bg="#dddddd").pack(side="right")

        self.top.protocol("WM_DELETE_WINDOW", self.on_skip)

    def on_replace(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a path from the list.", parent=self.top)
            return
        index = selection[0]
        self.selected_path = self.listbox.get(index)
        self.top.destroy()

    def on_skip(self):
        self.selected_path = None
        self.top.destroy()

class FileReplacerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SmartReplacer Tool")
        self.root.geometry("700x550")

        # --- UI Layout ---
        
        # Source Directory
        tk.Label(root, text="Source Directory (Files to copy):").pack(pady=(10, 0), anchor="w", padx=10)
        self.src_frame = tk.Frame(root)
        self.src_frame.pack(fill="x", padx=10, pady=5)
        self.src_entry = tk.Entry(self.src_frame)
        self.src_entry.pack(side="left", fill="x", expand=True)
        tk.Button(self.src_frame, text="Browse...", command=self.select_source).pack(side="right", padx=(5, 0))

        # Target Directory
        tk.Label(root, text="Target Directory (Search & Replace):").pack(pady=(10, 0), anchor="w", padx=10)
        self.dest_frame = tk.Frame(root)
        self.dest_frame.pack(fill="x", padx=10, pady=5)
        self.dest_entry = tk.Entry(self.dest_frame)
        self.dest_entry.pack(side="left", fill="x", expand=True)
        tk.Button(self.dest_frame, text="Browse...", command=self.select_dest).pack(side="right", padx=(5, 0))

        # Info Label
        info_text = f"ℹ️ Ignores: System files (Thumbs.db), Hidden files (.*), and entries in '{IGNORE_FILENAME}'."
        tk.Label(root, text=info_text, fg="#555555", font=("Arial", 9)).pack(pady=(5, 5), anchor="w", padx=10)

        # Run Button
        self.btn_run = tk.Button(root, text="Start Replacement", command=self.start_process, bg="#dddddd", height=2)
        self.btn_run.pack(fill="x", padx=10, pady=15)

        # Log Area
        tk.Label(root, text="Operation Log:").pack(anchor="w", padx=10)
        self.log_area = scrolledtext.ScrolledText(root, state='disabled', height=12)
        self.log_area.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Thread Synchronization
        self.user_choice_event = threading.Event()
        self.user_choice_path = None

    def select_source(self):
        path = filedialog.askdirectory()
        if path:
            self.src_entry.delete(0, tk.END)
            self.src_entry.insert(0, path)

    def select_dest(self):
        path = filedialog.askdirectory()
        if path:
            self.dest_entry.delete(0, tk.END)
            self.dest_entry.insert(0, path)

    def log(self, message):
        self.root.after(0, self._log_internal, message)

    def _log_internal(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def load_ignore_list(self):
        """Loads names to ignore from the text file."""
        ignore_set = set()
        script_dir = Path(__file__).parent
        ignore_file_path = script_dir / IGNORE_FILENAME

        if ignore_file_path.exists():
            try:
                with open(ignore_file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        name = line.strip()
                        if name and not name.startswith('#'):
                            ignore_set.add(name)
                self.log(f"Loaded ignore list: {len(ignore_set)} items")
            except Exception as e:
                self.log(f"Error reading {IGNORE_FILENAME}: {e}")
        else:
            self.log(f"No '{IGNORE_FILENAME}' found (scanning all folders).")
            
        return ignore_set

    def is_ignored(self, name, user_ignore_set):
        """Checks if a file/folder name should be skipped."""
        if name in SYSTEM_JUNK: return True
        if name.startswith('.'): return True
        if name in user_ignore_set: return True
        return False

    def start_process(self):
        src = self.src_entry.get()
        dest = self.dest_entry.get()

        if not src or not dest:
            messagebox.showwarning("Error", "Please select both directories.")
            return

        self.btn_run.config(state='disabled')
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state='disabled')

        threading.Thread(target=self.process_logic, args=(src, dest), daemon=True).start()

    def ask_user_resolution(self, filename, matches):
        self.user_choice_path = None
        self.user_choice_event.clear() 
        self.root.after(0, lambda: self._show_dialog_on_main(filename, matches))
        self.user_choice_event.wait()
        return self.user_choice_path

    def _show_dialog_on_main(self, filename, matches):
        dialog = ConflictDialog(self.root, filename, matches)
        self.root.wait_window(dialog.top)
        self.user_choice_path = dialog.selected_path
        self.user_choice_event.set()

    def process_logic(self, src_path, dest_path):
        source = Path(src_path)
        destination = Path(dest_path)
        
        ignored_names = self.load_ignore_list()
        
        self.log(f"Indexing files in: {dest_path}...")
        
        try:
            dest_files_map = defaultdict(list)
            
            # --- Step 1: Index Target Directory ---
            for root, dirs, files in os.walk(destination):
                # Filter directories in-place (os.walk feature)
                dirs[:] = [d for d in dirs if not self.is_ignored(d, ignored_names)]
                
                for filename in files:
                    if self.is_ignored(filename, ignored_names):
                        continue
                        
                    full_path = Path(root) / filename
                    dest_files_map[filename].append(full_path)
            
            replaced_count = 0
            
            # --- Step 2: Scan Source and Replace ---
            self.log("Scanning source...")
            for src_file in source.iterdir():
                if src_file.is_file():
                    filename = src_file.name
                    
                    if self.is_ignored(filename, ignored_names):
                        continue

                    if filename in dest_files_map:
                        matches = dest_files_map[filename]
                        target_file = None

                        if len(matches) == 1:
                            target_file = matches[0]
                        elif len(matches) > 1:
                            self.log(f"⚠️ CONFLICT: {filename} found in {len(matches)} locations.")
                            selected_str = self.ask_user_resolution(filename, matches)
                            if selected_str:
                                target_file = Path(selected_str)
                            else:
                                self.log(f"⏭️ Skipped: {filename}")

                        if target_file:
                            try:
                                shutil.copy2(src_file, target_file)
                                self.log(f"✅ Replaced: {target_file}")
                                replaced_count += 1
                            except Exception as e:
                                self.log(f"❌ Error copying {filename}: {e}")

            self.log("-" * 30)
            self.log(f"Done. Total files replaced: {replaced_count}")
            
        except Exception as e:
            self.log(f"Critical Error: {e}")
        finally:
            self.root.after(0, lambda: self.btn_run.config(state='normal'))

if __name__ == "__main__":
    root = tk.Tk()
    app = FileReplacerApp(root)
    root.mainloop()