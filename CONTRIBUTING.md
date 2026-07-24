# Contributing to Immich-Go GUI

First off, thank you for considering contributing to Immich-Go GUI! It's people like you that make open-source software such a great community.

## Where do I go from here?

If you've noticed a bug or have a feature request, make sure to check if there's already an [issue](https://github.com/shitan198u/immich-go-gui/issues) for it. If not, open a new one using the provided templates!

## Setting up for Local Development

To run the Immich-Go GUI locally or work on it, follow these steps:

1. **Install Prerequisites**: 
   - Ensure you have Python 3.11+ installed.
   - Install the [`uv`](https://docs.astral.sh/uv/getting-started/installation/) package manager.

2. **Fork & Clone**:
   - Fork this repository to your own GitHub account.
   - Clone it to your local machine: `git clone https://github.com/YOUR_USERNAME/immich-go-gui.git`

3. **Install Dependencies**:
   Navigate into the project directory and run:
   ```bash
   cd immich-go-gui
   uv sync --dev
   ```
   *(Note: This installs PySide6, Pytest, and other dev dependencies).*

4. **Run the Application**:
   ```bash
   uv run app.py
   ```

## Testing Your Changes

Before submitting a Pull Request, please ensure all tests pass:

```bash
uv run pytest
```
If you are adding a new feature, please consider writing a test for it in `tests/test_app.py`.

## Making a Pull Request

1. Create a new branch: `git checkout -b feature-or-bugfix-name`
2. Make your changes and commit them with a descriptive message.
3. Push your branch: `git push origin feature-or-bugfix-name`
4. Open a Pull Request! Fill out the provided PR template.

## Building Executables

If you want to test how your changes compile, you can use Nuitka locally.

**Windows**:
```bash
uv run python -m nuitka --assume-yes-for-downloads --onefile --windows-console-mode=disable --enable-plugin=pyside6 --include-data-files=immich-go-gui.png=immich-go-gui.png app.py
```

**macOS**:
```bash
uv run python -m nuitka --assume-yes-for-downloads --macos-create-app-bundle --enable-plugin=pyside6 --include-data-files=immich-go-gui.png=immich-go-gui.png app.py
```

**Linux**:
```bash
uv run python -m nuitka --assume-yes-for-downloads --standalone --enable-plugin=pyside6 --include-data-files=immich-go-gui.png=immich-go-gui.png app.py
```

Thank you for contributing!
