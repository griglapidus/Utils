import argparse
import shutil
import os
import sys
from pathlib import Path
from collections import defaultdict

# --- CONFIGURATION ---
IGNORE_FILENAME = "SmartReplacer_IgnoreDirs.txt"

SYSTEM_JUNK = {
    'Thumbs.db', 'ehthumbs.db', 'Desktop.ini', 
    '.DS_Store', '.localized'
}

def load_ignore_list():
    """Loads names to ignore from the text file located next to the script."""
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
            print(f"[INFO] Loaded ignore list from '{IGNORE_FILENAME}': {len(ignore_set)} items.")
        except Exception as e:
            print(f"[WARN] Error reading {IGNORE_FILENAME}: {e}")
    
    return ignore_set

def is_ignored(name, user_ignore_set):
    """Checks if a file/folder name should be skipped."""
    if name in SYSTEM_JUNK: return True
    if name.startswith('.'): return True
    if name in user_ignore_set: return True
    return False

def run_console_replacement(src_path, dest_path):
    source = Path(src_path)
    destination = Path(dest_path)

    if not source.exists() or not destination.exists():
        print("Error: Source or Target directory does not exist.")
        return

    user_ignore = load_ignore_list()

    print(f"Indexing target directory: {dest_path}...")
    print("(Skipping hidden files, system junk, and ignore list patterns)...")

    # 1. Index Destination
    dest_files_map = defaultdict(list)
    
    # os.walk allows modifying 'dirs' in-place to prune the search tree efficiently
    for root, dirs, files in os.walk(destination):
        # Prune ignored directories
        dirs[:] = [d for d in dirs if not is_ignored(d, user_ignore)]
        
        for filename in files:
            if is_ignored(filename, user_ignore):
                continue
            
            full_path = Path(root) / filename
            dest_files_map[filename].append(full_path)

    print("-" * 40)
    print("Processing files...")
    
    replaced_count = 0

    # 2. Process Source
    for src_file in source.iterdir():
        if src_file.is_file():
            filename = src_file.name
            
            # Check ignore rules for source files too
            if is_ignored(filename, user_ignore):
                continue

            if filename in dest_files_map:
                matches = dest_files_map[filename]
                
                if len(matches) == 1:
                    target_file = matches[0]
                    try:
                        shutil.copy2(src_file, target_file)
                        print(f"[OK] Replaced: {target_file}")
                        replaced_count += 1
                    except Exception as e:
                        print(f"[ERR] Failed to copy {filename}: {e}")
                
                elif len(matches) > 1:
                    print(f"[SKIP] Conflict: '{filename}' found in {len(matches)} locations (ambiguous).")
                    # CLI usually skips ambiguities in batch mode

    print("-" * 40)
    print(f"Done. Total files replaced: {replaced_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SmartReplacer: Recursively update files ignoring system junk and custom patterns.")
    parser.add_argument("source", help="Path to the source directory")
    parser.add_argument("target", help="Path to the target directory")

    args = parser.parse_args()

    run_console_replacement(args.source, args.target)