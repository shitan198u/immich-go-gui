"""Network diagnostic helpers for Immich-Go GUI.

Pure Python module, Qt-free.
"""

from dataclasses import dataclass
import requests


@dataclass
class ConnectionTestResult:
    ok: bool
    message: str
    status_code: int | None = None
    server_version: str | None = None


def normalize_server_url(url: str) -> str:
    """Ensure server URL has scheme and no trailing slash."""
    url = url.strip()
    if not url:
        return ""
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "http://" + url
    return url.rstrip("/")


def test_immich_connection(
    server_url: str,
    api_key: str,
    skip_ssl: bool = False,
    timeout: float = 6.0,
) -> ConnectionTestResult:
    """Test connectivity and API key validity against an Immich server.

    Does not leak or log the API key.
    """
    clean_url = normalize_server_url(server_url)
    if not clean_url:
        return ConnectionTestResult(ok=False, message="Server URL is empty")

    if not api_key:
        return ConnectionTestResult(ok=False, message="API key is empty")

    target_endpoint = f"{clean_url}/api/server/about"
    headers = {
        "x-api-key": api_key,
        "Accept": "application/json",
    }

    try:
        response = requests.get(
            target_endpoint,
            headers=headers,
            verify=not skip_ssl,
            timeout=timeout,
        )
        status_code = response.status_code

        if status_code == 200:
            version = None
            try:
                data = response.json()
                if isinstance(data, dict):
                    version = data.get("version") or data.get("serverVersion")
            except Exception:
                pass
            msg = f"Successfully connected to Immich server"
            if version:
                msg += f" (Version: {version})"
            return ConnectionTestResult(
                ok=True,
                message=msg,
                status_code=200,
                server_version=version,
            )
        elif status_code in (401, 403):
            return ConnectionTestResult(
                ok=False,
                message=f"Authentication failed (HTTP {status_code}). Please verify your API key.",
                status_code=status_code,
            )
        elif status_code == 404:
            return ConnectionTestResult(
                ok=False,
                message="Server responded (HTTP 404), but the Immich API endpoint '/api/server/about' was not found.",
                status_code=404,
            )
        else:
            return ConnectionTestResult(
                ok=False,
                message=f"Server returned status code {status_code}.",
                status_code=status_code,
            )

    except requests.exceptions.SSLError:
        return ConnectionTestResult(
            ok=False,
            message="SSL certificate verification failed. Enable 'Skip SSL verification' if using self-signed certificates.",
        )
    except requests.exceptions.Timeout:
        return ConnectionTestResult(
            ok=False,
            message=f"Connection timed out after {timeout} seconds. Check server URL and network connection.",
        )
    except requests.exceptions.ConnectionError:
        return ConnectionTestResult(
            ok=False,
            message="Failed to connect to server. Verify server URL and network accessibility.",
        )
    except Exception as e:
        return ConnectionTestResult(
            ok=False,
            message=f"Unexpected connection error: {str(e)}",
        )
