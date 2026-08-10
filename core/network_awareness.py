"""Network awareness for the Monitor subsystem.

Detects metered connections, Wi-Fi SSID, and enforces upload policies
(e.g., pause on metered, only upload on specific SSIDs).
"""

import logging
import subprocess
import sys
from enum import Enum

from .monitor_config import NetworkPolicy

_log = logging.getLogger(__name__)


class NetworkStatus(str, Enum):
    """Current network state."""

    UNKNOWN = "unknown"
    ALLOWED = "allowed"  # Policy permits uploads
    BLOCKED_METERED = "blocked_metered"  # On a metered connection
    BLOCKED_SSID = "blocked_ssid"  # Not on an allowed SSID
    BLOCKED_OFFLINE = "blocked_offline"  # No network connection


class NetworkMonitor:
    """Checks network conditions against the configured policy."""

    def __init__(self, policy: NetworkPolicy, allowed_ssids: list[str] | None = None):
        self._policy = policy
        self._allowed_ssids = set(allowed_ssids or [])

    def check_status(self) -> NetworkStatus:
        """Check current network state against policy.

        Returns:
            NetworkStatus indicating if uploads should be allowed.
        """
        # Check if online
        if not self._is_online():
            return NetworkStatus.BLOCKED_OFFLINE

        if self._policy == NetworkPolicy.ALWAYS:
            return NetworkStatus.ALLOWED

        # Check metered
        if self._policy == NetworkPolicy.NO_METERED:
            if self._is_metered():
                return NetworkStatus.BLOCKED_METERED
            return NetworkStatus.ALLOWED

        # Check SSID
        if self._policy == NetworkPolicy.SSID_ONLY:
            current_ssid = self._get_ssid()
            if not current_ssid:
                return NetworkStatus.UNKNOWN
            if current_ssid not in self._allowed_ssids:
                return NetworkStatus.BLOCKED_SSID
            return NetworkStatus.ALLOWED

        return NetworkStatus.UNKNOWN

    @staticmethod
    def _is_online() -> bool:
        """Basic internet connectivity test."""
        import socket

        try:
            with socket.create_connection(("8.8.8.8", 53), timeout=3):
                return True
        except OSError:
            return False

    @staticmethod
    def _is_metered() -> bool:
        """Check if the current network is metered.

        No reliable detection is available yet: the correct Windows
        implementation requires the INetworkConnectionCost COM API and is
        tracked as a follow-up.  Returning False avoids permanently
        blocking uploads on a false positive.
        """
        return False

    @staticmethod
    def _get_ssid() -> str | None:
        """Get the current Wi-Fi SSID name."""
        if sys.platform.startswith("win"):
            return _get_ssid_windows()
        else:
            return _get_ssid_linux()


def _get_ssid_windows() -> str | None:
    """Get Wi-Fi SSID on Windows using netsh."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            check=False,
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("SSID") and ":" in line:
                ssid = line.split(":", 1)[1].strip()
                if ssid:
                    return ssid
    except Exception:
        pass
    return None


def _get_ssid_linux() -> str | None:
    """Get Wi-Fi SSID on Linux via nmcli or iwconfig."""
    # Try nmcli first
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in result.stdout.splitlines():
            if line.startswith("yes:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass

    # Try iwconfig as fallback
    try:
        result = subprocess.run(
            ["iwconfig"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in result.stdout.splitlines():
            if "ESSID:" in line:
                ssid = line.split('ESSID:"', 1)[1].rstrip('"')
                if ssid and ssid != "off/any":
                    return ssid
    except Exception:
        pass

    return None
