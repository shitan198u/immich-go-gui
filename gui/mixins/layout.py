from typing import ClassVar

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
)

from gui.tabs.archive.folder import build_archive_folder_tab
from gui.tabs.archive.google_photos import build_archive_gp_tab
from gui.tabs.archive.icloud import build_archive_icloud_tab
from gui.tabs.archive.immich import build_archive_immich_tab
from gui.tabs.archive.picasa import build_archive_picasa_tab
from gui.tabs.upload.folder import build_upload_folder_tab
from gui.tabs.upload.google_photos import build_upload_gp_tab
from gui.tabs.upload.icloud import build_upload_icloud_tab
from gui.tabs.upload.immich import build_upload_immich_tab
from gui.tabs.upload.picasa import build_upload_picasa_tab
from gui.widgets import (
    BasePage,
    NavGroup,
    NavItem,
    StatusCard,
    SwitchButton,
)

_UPLOAD_TAB_KEYS = (
    "upload-folder",
    "upload-gp",
    "upload-icloud",
    "upload-picasa",
    "upload-immich",
)
_UPLOAD_CRUMBS = (
    "upload \u00b7 from-folder",
    "upload \u00b7 from-google-photos",
    "upload \u00b7 from-icloud",
    "upload \u00b7 from-picasa",
    "upload \u00b7 from-immich",
)
_ARCHIVE_TAB_KEYS = (
    "archive-folder",
    "archive-gp",
    "archive-icloud",
    "archive-picasa",
    "archive-immich",
)
_ARCHIVE_CRUMBS = (
    "archive \u00b7 from-folder",
    "archive \u00b7 from-google-photos",
    "archive \u00b7 from-icloud",
    "archive \u00b7 from-picasa",
    "archive \u00b7 from-immich",
)


class LayoutMixin:
    TAB_KEYS: ClassVar[list[str]] = [
        "config",
        "upload",
        "archive",
        "stack",
        "monitor",
    ]

    def _get_active_tab_key(self) -> str:
        idx = self.stacked_widget.currentIndex()
        if idx == 0:
            return "config"
        if idx == 1:
            u = self.upload_tabs.currentIndex() if hasattr(self, "upload_tabs") else 0
            return _UPLOAD_TAB_KEYS[min(u, len(_UPLOAD_TAB_KEYS) - 1)]
        if idx == 2:
            a = self.archive_tabs.currentIndex() if hasattr(self, "archive_tabs") else 0
            return _ARCHIVE_TAB_KEYS[min(a, len(_ARCHIVE_TAB_KEYS) - 1)]
        if idx == 3:
            return "stack"
        if idx == 4:
            return "monitor"
        return "config"

    def _build_upload_page(self):
        page = BasePage()
        self.upload_tabs = QTabWidget()
        self.upload_tabs.setDocumentMode(True)

        self.upload_folder_tab = build_upload_folder_tab(self)
        self.upload_gp_tab = build_upload_gp_tab(self)
        self.upload_icloud_tab = build_upload_icloud_tab(self)
        self.upload_picasa_tab = build_upload_picasa_tab(self)
        self.upload_immich_tab = build_upload_immich_tab(self)

        self.upload_tabs.addTab(self.upload_folder_tab, "From Folder")
        self.upload_tabs.addTab(self.upload_gp_tab, "Google Takeout")
        self.upload_tabs.addTab(self.upload_icloud_tab, "iCloud")
        self.upload_tabs.addTab(self.upload_picasa_tab, "Picasa")
        self.upload_tabs.addTab(self.upload_immich_tab, "From Immich")

        page.addWidget(self.upload_tabs)
        self.upload_tabs.currentChanged.connect(self._on_upload_tab_changed)
        self._on_upload_tab_changed(self.upload_tabs.currentIndex())
        return page

    def _on_upload_tab_changed(self, index: int):
        self.update_header_crumb(_UPLOAD_CRUMBS[min(index, len(_UPLOAD_CRUMBS) - 1)])
        self.update_status()

    def _build_archive_page(self):
        page = BasePage()
        self.archive_tabs = QTabWidget()
        self.archive_tabs.setDocumentMode(True)

        self.archive_folder_tab = build_archive_folder_tab(self)
        self.archive_gp_tab = build_archive_gp_tab(self)
        self.archive_icloud_tab = build_archive_icloud_tab(self)
        self.archive_picasa_tab = build_archive_picasa_tab(self)
        self.archive_immich_tab = build_archive_immich_tab(self)

        self.archive_tabs.addTab(self.archive_folder_tab, "From Folder")
        self.archive_tabs.addTab(self.archive_gp_tab, "Google Takeout")
        self.archive_tabs.addTab(self.archive_icloud_tab, "iCloud")
        self.archive_tabs.addTab(self.archive_picasa_tab, "Picasa")
        self.archive_tabs.addTab(self.archive_immich_tab, "From Immich")

        page.addWidget(self.archive_tabs)
        self.archive_tabs.currentChanged.connect(self._on_archive_tab_changed)
        self._on_archive_tab_changed(self.archive_tabs.currentIndex())
        return page

    def _on_archive_tab_changed(self, index: int):
        self.update_header_crumb(_ARCHIVE_CRUMBS[min(index, len(_ARCHIVE_CRUMBS) - 1)])
        self.update_status()

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)

        self.btn_config = NavItem("Configuration", None)
        self.btn_config.icon_name = "settings"
        self.btn_config.setChecked(True)
        self.btn_config.clicked.connect(
            lambda: self.switch_tab(0, "configuration", self.btn_config)
        )
        sidebar_layout.addWidget(NavGroup("", [self.btn_config]))

        self.btn_upload = NavItem("Upload", None)
        self.btn_upload.icon_name = "upload"
        self.btn_upload.clicked.connect(
            lambda: self.switch_tab(1, "upload", self.btn_upload)
        )
        sidebar_layout.addWidget(NavGroup("UPLOAD", [self.btn_upload]))

        self.btn_archive = NavItem("Archive", None)
        self.btn_archive.icon_name = "archive"
        self.btn_archive.clicked.connect(
            lambda: self.switch_tab(2, "archive", self.btn_archive)
        )
        sidebar_layout.addWidget(NavGroup("ARCHIVE", [self.btn_archive]))

        self.btn_stack = NavItem("Stack Assets", None)
        self.btn_stack.icon_name = "layers"
        self.btn_stack.clicked.connect(
            lambda: self.switch_tab(3, "stack", self.btn_stack)
        )
        sidebar_layout.addWidget(NavGroup("ORGANIZE", [self.btn_stack]))

        self.btn_monitor = NavItem("Monitor", None)
        self.btn_monitor.icon_name = "sync"
        self.btn_monitor.clicked.connect(
            lambda: self.switch_tab(4, "monitor", self.btn_monitor)
        )
        sidebar_layout.addWidget(NavGroup("BACKUP", [self.btn_monitor]))

        sidebar_layout.addStretch()

        self.status_card = StatusCard()
        sidebar_layout.addWidget(self.status_card)

        self.main_layout.addWidget(sidebar)

    def _build_content_area(self):
        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("HeaderFrame")
        header.setFixedHeight(60)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)

        title_box = QVBoxLayout()
        self.lbl_app_name = QLabel("Immich Go GUI")
        self.lbl_app_name.setObjectName("AppName")
        self.lbl_crumb = QLabel("configuration")
        self.lbl_crumb.setObjectName("Crumb")
        title_box.addWidget(self.lbl_app_name)
        title_box.addWidget(self.lbl_crumb)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        adv_box = QHBoxLayout()
        self.lbl_mode = QLabel("Simple")
        self.lbl_mode.setObjectName("ModeLabel")
        self.lbl_mode.setToolTip(
            "Simple mode hides advanced options and excludes them from the generated command."
        )
        adv_box.addWidget(self.lbl_mode)
        self.switch_advanced = SwitchButton()
        self.switch_advanced.setToolTip(
            "Simple mode hides advanced options and excludes them from the generated command."
        )
        self.switch_advanced.toggled.connect(self.toggle_advanced)
        adv_box.addWidget(self.switch_advanced)
        header_layout.addLayout(adv_box)

        content_layout.addWidget(header)

        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget)

        self.footer = QFrame()
        self.footer.setObjectName("FooterFrame")
        self.footer.setFixedHeight(70)
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(24, 0, 24, 0)

        self.lbl_running_warning = QLabel(
            "\u26a0\ufe0f Immich-Go is currently running in a terminal. "
            "Close the terminal to run another command."
        )
        self.lbl_running_warning.setObjectName("RunningWarning")
        self.lbl_running_warning.setStyleSheet("color: #EAB308; font-weight: 500;")
        self.lbl_running_warning.setVisible(False)
        footer_layout.addWidget(self.lbl_running_warning)
        footer_layout.addStretch()

        self.btn_dry_run = QPushButton("Preview (Dry Run)")
        self.btn_dry_run.setObjectName("BtnPreview")
        self.btn_dry_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dry_run.clicked.connect(lambda: self.show_confirm_dialog(True))
        footer_layout.addWidget(self.btn_dry_run)

        self.btn_run = QPushButton("Run Command")
        self.btn_run.setObjectName("BtnRun")
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.clicked.connect(lambda: self.show_confirm_dialog(False))
        footer_layout.addWidget(self.btn_run)

        content_layout.addWidget(self.footer)
        self.main_layout.addWidget(content_frame)

    def toggle_advanced(self, checked):
        self.is_advanced = checked
        if hasattr(self, "app_config"):
            self.app_config.advanced_mode = checked
        if hasattr(self, "switch_advanced"):
            self.switch_advanced.blockSignals(True)
            self.switch_advanced.setChecked(checked)
            self.switch_advanced.blockSignals(False)
        if hasattr(self, "btn_mode"):
            self.btn_mode.blockSignals(True)
            self.btn_mode.setChecked(checked)
            self.btn_mode.blockSignals(False)
        if hasattr(self, "lbl_mode"):
            self.lbl_mode.setText("Advanced" if checked else "Simple")
        for w in getattr(self, "adv_frames", []):
            w.setVisible(checked)

    def switch_tab(self, index, crumb, btn):
        self.stacked_widget.setCurrentIndex(index)
        if index == 1 and hasattr(self, "upload_tabs"):
            u = self.upload_tabs.currentIndex()
            crumb = _UPLOAD_CRUMBS[min(u, len(_UPLOAD_CRUMBS) - 1)]
        elif index == 2 and hasattr(self, "archive_tabs"):
            a = self.archive_tabs.currentIndex()
            crumb = _ARCHIVE_CRUMBS[min(a, len(_ARCHIVE_CRUMBS) - 1)]
        elif index == 4:
            crumb = "monitor"
        self.update_header_crumb(crumb)
        for w in (
            self.btn_config,
            self.btn_upload,
            self.btn_archive,
            self.btn_stack,
            self.btn_monitor,
        ):
            w.setChecked(False)
        btn.setChecked(True)
        self.footer.setVisible(index not in (0, 4))
        tab_key = self._get_active_tab_key()
        if tab_key in self.inputs and "target-server" in self.inputs[tab_key]:
            srv_edit = self.inputs.get("config", {}).get("server")
            srv = srv_edit.text() if srv_edit else ""
            self.inputs[tab_key]["target-server"].setText(
                srv if srv else "Not Configured"
            )

    def update_header_crumb(self, text):
        self.lbl_crumb.setText(text)
