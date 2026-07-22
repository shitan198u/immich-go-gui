# TODO

- [x] Fix terminal tracking: Without closing the terminal, the user cannot launch the immich-go binary again.
- [x] Fix theming

## Technical Debt
- [ ] Investigate process tracking compatibility in strict sandboxes (Flatpak/Snap) where psutil cannot see host processes.
- [ ] Rewrite `test_app.py` to decouple tests from the GUI layout (since the transition to QTabWidget, tests referencing `gui.inputs` are broken).
- [ ] Standardize configuration storage: Migrate the load/save configuration mechanism to use a standardized `.toml` format. Ensure robust cross-platform compatibility for configuration paths (e.g., `~/.config` on Linux, `AppData` on Windows, and `Application Support` on macOS).

## UI & Discoverability Improvements
- [ ] Improve discoverability of Simple/Advanced toggle: The toggle to switch between simple and advanced modes is currently hard to find. Redesign or reposition it to make it more intuitive for users.
- [ ] Sidebar icon styling: Update the sidebar icons to use the active accent color instead of inheriting plain text styling, ensuring better visual hierarchy and modern aesthetics.
- [ ] Streamline theme settings: Remove the unnecessary informational message stating that the app follows the operating system's theme to declutter the user interface.

## Features
- [ ] App update notifications: Implement an in-app notification system to alert users when a new version of the GUI application is available, similar to the existing binary management updates.
