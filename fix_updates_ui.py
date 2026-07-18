import re

with open("app2.py", "r") as f:
    text = f.read()

# 1. Assign self.btn_check_updates
text = text.replace(
    'btn_check = QPushButton("Check for Updates")\n        btn_check.clicked.connect(self.check_for_updates)',
    'btn_check = QPushButton("Check for Updates")\n        self.btn_check_updates = btn_check\n        btn_check.clicked.connect(self.check_for_updates)'
)

# 2. Add btn_check_updates.setText("Download Immich-Go") to missing binary logic
text = text.replace(
    'if hasattr(self, \'lbl_binary_status\'):\n                self.lbl_binary_status.setText("🔴 Binary: Missing")\n            return',
    'if hasattr(self, \'lbl_binary_status\'):\n                self.lbl_binary_status.setText("🔴 Binary: Missing")\n            if hasattr(self, \'btn_check_updates\'):\n                self.btn_check_updates.setText("Download Immich-Go")\n            return'
)

# 3. Add btn_check_updates.setText("Check for Updates") to found binary logic (both try and except)
text = text.replace(
    'if hasattr(self, \'lbl_binary_status\'):\n                self.lbl_binary_status.setText("🟢 Binary: Ready")\n        except',
    'if hasattr(self, \'lbl_binary_status\'):\n                self.lbl_binary_status.setText("🟢 Binary: Ready")\n            if hasattr(self, \'btn_check_updates\'):\n                self.btn_check_updates.setText("Check for Updates")\n        except'
)

text = text.replace(
    'if hasattr(self, \'lbl_binary_status\'):\n                self.lbl_binary_status.setText("🟢 Binary: Ready")\n\n    def',
    'if hasattr(self, \'lbl_binary_status\'):\n                self.lbl_binary_status.setText("🟢 Binary: Ready")\n            if hasattr(self, \'btn_check_updates\'):\n                self.btn_check_updates.setText("Check for Updates")\n\n    def'
)

# 4. Modify check_for_updates message box text
check_for_updates_old = '''        reply = QMessageBox.question(self, "Update Check", 
            f"Latest version: {latest_version}\\nCurrent version: {current_version}\\n\\nDo you want to download and install the latest version?",
            QMessageBox.Yes | QMessageBox.No)'''

check_for_updates_new = '''        if current_version == "Not found":
            reply = QMessageBox.question(self, "Download Immich-Go", 
                f"The latest version is {latest_version}.\\n\\nDo you want to download and install it now?",
                QMessageBox.Yes | QMessageBox.No)
        else:
            reply = QMessageBox.question(self, "Update Check", 
                f"Latest version: {latest_version}\\nCurrent version: {current_version}\\n\\nDo you want to download and install the latest version?",
                QMessageBox.Yes | QMessageBox.No)'''

text = text.replace(check_for_updates_old, check_for_updates_new)

with open("app2.py", "w") as f:
    f.write(text)
