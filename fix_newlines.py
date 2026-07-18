with open("app2.py", "r") as f:
    text = f.read()

# Fix 1: Failed to extract
text = text.replace('f"Failed to extract binary: {str(extraction_error)}\n\n"\n                            "Please download manually from GitHub."', 'f"Failed to extract binary: {str(extraction_error)}\\n\\n" "Please download manually from GitHub."')

# Fix 2: Please download the binary manually
text = text.replace('''"Please download the binary manually:\n\n"\n                        f"1. Visit: {download_url}\n"\n                        f"2. Download the appropriate binary for your system\n"\n                        f"3. Place it in: {binary_folder}\n"\n                        "4. Rename to \'immich-go\' (or \'immich-go.exe\' on Windows)\n"\n                        "5. Ensure it has executable permissions"''', 
'''"Please download the binary manually:\\n\\n" f"1. Visit: {download_url}\\n" f"2. Download the appropriate binary for your system\\n" f"3. Place it in: {binary_folder}\\n" "4. Rename to 'immich-go' (or 'immich-go.exe' on Windows)\\n" "5. Ensure it has executable permissions"''')

# Fix 3: Failed to initiate download
text = text.replace('f"Failed to initiate download: {str(e)}\n\n"\n                    "Please download manually from GitHub."', 'f"Failed to initiate download: {str(e)}\\n\\n" "Please download manually from GitHub."')

with open("app2.py", "w") as f:
    f.write(text)
