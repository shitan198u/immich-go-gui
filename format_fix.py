with open("app2.py", "r") as f:
    text = f.read()

# Replace \\n with \n in the string literals
text = text.replace('f"Current Version: Not found\\\\nLocated at: {self.binary_path}"', 'f"Current Version: Not found\\nLocated at: {self.binary_path}"')
text = text.replace('f"Current Version: {version_text}\\\\nLocated at: {self.binary_path}"', 'f"Current Version: {version_text}\\nLocated at: {self.binary_path}"')
text = text.replace('f"Current Version: Unknown\\\\nLocated at: {self.binary_path}"', 'f"Current Version: Unknown\\nLocated at: {self.binary_path}"')
text = text.replace('info.split("Current Version: ")[1].split("\\\\n")[0]', 'info.split("Current Version: ")[1].split("\\n")[0]')
text = text.replace('f"Latest version: {latest_version}\\\\nCurrent version: {current_version}\\\\n\\\\nDo you want to download and install the latest version?"', 'f"Latest version: {latest_version}\\nCurrent version: {current_version}\\n\\nDo you want to download and install the latest version?"')

# Add version_text split
import re
text = re.sub(
    r'version_text = result.stdout.strip\(\) if result.stdout else "Unknown version"',
    'version_text = result.stdout.strip() if result.stdout else "Unknown version"\n            if "," in version_text: version_text = version_text.split(",")[0]',
    text
)

# And fix the remaining places where I might have messed up the newlines in QMessageBox:
text = text.replace('f"Failed to extract binary: {str(extraction_error)}\\\\n\\\\n" "Please download manually from GitHub."', 'f"Failed to extract binary: {str(extraction_error)}\\n\\n" "Please download manually from GitHub."')
text = text.replace('"Please download the binary manually:\\\\n\\\\n" f"1. Visit: {download_url}\\\\n" f"2. Download the appropriate binary for your system\\\\n" f"3. Place it in: {binary_folder}\\\\n" "4. Rename to \'immich-go\' (or \'immich-go.exe\' on Windows)\\\\n" "5. Ensure it has executable permissions"', '"Please download the binary manually:\\n\\n" f"1. Visit: {download_url}\\n" f"2. Download the appropriate binary for your system\\n" f"3. Place it in: {binary_folder}\\n" "4. Rename to \'immich-go\' (or \'immich-go.exe\' on Windows)\\n" "5. Ensure it has executable permissions"')
text = text.replace('f"Failed to initiate download: {str(e)}\\\\n\\\\n" "Please download manually from GitHub."', 'f"Failed to initiate download: {str(e)}\\n\\n" "Please download manually from GitHub."')


with open("app2.py", "w") as f:
    f.write(text)
