import re

with open("app2.py", "r") as f:
    app2_code = f.read()
    
with open("update_binary_app.py.txt", "r") as f:
    update_binary_src = f.read()

# Make the adjustments to update_binary_src
# 1. Change def update_binary(self): to def update_binary(self, force_download=False):
update_binary_src = update_binary_src.replace("def update_binary(self):", "def update_binary(self, force_download=False):")
# 2. Change if not os.path.exists(binary_path): to if not os.path.exists(binary_path) or force_download:
update_binary_src = update_binary_src.replace("if not os.path.exists(binary_path):", "if not os.path.exists(binary_path) or force_download:")
# 3. Add self.check_binary_version() after os.chmod
update_binary_src = update_binary_src.replace("os.chmod(binary_path, 0o755)", "os.chmod(binary_path, 0o755)\n                            self.check_binary_version()")
# 4. Add self.check_binary_version() after progress_dialog.accept() maybe? wait, after we open the zip/tar, it's better. But wait, at the end of handle_download_complete is better.
# Actually, I'll just leave it after chmod and for windows after extraction. 
update_binary_src = update_binary_src.replace("raise ValueError(\"Unsupported archive type\")", "raise ValueError(\"Unsupported archive type\")\n\n                        if sys.platform.startswith(\"win\"):\n                            self.check_binary_version()")


# In app2_code, replace the entire update_binary method.
# We know check_for_updates is right before update_binary
# So we can regex match from def update_binary to def run_command
app2_code = re.sub(r'    def update_binary\(self, force_download=False\):.*?    def run_command\(self, command_parts=None\):', 
                   update_binary_src + '\n\n    def run_command(self, command_parts=None):', 
                   app2_code, flags=re.DOTALL)

with open("app2.py", "w") as f:
    f.write(app2_code)
