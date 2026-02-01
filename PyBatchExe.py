import os
import subprocess
import shutil

def is_gui_script(filepath):
    """
    Checks if the script imports common GUI libraries.
    """
    gui_libraries = ['tkinter', 'pyqt', 'pyside', 'customtkinter', 'flet', 'kivy']
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().lower()
            for lib in gui_libraries:
                if f'import {lib}' in content or f'from {lib}' in content:
                    return True
    except Exception as e:
        print(f"Could not read {filepath}: {e}")
    return False

def cleanup(script_name):
    """
    Removes temporary build files and directories created by PyInstaller.
    """
    # Remove .spec file
    spec_file = script_name.replace('.py', '.spec')
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"Removed: {spec_file}")

    # Remove build directory
    if os.path.exists('build'):
        shutil.rmtree('build')
        print("Removed: build/ directory")

def convert_to_exe():
    current_script = os.path.basename(__file__)
    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    python_files = [f for f in files if f.endswith('.py') and f != current_script]
    
    if not python_files:
        print("No Python scripts found.")
        return

    for script in python_files:
        print(f"\n--- Processing: {script} ---")
        
        command = ["pyinstaller", "--onefile", "--clean"]
        
        if is_gui_script(script):
            print(f"GUI detected. Adding --noconsole flag.")
            command.append("--noconsole")
        
        command.append(script)
        
        try:
            # Execute PyInstaller
            subprocess.run(command, check=True)
            print(f"Successfully converted: {script}")
        except subprocess.CalledProcessError as e:
            print(f"Error converting {script}: {e}")
        finally:
            # Perform cleanup for the current script
            cleanup(script)

    print("\n--- All tasks finished. Check the 'dist' folder for results ---")

if __name__ == "__main__":
    convert_to_exe()