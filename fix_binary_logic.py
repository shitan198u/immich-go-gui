import re

with open("app.py", "r") as f:
    app_code = f.read()

# Extract update_binary from app.py
match = re.search(r'    def update_binary\(self\):(.*?)    def run_command\(self, command_parts=None\):', app_code, re.DOTALL)
app_update_binary = match.group(1) if match else ""

# Ensure we have the logic
if not app_update_binary:
    print("Could not find update_binary in app.py")
    exit(1)

# Let's adjust the update_binary to support force_download
new_update_binary = """    def check_binary_version(self):
        binary_folder = os.path.abspath(os.path.join(os.getcwd(), "immich-go"))
        binary_filename = "immich-go.exe" if sys.platform.startswith("win") else "immich-go"
        self.binary_path = os.path.join(binary_folder, binary_filename)

        if not os.path.exists(self.binary_path):
            if hasattr(self, 'lbl_binary_info'):
                self.lbl_binary_info.setText(f"Current Version: Not found\\nLocated at: {self.binary_path}")
            if hasattr(self, 'lbl_binary_status'):
                self.lbl_binary_status.setText("🔴 Binary: Missing")
            return
            
        try:
            result = subprocess.run([self.binary_path, "version"], capture_output=True, text=True, timeout=2)
            version_text = result.stdout.strip() if result.stdout else "Unknown version"
            if hasattr(self, 'lbl_binary_info'):
                self.lbl_binary_info.setText(f"Current Version: {version_text}\\nLocated at: {self.binary_path}")
            if hasattr(self, 'lbl_binary_status'):
                self.lbl_binary_status.setText("🟢 Binary: Ready")
        except Exception:
            if hasattr(self, 'lbl_binary_info'):
                self.lbl_binary_info.setText(f"Current Version: Unknown\\nLocated at: {self.binary_path}")
            if hasattr(self, 'lbl_binary_status'):
                self.lbl_binary_status.setText("🟢 Binary: Ready")

    def check_for_updates(self):
        self.check_binary_version()
        latest_version = self.get_latest_release_info()
        if not latest_version:
            QMessageBox.warning(self, "Update Check", "Failed to fetch the latest version information from GitHub.")
            return
            
        current_version = "Unknown"
        if hasattr(self, 'lbl_binary_info'):
            info = self.lbl_binary_info.text()
            if "Current Version: " in info:
                current_version = info.split("Current Version: ")[1].split("\\n")[0]
                
        reply = QMessageBox.question(self, "Update Check", 
            f"Latest version: {latest_version}\\nCurrent version: {current_version}\\n\\nDo you want to download and install the latest version?",
            QMessageBox.Yes | QMessageBox.No)
            
        if reply == QMessageBox.Yes:
            self.update_binary(force_download=True)

    def update_binary(self, force_download=False):"""

# Modify the extracted logic
app_update_binary_lines = app_update_binary.split('\n')
modified_lines = []
for line in app_update_binary_lines[1:]:
    if "if not os.path.exists(binary_path):" in line:
        modified_lines.append(line.replace("if not os.path.exists(binary_path):", "if not os.path.exists(binary_path) or force_download:"))
    elif "def handle_download_complete(content):" in line:
        modified_lines.append(line)
    elif "progress_dialog.accept()" in line:
        modified_lines.append(line)
    elif "os.chmod(binary_path, 0o755)" in line:
        modified_lines.append(line)
        modified_lines.append(line.replace("os.chmod(binary_path, 0o755)", "self.check_binary_version()"))
    else:
        modified_lines.append(line)

new_code = new_update_binary + "\n" + "\n".join(modified_lines)

with open("app2.py", "r") as f:
    app2_code = f.read()

# Replace dummy update_binary with the new one
app2_code = re.sub(r'    def update_binary\(self\):.*?return False\n+', new_code + '\n\n', app2_code, flags=re.DOTALL)

with open("app2.py", "w") as f:
    f.write(app2_code)

print("Successfully replaced update_binary and added checking logic in app2.py")
