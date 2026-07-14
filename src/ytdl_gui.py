from __future__ import annotations

import asyncio
import importlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import flet as ft


def resource_root() -> Path:
    """Locate project root (pic/, src/, bin/) for dev and packaged builds."""
    candidates: list[Path] = []

    # PyInstaller
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS))  # type: ignore[attr-defined]

    # Flet / serious_python macOS / Windows app bundle
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        # YTDL.app/Contents/MacOS/YTDL → Resources / Resources/app
        candidates.extend(
            [
                exe.parent.parent / "Resources" / "app",
                exe.parent.parent / "Resources",
                exe.parent.parent / "Frameworks",
                exe.parent,
            ]
        )

    # Env hints used by some Flet desktop builds
    for key in ("FLET_APP_STORAGE_DATA", "FLET_APP_HOME", "APP_ROOT"):
        value = (os.environ.get(key) or "").strip()
        if value:
            candidates.append(Path(value))

    # Flet macOS extract dir: ~/Library/Application Support/<bundle>/flet/app
    try:
        support = Path.home() / "Library" / "Application Support"
        if support.is_dir():
            for app_dir in support.glob("*/flet/app"):
                candidates.append(app_dir)
                candidates.append(app_dir.parent.parent)  # bundle support root
    except Exception:
        pass

    # Source layout: .../src/ytdl_gui.py → project root
    try:
        here = Path(__file__).resolve()
        candidates.append(here.parent)  # next to ytdl_gui.py (sometimes app root)
        candidates.append(here.parents[1])  # .../src/ytdl_gui.py → project root
    except Exception:
        pass

    candidates.append(Path.cwd())

    seen: set[str] = set()
    for path in candidates:
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        if (resolved / "pic").is_dir() or (resolved / "src").is_dir() or (resolved / "assets").is_dir():
            return resolved

    try:
        return Path(__file__).resolve().parents[1]
    except Exception:
        return Path.cwd()


APP_ROOT = resource_root()


def app_data_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "YTDL"
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return APP_ROOT


USER_DATA_DIR = app_data_dir()
SETTINGS_PATH = USER_DATA_DIR / "settings.json"


def background_image_path() -> Path:
    root = resource_root()
    for relative in ("pic/BG.jpg", "assets/BG.jpg", "BG.jpg"):
        path = root / relative
        if path.is_file():
            return path
    return root / "pic" / "BG.jpg"


def background_svg_path() -> Path:
    root = resource_root()
    for relative in ("pic/BG.svg", "assets/BG.svg", "BG.svg"):
        path = root / relative
        if path.is_file():
            return path
    return root / "pic" / "BG.svg"


def app_icon_ico_path() -> Path:
    root = resource_root()
    for relative in ("pic/YTDL_LOGO.ico", "assets/icon.ico", "YTDL_LOGO.ico"):
        path = root / relative
        if path.is_file():
            return path
    return root / "pic" / "YTDL_LOGO.ico"


def app_icon_png_path() -> Path:
    root = resource_root()
    for relative in ("pic/YTDL_LOGO.png", "assets/icon.png", "assets/icon_macos.png", "YTDL_LOGO.png"):
        path = root / relative
        if path.is_file():
            return path
    return root / "pic" / "YTDL_LOGO.png"


# Kept for compatibility with older code paths / packaging tools.
BACKGROUND_IMAGE = background_image_path()
BACKGROUND_SVG = background_svg_path()
APP_ICON_ICO = app_icon_ico_path()
APP_ICON_PNG = app_icon_png_path()
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Local app version. Bump this when you publish a matching GitHub Release tag
# (tag "v1.0.1" or "1.0.1" both compare as 1.0.1).
APP_VERSION = "1.0.0"
# GitHub "owner/repo" used for Releases update check.
# Leave empty to disable. Example: "yourname/YTDL"
# Override at runtime with env var YTDL_GITHUB_REPO if needed.
GITHUB_REPO = (os.environ.get("YTDL_GITHUB_REPO") or "WiKiVibe/YTDL").strip()

VIDEO_QUALITIES = ("AUTO", "4K", "HD")
VIDEO_CODECS = ("AUTO", "H264", "AV1")
AUDIO_FORMATS = ("WAV", "MP3", "AAC")
COOKIE_BROWSER_OPTIONS = ("AUTO", "OFF", "brave", "chrome", "edge", "firefox")
COOKIE_BROWSER_LABELS = {
    "AUTO": "自動（建議）",
    "OFF": "關閉",
    "brave": "Brave",
    "chrome": "Chrome",
    "edge": "Edge",
    "firefox": "Firefox",
}
COOKIE_BROWSER_DETECT_ORDER = ("brave", "chrome", "edge", "firefox")
_COOKIE_BROWSER_DEFAULT = object()

BG = "#140605"
SURFACE = "0x12FFFFFF"
SURFACE_STRONG = "0x28EAF2FF"
SURFACE_SOFT = "0x0AFFFFFF"
BORDER = "0x76FFFFFF"
BORDER_ACTIVE = "#F0524D"
TEXT = "#F9FAFB"
TEXT_MUTED = "#A1A1AA"
TEXT_SOFT = "#D4D4D8"
YT_RED = "#F0524D"
YT_RED_DARK = "#D73A36"
TRANSCODE_BLUE = "#60A5FA"
PILL_RADIUS = 999
CARD_RADIUS = 22
GLASS_SHADOW = "0x66000000"


DEFAULT_WINDOW_WIDTH = 895
DEFAULT_WINDOW_HEIGHT = 1425


def is_packaged_app() -> bool:
    if getattr(sys, "frozen", False):
        return True
    try:
        exe = str(Path(sys.executable).resolve())
        # Flet/serious_python macOS: .../YTDL.app/Contents/MacOS/YTDL
        if sys.platform == "darwin" and ".app/Contents/MacOS" in exe.replace("\\", "/"):
            return True
    except Exception:
        pass
    return False


def startup_log(message: str) -> None:
    """Append a line to a startup log (helps debug black-screen packaged builds)."""
    try:
        log_dir = app_data_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / "startup.log"
        line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception:
        pass

JS_RUNTIME_DIR = APP_ROOT / "bin"
YTDLP_CACHE_DIR = USER_DATA_DIR / "cache" / "yt-dlp"


def parse_version_tuple(version: str) -> tuple[int, ...]:
    """Parse 'v1.2.3' / '1.2.3-beta' into a comparable int tuple."""
    text = (version or "").strip()
    if text.lower().startswith("v"):
        text = text[1:]
    parts: list[int] = []
    for chunk in text.split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    while parts and parts[-1] == 0 and len(parts) > 1:
        parts.pop()
    return tuple(parts) if parts else (0,)


def is_remote_version_newer(remote: str, local: str) -> bool:
    return parse_version_tuple(remote) > parse_version_tuple(local)


def fetch_latest_github_release(
    repo: str,
    *,
    timeout: float = 6.0,
) -> dict[str, str] | None:
    """Return {tag, url} for the latest GitHub Release, or None on failure."""
    repo = (repo or "").strip().strip("/")
    if not repo or "/" not in repo:
        return None
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    request = urllib.request.Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"YTDL/{APP_VERSION}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    tag = str(payload.get("tag_name") or payload.get("name") or "").strip()
    if not tag:
        return None
    html_url = str(payload.get("html_url") or f"https://github.com/{repo}/releases/latest").strip()
    return {"tag": tag, "url": html_url}


def bundled_deno_path() -> Path | None:
    deno = JS_RUNTIME_DIR / ("deno.exe" if os.name == "nt" else "deno")
    if deno.exists():
        return deno
    system_deno = shutil.which("deno")
    return Path(system_deno) if system_deno else None


def ensure_js_runtime_on_path() -> Path | None:
    """Make a bundled Deno (bin/deno) discoverable by yt-dlp.

    Newer yt-dlp needs a JS runtime to extract YouTube; without one it falls back
    to limited clients and hits the 'confirm you're not a bot' check. Shipping
    Deno and putting it on PATH lets most downloads work without cookies."""
    try:
        deno = bundled_deno_path()
        if deno:
            bin_dir = deno.parent
            current = os.environ.get("PATH", "")
            if str(bin_dir) not in current.split(os.pathsep):
                os.environ["PATH"] = str(bin_dir) + os.pathsep + current
            return deno
    except Exception:
        pass
    return None


def apply_js_runtime_options(options: dict[str, Any], log: Callable[[str], None] | None = None) -> None:
    deno = ensure_js_runtime_on_path()
    if deno:
        options["js_runtimes"] = {"deno": {"path": str(deno)}}
        options["remote_components"] = ["ejs:github"]
        if log:
            log("使用內建 Deno JavaScript runtime。")
    elif log:
        log("未找到 Deno JavaScript runtime，YouTube 可能要求登入驗證。")


def enable_high_dpi() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def dpi_scale() -> float:
    """Primary-monitor display scaling factor (1.0 = 100%, 1.5 = 150%)."""
    if os.name != "nt":
        return 1.0
    try:
        import ctypes

        hdc = ctypes.windll.user32.GetDC(0)
        try:
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        finally:
            ctypes.windll.user32.ReleaseDC(0, hdc)
        if dpi and dpi > 0:
            return dpi / 96.0
    except Exception:
        return 1.0
    return 1.0


def screen_work_area() -> tuple[int, int] | None:
    """Return the usable (width, height) of the primary monitor in pixels."""
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            SPI_GETWORKAREA = 0x0030
            rect = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
                width = int(rect.right - rect.left)
                height = int(rect.bottom - rect.top)
                if width > 0 and height > 0:
                    return width, height
        except Exception:
            return None
        return None

    # macOS / Linux: avoid a 1425px-tall window that can leave content looking "blank"
    # on laptop screens when work-area APIs are unavailable.
    if sys.platform == "darwin":
        # Logical-ish safe defaults for MacBook Air / 13–15" displays.
        return (1440, 900)
    return (1280, 800)


class DownloadCancelled(Exception):
    pass


@dataclass
class VideoItem:
    title: str
    url: str
    uploader: str = ""
    duration: str = ""
    checked: bool = True


@dataclass
class Settings:
    output_dir: str
    default_video_quality: str = "AUTO"
    default_video_codec: str = "AUTO"
    default_audio_format: str = "MP3"
    cookie_browser: str = "OFF"
    cookie_file: str = ""
    open_folder_when_done: bool = False
    delete_temp_source: bool = True
    prefer_nvenc: bool = True


# Manual (uploader) subtitles only — never YouTube auto-generated captions.
DEFAULT_SUBTITLE_LANGS = ["zh-TW", "zh-Hant", "zh-Hans", "zh", "en", "en.*"]


@dataclass
class AppState:
    settings: Settings
    yt_dlp: Any | None = None
    ffmpeg_path: str | None = None
    ready: bool = False
    urls: list[str] = field(default_factory=list)
    items: list[VideoItem] = field(default_factory=list)
    mode: str = "video"
    video_quality: str = "AUTO"
    video_codec: str = "AUTO"
    audio_format: str = "MP3"
    download_manual_subs: bool = False
    current_step: str = "url"
    last_output_dir: str = ""


def get_downloads_dir() -> Path:
    if os.name == "nt":
        try:
            import winreg

            keys = (
                (
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
                ),
                (
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
                ),
            )
            names = ("{374DE290-123F-4565-9164-39C4925E467B}", "Downloads")
            for root, key_name in keys:
                with winreg.OpenKey(root, key_name) as key:
                    for name in names:
                        try:
                            value, _value_type = winreg.QueryValueEx(key, name)
                        except FileNotFoundError:
                            continue
                        path = Path(os.path.expandvars(str(value)))
                        if path:
                            return path
        except Exception:
            pass
    return Path.home() / "Downloads"


def default_settings() -> Settings:
    return Settings(output_dir=str(get_downloads_dir()))


def load_settings() -> Settings:
    settings = default_settings()
    if not SETTINGS_PATH.exists():
        return settings
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return settings
    for key, value in data.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    if not settings.output_dir:
        settings.output_dir = str(get_downloads_dir())
    # Browser-cookie controls were removed from the UI. Old settings must not
    # keep forcing Chrome/Brave cookies and reintroduce database-lock errors.
    settings.cookie_browser = "OFF"
    settings.cookie_file = ""
    return settings


def save_settings(settings: Settings) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(settings.__dict__, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def browser_cookie_source_exists(browser: str) -> bool:
    if os.name != "nt":
        return False
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    roaming = Path(os.environ.get("APPDATA", ""))
    paths = {
        "brave": local / "BraveSoftware" / "Brave-Browser" / "User Data",
        "chrome": local / "Google" / "Chrome" / "User Data",
        "edge": local / "Microsoft" / "Edge" / "User Data",
        "firefox": roaming / "Mozilla" / "Firefox" / "Profiles",
    }
    path = paths.get(browser.lower())
    return bool(path and path.exists())


def normalize_cookie_browser(value: str | None) -> str:
    normalized = (value or "AUTO").strip()
    upper = normalized.upper()
    if upper in ("", "AUTO"):
        return "AUTO"
    if upper in ("OFF", "NONE", "NO", "FALSE", "0"):
        return "OFF"
    lower = normalized.lower()
    if lower in COOKIE_BROWSER_OPTIONS:
        return lower
    return "AUTO"


def resolve_cookie_browser(value: str | None) -> str | None:
    normalized = normalize_cookie_browser(value)
    if normalized == "OFF":
        return None
    if normalized == "AUTO":
        for browser in COOKIE_BROWSER_DETECT_ORDER:
            if browser_cookie_source_exists(browser):
                return browser
        return None
    return normalized


def cookie_browser_candidates(value: str | None) -> list[str | None]:
    normalized = normalize_cookie_browser(value)
    if normalized == "OFF":
        return [None]
    if normalized == "AUTO":
        browsers = [
            browser for browser in COOKIE_BROWSER_DETECT_ORDER
            if browser_cookie_source_exists(browser)
        ]
        return browsers or [None]
    return [normalized]


def cookie_browser_label(value: str | None) -> str:
    normalized = normalize_cookie_browser(value)
    return COOKIE_BROWSER_LABELS.get(normalized, normalized)


DEFAULT_COOKIE_FILE = USER_DATA_DIR / "cookies.txt"


def resolve_cookie_file(settings: Settings) -> str | None:
    """A cookies.txt path to use, if any. Explicit setting wins, else auto-detect
    a cookies.txt sitting next to the app (e.g. ./cookies.txt)."""
    candidate = (settings.cookie_file or "").strip()
    if candidate:
        path = Path(candidate).expanduser()
        if path.exists() and path.is_file():
            return str(path)
    if DEFAULT_COOKIE_FILE.exists() and DEFAULT_COOKIE_FILE.is_file():
        return str(DEFAULT_COOKIE_FILE)
    return None


def apply_cookie_file(
    options: dict[str, Any],
    settings: Settings,
    log: Callable[[str], None] | None = None,
) -> bool:
    """Use a cookies.txt file if available. Returns True if applied.

    A cookies.txt avoids Chrome/Brave/Edge App-Bound Encryption (the
    'Failed to decrypt with DPAPI' error), so it takes priority over browser
    cookies when present."""
    cookie_file = resolve_cookie_file(settings)
    if not cookie_file:
        return False
    options["cookiefile"] = cookie_file
    if log:
        log(f"使用 Cookies 檔案：{cookie_file}")
    return True


def apply_cookie_options_for_browser(
    options: dict[str, Any],
    browser: str | None,
    log: Callable[[str], None] | None = None,
) -> None:
    if not browser:
        return
    options["cookiesfrombrowser"] = (browser, None, None, None)
    if log:
        label = COOKIE_BROWSER_LABELS.get(browser, browser)
        log(f"使用 {label} 瀏覽器 Cookies。")


def apply_cookie_options(
    options: dict[str, Any],
    settings: Settings,
    log: Callable[[str], None] | None = None,
) -> None:
    # A cookies.txt file (if present) takes priority and skips browser cookies.
    if apply_cookie_file(options, settings, log):
        return
    apply_cookie_options_for_browser(options, resolve_cookie_browser(settings.cookie_browser), log)


def format_duration(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        seconds = int(float(value))
    except (TypeError, ValueError):
        return str(value)

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def format_bytes(value: Any) -> str:
    if not value:
        return ""
    try:
        size = float(value)
    except (TypeError, ValueError):
        return ""
    units = ("B", "KB", "MB", "GB", "TB")
    unit = 0
    while size >= 1024 and unit < len(units) - 1:
        size /= 1024
        unit += 1
    return f"{size:.1f} {units[unit]}"


def parse_input_urls(text: str) -> list[str]:
    urls: list[str] = []
    for match in re.findall(r"https?://[^\s<>'\"]+", text or ""):
        url = match.strip().strip("<>").rstrip(").,;，。）」』】")
        if url and url not in urls:
            urls.append(url)
    if urls:
        return urls

    for line in (text or "").splitlines():
        url = line.strip().strip("<>")
        if url and url not in urls:
            urls.append(url)
    return urls


def fallback_items_from_urls(urls: list[str]) -> list[VideoItem]:
    return [
        VideoItem(title=url, url=url)
        for url in urls
        if url.lower().startswith(("http://", "https://"))
    ]


def short_error(text: str, limit: int = 140) -> str:
    message = " ".join(str(text).split())
    if len(message) <= limit:
        return message
    return f"{message[:limit - 3]}..."


def friendly_error_message(error: Any) -> str:
    message = str(error)
    if is_cookie_decrypt_error(error):
        return (
            "下載失敗：YouTube 登入驗證被擋。"
            "請重新執行 install.bat 確認 Deno 已安裝完成，或稍後換網路再試。"
        )
    if is_cookie_database_error(error):
        return (
            "下載失敗：YouTube 驗證資料被鎖住。"
            "請關閉瀏覽器背景程序後再試；程式會優先使用 Deno，不需要手動選 Cookies。"
        )
    if is_cookie_auth_error(error):
        return (
            "下載失敗：YouTube 要求登入或驗證。"
            "請重新執行 install.bat 確認 Deno 已安裝完成，或稍後換網路再試。"
        )
    return f"下載失敗：{short_error(message, 180)}"


def is_cookie_decrypt_error(error: Any) -> bool:
    lower = str(error).lower()
    return (
        "failed to decrypt with dpapi" in lower
        or "dpapi" in lower
        or "10927" in lower
        or "app-bound" in lower
        or "failed to decrypt" in lower
    )


def is_cookie_database_error(error: Any) -> bool:
    lower = str(error).lower()
    return (
        "could not copy chrome cookie database" in lower
        or "cookie database" in lower
        or "database is locked" in lower
    )


def is_cookie_auth_error(error: Any) -> bool:
    lower = str(error).lower()
    return "not a bot" in lower or "cookies-from-browser" in lower or "--cookies" in lower


def extract_info_with_cookie_fallback(
    *,
    yt_dlp: Any,
    base_options: dict[str, Any],
    settings: Settings,
    url: str,
    download: bool,
    log: Callable[[str], None],
) -> dict[str, Any] | None:
    # A cookies.txt file (if present) is the most reliable path — use it alone.
    cookie_options = dict(base_options)
    if apply_cookie_file(cookie_options, settings, log):
        with yt_dlp.YoutubeDL(cookie_options) as ydl:
            return ydl.extract_info(url, download=download)

    last_exc: Exception | None = None

    def with_player_client(options: dict[str, Any], client: str | None) -> dict[str, Any]:
        opts = dict(options)
        if client:
            opts["extractor_args"] = {"youtube": {"player_client": [client]}}
        return opts

    # Step 1: try several YouTube clients WITHOUT cookies — these often pass the
    # "confirm you're not a bot" check with zero setup for end users.
    client_attempts: list[str | None] = [None, "tv", "web_safari", "mweb"]
    for client in client_attempts:
        options = with_player_client(base_options, client)
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                return ydl.extract_info(url, download=download)
        except Exception as exc:
            last_exc = exc
            # Only keep trying other clients for bot/auth-type blocks.
            if not (is_cookie_auth_error(exc) or is_cookie_decrypt_error(exc)):
                # A real error (e.g. video unavailable) — stop early.
                if client is None:
                    raise
                break
            if client is not None:
                log(f"player_client={client} 仍被 YouTube 擋，改試下一個。")

    # Step 2: fall back to browser cookies (for the minority still blocked).
    candidates = cookie_browser_candidates(settings.cookie_browser)
    auto_mode = normalize_cookie_browser(settings.cookie_browser) == "AUTO"
    for index, browser in enumerate(candidates):
        if not browser:
            continue
        options = dict(base_options)
        apply_cookie_options_for_browser(options, browser, log)
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                return ydl.extract_info(url, download=download)
        except Exception as exc:
            last_exc = exc
            should_try_next = (
                auto_mode
                and index < len(candidates) - 1
                and (
                    is_cookie_database_error(exc)
                    or is_cookie_auth_error(exc)
                    or is_cookie_decrypt_error(exc)
                )
            )
            if not should_try_next:
                raise
            label = COOKIE_BROWSER_LABELS.get(browser, browser)
            log(f"{label} Cookies 無法通過 YouTube 驗證，改試下一個瀏覽器。")

    if last_exc:
        raise last_exc
    return None


def normalize_video_url(entry: dict[str, Any], fallback_url: str) -> str:
    webpage_url = entry.get("webpage_url") or entry.get("original_url")
    if webpage_url:
        return str(webpage_url)

    raw_url = entry.get("url") or entry.get("id") or fallback_url
    if isinstance(raw_url, str) and raw_url.startswith(("http://", "https://")):
        return raw_url

    ie_key = str(entry.get("ie_key") or "").lower()
    if isinstance(raw_url, str) and ("youtube" in ie_key or re.fullmatch(r"[\w-]{11}", raw_url)):
        return f"https://www.youtube.com/watch?v={raw_url}"

    return str(raw_url)


def flatten_info(info: dict[str, Any], source_url: str) -> list[VideoItem]:
    entries = info.get("entries")
    if entries:
        items: list[VideoItem] = []
        for entry in entries:
            if not entry:
                continue
            title = entry.get("title") or entry.get("id") or "未命名影片"
            items.append(
                VideoItem(
                    title=str(title),
                    url=normalize_video_url(entry, source_url),
                    uploader=str(entry.get("uploader") or entry.get("channel") or ""),
                    duration=format_duration(entry.get("duration")),
                )
            )
        return items

    return [
        VideoItem(
            title=str(info.get("title") or source_url),
            url=normalize_video_url(info, source_url),
            uploader=str(info.get("uploader") or info.get("channel") or ""),
            duration=format_duration(info.get("duration")),
        )
    ]


def height_filter(quality: str) -> str:
    if quality == "4K":
        return "[height<=2160]"
    if quality == "HD":
        return "[height<=1080]"
    return ""


def best_source_selector(quality: str) -> str:
    height = height_filter(quality)
    fallback_best = f"best{height}/best" if height else "best"
    return f"bestvideo*{height}+bestaudio/{fallback_best}"


def video_format_selector(quality: str, codec: str) -> str:
    height = height_filter(quality)
    fallback_best = f"best{height}/best" if height else "best"
    if codec == "H264":
        return (
            f"bestvideo*{height}[vcodec^=avc1]+bestaudio/"
            f"best{height}[vcodec^=avc1]/{fallback_best}"
        )
    if codec == "AV1":
        return (
            f"bestvideo*{height}[vcodec^=av01]+bestaudio/"
            f"best{height}[vcodec^=av01]/{fallback_best}"
        )
    return best_source_selector(quality)


def should_transcode_4k_h264(quality: str, codec: str) -> bool:
    # Explicit 4K + H.264, and AUTO (lazy "best playable"): download the best 4K
    # source then transcode to H.264 MP4 with 320k AAC audio.
    if quality == "4K" and codec == "H264":
        return True
    if quality == "AUTO" and codec == "AUTO":
        return True
    return False


def command_output(command: list[str], timeout: int = 10) -> str:
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
        return result.stdout or ""
    except Exception:
        return ""


def ffmpeg_has_encoder(ffmpeg_path: str, encoder: str) -> bool:
    return encoder in command_output([ffmpeg_path, "-hide_banner", "-encoders"], timeout=15)


def has_nvidia_gpu() -> bool:
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return False
    output = command_output([nvidia_smi, "-L"], timeout=8)
    return "GPU" in output or "NVIDIA" in output.upper()


def ffmpeg_progress_percent(line: str, duration: float | None) -> float | None:
    if not duration or duration <= 0:
        return None
    # ffmpeg's -progress emits one key=value per line. We accept the three
    # variants ffmpeg ships across versions so the bar tracks reality on every
    # build instead of staying at 0%.
    if line.startswith("out_time_us="):
        try:
            out_time_us = int(line.split("=", 1)[1].strip())
        except ValueError:
            return None
        return min(100.0, out_time_us / (duration * 1_000_000) * 100)
    if line.startswith("out_time_ms="):
        # Despite the name, modern ffmpeg writes microseconds here.
        try:
            out_time_us = int(line.split("=", 1)[1].strip())
        except ValueError:
            return None
        return min(100.0, out_time_us / (duration * 1_000_000) * 100)
    if line.startswith("out_time="):
        # Fallback: human-formatted HH:MM:SS.micro
        raw = line.split("=", 1)[1].strip()
        if not raw or raw.upper() == "N/A":
            return None
        try:
            parts = raw.split(":")
            if len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
            elif len(parts) == 2:
                hours = 0
                minutes = int(parts[0])
                seconds = float(parts[1])
            else:
                hours = 0
                minutes = 0
                seconds = float(parts[0])
        except ValueError:
            return None
        elapsed = hours * 3600 + minutes * 60 + seconds
        return min(100.0, elapsed / duration * 100)
    return None


def find_downloaded_filepath(info: dict[str, Any], output_dir: Path, source_for_transcode: bool) -> Path | None:
    candidates: list[Path] = []
    for key in ("filepath", "_filename", "filename"):
        value = info.get(key)
        if value:
            candidates.append(Path(value))

    for download in info.get("requested_downloads") or []:
        if isinstance(download, dict):
            for key in ("filepath", "_filename", "filename"):
                value = download.get(key)
                if value:
                    candidates.append(Path(value))

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    pattern = "*_YTDL_source.*" if source_for_transcode else "*_YTDL.*"
    files = [path for path in output_dir.glob(pattern) if path.is_file()]
    if not files:
        return None
    return max(files, key=lambda path: path.stat().st_mtime)


def newest_output_file(output_dir: Path) -> Path | None:
    files = [
        path
        for path in output_dir.glob("*_YTDL*.*")
        if path.is_file() and not path.name.endswith("_YTDL_source." + path.suffix.lstrip("."))
    ]
    if not files:
        files = [path for path in output_dir.glob("*.*") if path.is_file()]
    if not files:
        return None
    return max(files, key=lambda path: path.stat().st_mtime)


def final_h264_path(source_path: Path) -> Path:
    stem = source_path.stem
    if stem.endswith("_YTDL_source"):
        stem = stem[: -len("_source")]
    elif not stem.endswith("_YTDL"):
        stem = f"{stem}_YTDL"
    return source_path.with_name(f"{stem}.mp4")


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def load_background_bytes() -> bytes | None:
    image_path = background_image_path()
    if image_path.exists():
        try:
            return image_path.read_bytes()
        except OSError:
            return None
    svg_path = background_svg_path()
    if svg_path.exists():
        try:
            svg = svg_path.read_text(encoding="utf-8")
        except OSError:
            return None
        match = re.search(r"data:image/jpeg;base64,([^\"]+)", svg)
        if match:
            import base64

            try:
                return base64.b64decode(match.group(1))
            except Exception:
                return None
    return None


def make_background_control() -> ft.Control:
    """Background for the shell. Prefer solid color if image fails (packaged builds)."""
    data = load_background_bytes()
    if not data:
        return ft.Container(bgcolor=BG, expand=True)
    try:
        import base64

        encoded = base64.b64encode(data).decode("ascii")
        # Prefer src_base64 when available (more reliable in packaged Flutter views).
        image_kwargs: dict[str, Any] = {
            "fit": ft.BoxFit.COVER,
            "expand": True,
        }
        try:
            return ft.Image(src_base64=encoded, **image_kwargs)
        except TypeError:
            return ft.Image(src=data, **image_kwargs)
    except Exception:
        return ft.Container(bgcolor=BG, expand=True)


class QueueLogger:
    def __init__(self, emit: Callable[[str, str], None]) -> None:
        self.emit = emit

    def debug(self, msg: str) -> None:
        if msg and not msg.startswith("[debug]"):
            self.emit("log", msg)

    def info(self, msg: str) -> None:
        if msg:
            self.emit("log", msg)

    def warning(self, msg: str) -> None:
        if msg:
            self.emit("log", f"警告：{msg}")

    def error(self, msg: str) -> None:
        if msg:
            self.emit("log", f"錯誤：{msg}")


def apply_manual_subtitle_options(options: dict[str, Any], download_manual_subs: bool) -> None:
    """Download uploader/official CC only; never YouTube auto captions."""
    if not download_manual_subs:
        return
    options["writesubtitles"] = True
    options["writeautomaticsub"] = False
    options["subtitleslangs"] = list(DEFAULT_SUBTITLE_LANGS)
    postprocessors = list(options.get("postprocessors") or [])
    postprocessors.append({"key": "FFmpegSubtitlesConvertor", "format": "srt"})
    options["postprocessors"] = postprocessors


def build_download_options(
    *,
    output_dir: Path,
    ffmpeg_path: str | None,
    quality: str,
    codec: str,
    audio_format: str,
    mode: str,
    settings: Settings,
    cancel_event: threading.Event,
    emit: Callable[..., None],
    source_for_transcode: bool = False,
    cookie_browser: str | None | object = _COOKIE_BROWSER_DEFAULT,
    progress_tracker: dict[str, Any] | None = None,
    download_manual_subs: bool = False,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        YTDLP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    # Shared state for honest multi-stream / multi-item progress accounting.
    # Keys we maintain:
    #   item_index, item_total: 1-based index of the current item and total items in the job.
    #   current_file: filename of the stream currently being downloaded.
    #   stream_index: 0 = first stream of this item (video), 1 = second (audio), ...
    #   item_done_bytes: bytes already downloaded for finished streams of THIS item.
    #   item_total_bytes_seen: best estimate of this item's total bytes so far
    #     (sum of completed-stream totals + current stream's total estimate).
    tracker = progress_tracker if progress_tracker is not None else {}
    tracker.setdefault("item_index", 1)
    tracker.setdefault("item_total", 1)
    tracker.setdefault("current_file", "")
    tracker.setdefault("stream_index", 0)
    tracker.setdefault("item_done_bytes", 0)
    tracker.setdefault("item_total_bytes_seen", 0)

    # For video downloads we expect two streams (video + audio) to be merged.
    # We weight them so the overall bar moves smoothly through the item:
    # video covers 0-90%, audio covers 90-100% (typical size ratio).
    video_two_stream = (mode == "video")
    stream_weights = [0.90, 0.10] if video_two_stream else [1.0]

    def _stream_label(idx: int) -> str:
        if video_two_stream:
            return "視訊" if idx == 0 else "音訊"
        return ""

    def _emit_item_percent(item_percent: float, detail: str) -> None:
        # Map this item's 0-100% onto the whole-job 0-100% range.
        item_percent = max(0.0, min(100.0, item_percent))
        total_items = max(1, int(tracker.get("item_total", 1) or 1))
        index = max(1, int(tracker.get("item_index", 1) or 1))
        overall = ((index - 1) + item_percent / 100.0) / total_items * 100.0
        emit("progress", overall, detail, "download")

    def progress_hook(data: dict[str, Any]) -> None:
        if cancel_event.is_set():
            raise DownloadCancelled()

        status = data.get("status")
        filename = (
            data.get("tmpfilename")
            or data.get("filename")
            or (data.get("info_dict") or {}).get("filename")
            or ""
        )

        # Detect stream change: a new tmpfilename means yt-dlp started the next
        # stream (e.g. video done, audio starting). Roll the finished stream's
        # bytes into item_done_bytes so the bar keeps moving forward instead of
        # resetting to 0%.
        if filename and filename != tracker["current_file"]:
            if tracker["current_file"]:
                tracker["item_done_bytes"] = int(
                    tracker["item_total_bytes_seen"]
                )
                tracker["stream_index"] = int(tracker.get("stream_index", 0)) + 1
            tracker["current_file"] = filename

        if status == "downloading":
            downloaded = int(data.get("downloaded_bytes") or 0)
            total = int(data.get("total_bytes") or data.get("total_bytes_estimate") or 0)

            idx = int(tracker.get("stream_index", 0))
            label = _stream_label(idx)

            if total > 0:
                # Use weighted mapping when we know how many streams to expect.
                if idx < len(stream_weights):
                    base = sum(stream_weights[:idx]) * 100.0
                    span = stream_weights[idx] * 100.0
                    stream_pct = min(100.0, downloaded / total * 100.0)
                    item_pct = base + span * (stream_pct / 100.0)
                else:
                    # Unexpected extra stream - fall back to byte-sum estimate.
                    seen = tracker["item_done_bytes"] + total
                    tracker["item_total_bytes_seen"] = max(
                        tracker["item_total_bytes_seen"], seen
                    )
                    denom = max(1, tracker["item_total_bytes_seen"])
                    item_pct = (tracker["item_done_bytes"] + downloaded) / denom * 100.0
                    stream_pct = min(100.0, downloaded / total * 100.0)

                # Always update the per-item byte tally so a stream change can
                # close it out correctly.
                tracker["item_total_bytes_seen"] = (
                    tracker["item_done_bytes"] + total
                )

                if label:
                    detail = (
                        f"{label} {stream_pct:5.1f}%  "
                        f"{format_bytes(downloaded)} / {format_bytes(total)}"
                    )
                else:
                    detail = (
                        f"{stream_pct:5.1f}%  "
                        f"{format_bytes(downloaded)} / {format_bytes(total)}"
                    )
                _emit_item_percent(item_pct, detail)
            else:
                # No total known - show byte count and leave the bar where it is.
                prefix = f"{label} " if label else ""
                emit(
                    "progress",
                    -1.0,
                    f"{prefix}已下載 {format_bytes(downloaded)}",
                    "download",
                )
        elif status == "finished":
            # A stream finished. Don't claim 100% of the item yet - there may be
            # another stream (e.g. audio after video) or a merge step coming.
            # Just roll its bytes into the item tally so the bar holds steady.
            total = int(data.get("total_bytes") or data.get("total_bytes_estimate") or 0)
            if total > 0:
                # Set baseline to the cumulative seen total.
                tracker["item_done_bytes"] = max(
                    tracker["item_done_bytes"], tracker["item_total_bytes_seen"]
                )
            emit("progress", -1.0, "串流完成，準備下一段…", "download")

    def postprocessor_hook(data: dict[str, Any]) -> None:
        if cancel_event.is_set():
            raise DownloadCancelled()
        pp = data.get("postprocessor") or "後處理"
        status = data.get("status")
        if status == "started":
            emit("status", f"{pp} 處理中...")
        elif status == "finished":
            emit("status", f"{pp} 完成")

    suffix = "_YTDL_source" if source_for_transcode else "_YTDL"
    options: dict[str, Any] = {
        "outtmpl": str(output_dir / f"%(title).200s{suffix}.%(ext)s"),
        "windowsfilenames": True,
        "continuedl": True,
        "retries": 10,
        "fragment_retries": 10,
        "noplaylist": True,
        "ignoreerrors": False,
        "quiet": True,
        "no_warnings": False,
        "logger": QueueLogger(lambda kind, value: emit(kind, value)),
        "progress_hooks": [progress_hook],
        "postprocessor_hooks": [postprocessor_hook],
        "concurrent_fragment_downloads": 6,
        "cachedir": str(YTDLP_CACHE_DIR),
    }

    if ffmpeg_path:
        options["ffmpeg_location"] = ffmpeg_path

    apply_js_runtime_options(options, lambda message: emit("log", message))

    if cookie_browser is _COOKIE_BROWSER_DEFAULT:
        apply_cookie_options(options, settings, lambda message: emit("log", message))
    else:
        apply_cookie_options_for_browser(options, cookie_browser if isinstance(cookie_browser, str) else None, lambda message: emit("log", message))

    if mode == "audio":
        preferred_codec = audio_format.lower()
        postprocessor: dict[str, Any] = {
            "key": "FFmpegExtractAudio",
            "preferredcodec": preferred_codec,
        }
        if audio_format in ("MP3", "AAC"):
            postprocessor["preferredquality"] = "320"
            options["postprocessor_args"] = ["-b:a", "320k"]
        options.update({"format": "bestaudio/best", "postprocessors": [postprocessor]})
        apply_manual_subtitle_options(options, download_manual_subs)
        return options

    if source_for_transcode:
        options["format"] = best_source_selector("4K")
        options["merge_output_format"] = "mkv"
        apply_manual_subtitle_options(options, download_manual_subs)
        return options

    options["format"] = video_format_selector(quality, codec)
    options["merge_output_format"] = "mkv" if codec in ("AUTO", "AV1") else "mp4"
    apply_manual_subtitle_options(options, download_manual_subs)
    return options


class DownloadJob:
    def __init__(
        self,
        *,
        yt_dlp: Any,
        ffmpeg_path: str | None,
        settings: Settings,
        items: list[VideoItem],
        mode: str,
        quality: str,
        codec: str,
        audio_format: str,
        output_dir: Path,
        callbacks: dict[str, Callable[..., None]],
        download_manual_subs: bool = False,
    ) -> None:
        self.yt_dlp = yt_dlp
        self.ffmpeg_path = ffmpeg_path
        self.settings = settings
        self.items = items
        self.mode = mode
        self.quality = quality
        self.codec = codec
        self.audio_format = audio_format
        self.download_manual_subs = download_manual_subs
        self.output_dir = output_dir
        self.callbacks = callbacks
        self.cancel_event = threading.Event()
        self.nvenc_available_cache: bool | None = None
        self.last_file: Path | None = None
        # Shared progress tracker used by build_download_options so the bar can
        # report honest, monotonically increasing progress across streams and
        # across multiple items in a single job.
        self.progress_tracker: dict[str, Any] = {
            "item_index": 1,
            "item_total": max(1, len(items)),
            "current_file": "",
            "stream_index": 0,
            "item_done_bytes": 0,
            "item_total_bytes_seen": 0,
        }

    def cancel(self) -> None:
        self.cancel_event.set()

    def emit(self, kind: str, *values: Any) -> None:
        callback = self.callbacks.get(kind)
        if callback:
            callback(*values)

    def _reset_item_progress(self, index: int, total: int) -> None:
        """Prepare the tracker for a new item without zeroing the bar mid-job."""
        self.progress_tracker["item_index"] = index
        self.progress_tracker["item_total"] = max(1, total)
        self.progress_tracker["current_file"] = ""
        self.progress_tracker["stream_index"] = 0
        self.progress_tracker["item_done_bytes"] = 0
        self.progress_tracker["item_total_bytes_seen"] = 0

    def run(self) -> None:
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            total = len(self.items)
            transcode_4k_h264 = (
                self.mode == "video" and should_transcode_4k_h264(self.quality, self.codec)
            )
            for index, item in enumerate(self.items, start=1):
                if self.cancel_event.is_set():
                    raise DownloadCancelled()
                self._reset_item_progress(index, total)
                self.emit("status", f"下載中 {index}/{total}：{item.title}")
                self.emit("log", f"開始下載：{item.title}")
                if transcode_4k_h264:
                    self.download_then_transcode(item)
                else:
                    self.download_direct(item)
                # Pin this item's bracket to its end value (e.g. 1/2 = 50%).
                # Covers the case where a single-stream (pre-muxed) download
                # finishes at the weighted 90% mark instead of 100%.
                bracket_end = index / max(1, total) * 100.0
                self.emit("progress", bracket_end, f"{bracket_end:.0f}%", "download")
            self.emit("progress", 100.0, "100%", "download")
            done_path = str(self.last_file) if self.last_file else None
            self.emit("done", True, f"完成：{total} 個項目", done_path)
        except DownloadCancelled:
            self.emit("done", False, "下載已停止。", None)
        except Exception as exc:
            self.emit("log", f"下載失敗：{exc}")
            self.emit("done", False, friendly_error_message(exc), None)

    def download_direct(self, item: VideoItem) -> None:
        options = build_download_options(
            output_dir=self.output_dir,
            ffmpeg_path=self.ffmpeg_path,
            quality=self.quality,
            codec=self.codec,
            audio_format=self.audio_format,
            mode=self.mode,
            settings=self.settings,
            cancel_event=self.cancel_event,
            emit=self.emit,
            cookie_browser=None,
            progress_tracker=self.progress_tracker,
            download_manual_subs=self.download_manual_subs,
        )
        if self.download_manual_subs:
            self.emit("log", "已啟用：下載頻道主 CC 字幕（不含 YouTube 自動字幕）。")
        info = extract_info_with_cookie_fallback(
            yt_dlp=self.yt_dlp,
            base_options=options,
            settings=self.settings,
            url=item.url,
            download=True,
            log=lambda message: self.emit("log", message),
        )
        found = find_downloaded_filepath(info or {}, self.output_dir, source_for_transcode=False)
        if found is None:
            found = newest_output_file(self.output_dir)
        if found is not None:
            self.last_file = found

    def download_then_transcode(self, item: VideoItem) -> None:
        if not self.ffmpeg_path:
            raise RuntimeError("找不到 FFmpeg，無法轉碼。")

        self.emit("log", "4K H.264：先下載 4K 原始串流，再轉碼成 4K H.264 MP4。")
        options = build_download_options(
            output_dir=self.output_dir,
            ffmpeg_path=self.ffmpeg_path,
            quality=self.quality,
            codec=self.codec,
            audio_format=self.audio_format,
            mode=self.mode,
            settings=self.settings,
            cancel_event=self.cancel_event,
            emit=self.emit,
            source_for_transcode=True,
            cookie_browser=None,
            progress_tracker=self.progress_tracker,
            download_manual_subs=self.download_manual_subs,
        )
        if self.download_manual_subs:
            self.emit("log", "已啟用：下載頻道主 CC 字幕（不含 YouTube 自動字幕）。")
        info = extract_info_with_cookie_fallback(
            yt_dlp=self.yt_dlp,
            base_options=options,
            settings=self.settings,
            url=item.url,
            download=True,
            log=lambda message: self.emit("log", message),
        )

        source_path = find_downloaded_filepath(info or {}, self.output_dir, source_for_transcode=True)
        if not source_path:
            raise RuntimeError("下載完成，但找不到要轉碼的原始檔。")

        output_path = unique_path(final_h264_path(source_path))
        duration = None
        if isinstance(info, dict):
            try:
                duration = float(info.get("duration") or 0)
            except (TypeError, ValueError):
                duration = None

        self.transcode_to_h264(source_path, output_path, duration)
        self.last_file = output_path
        if self.settings.delete_temp_source:
            try:
                source_path.unlink()
            except OSError:
                self.emit("log", f"原始暫存檔無法刪除，可手動移除：{source_path}")

    def nvenc_available(self) -> bool:
        if self.nvenc_available_cache is not None:
            return self.nvenc_available_cache
        if not self.ffmpeg_path or not self.settings.prefer_nvenc:
            self.nvenc_available_cache = False
            return False
        self.nvenc_available_cache = has_nvidia_gpu() and ffmpeg_has_encoder(
            self.ffmpeg_path, "h264_nvenc"
        )
        return self.nvenc_available_cache

    def transcode_to_h264(self, source_path: Path, output_path: Path, duration: float | None) -> None:
        if self.nvenc_available():
            self.emit("log", "偵測到 NVIDIA 顯示卡，使用 NVENC 轉碼。")
            nvenc_args = [
                "-c:v",
                "h264_nvenc",
                "-preset",
                "p5",
                "-tune",
                "hq",
                "-rc",
                "vbr",
                "-cq",
                "18",
                "-b:v",
                "0",
                "-pix_fmt",
                "yuv420p",
                "-profile:v",
                "high",
            ]
            try:
                self.run_ffmpeg_transcode(source_path, output_path, nvenc_args, duration)
                return
            except Exception as exc:
                self.emit("log", f"NVENC 轉碼失敗，改用 CPU：{exc}")
                try:
                    output_path.unlink(missing_ok=True)
                except OSError:
                    pass

        self.emit("log", "使用 CPU libx264 轉碼。")
        cpu_args = [
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "17",
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "high",
        ]
        self.run_ffmpeg_transcode(source_path, output_path, cpu_args, duration)

    def run_ffmpeg_transcode(
        self,
        source_path: Path,
        output_path: Path,
        video_args: list[str],
        duration: float | None,
    ) -> None:
        if not self.ffmpeg_path:
            raise RuntimeError("找不到 FFmpeg。")

        command = [
            self.ffmpeg_path,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            *video_args,
            "-c:a",
            "aac",
            "-b:a",
            "320k",
            "-movflags",
            "+faststart",
            "-progress",
            "pipe:1",
            "-nostats",
            str(output_path),
        ]

        self.emit("status", "正在轉碼成 4K H.264 MP4...")
        # Reset to 0% for the new (transcode) stage and let ffmpeg drive it
        # honestly from there. The expanded out_time parser handles every
        # ffmpeg build, so the bar shouldn't stick at 0% for long.
        self.emit("progress", 0.0, "轉碼準備中…", "transcode")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=CREATE_NO_WINDOW,
        )
        assert process.stdout is not None
        last_output: list[str] = []
        try:
            for raw_line in process.stdout:
                if self.cancel_event.is_set():
                    process.terminate()
                    raise DownloadCancelled()
                line = raw_line.strip()
                if line:
                    last_output.append(line)
                    last_output = last_output[-8:]
                percent = ffmpeg_progress_percent(line, duration)
                if percent is not None:
                    self.emit("progress", percent, f"轉碼中 {percent:5.1f}%", "transcode")
                elif line == "progress=end":
                    self.emit("progress", 100.0, "轉碼完成", "transcode")
            return_code = process.wait()
        finally:
            if process.poll() is None:
                process.kill()

        if return_code != 0:
            detail = "\n".join(last_output)
            raise RuntimeError(detail or f"FFmpeg 失敗，代碼 {return_code}")

        self.emit("progress", 100.0, "轉碼完成", "transcode")
        self.emit("log", f"已輸出：{output_path}")


def icon(name: str) -> Any:
    icons_obj = getattr(ft, "Icons", None)
    if icons_obj is not None and hasattr(icons_obj, name):
        return getattr(icons_obj, name)
    icons_mod = getattr(ft, "icons", None)
    if icons_mod is not None and hasattr(icons_mod, name):
        return getattr(icons_mod, name)
    return name.lower()


def color(name: str, fallback: str) -> str:
    colors_obj = getattr(ft, "Colors", None)
    if colors_obj is not None and hasattr(colors_obj, name):
        return getattr(colors_obj, name)
    colors_mod = getattr(ft, "colors", None)
    if colors_mod is not None and hasattr(colors_mod, name):
        return getattr(colors_mod, name)
    return fallback


def padding_symmetric(horizontal: int = 0, vertical: int = 0) -> Any:
    padding_class = getattr(ft, "Padding", None)
    if padding_class is not None:
        return padding_class(horizontal, vertical, horizontal, vertical)
    return {"left": horizontal, "top": vertical, "right": horizontal, "bottom": vertical}


def padding_edges(left: int = 0, top: int = 0, right: int = 0, bottom: int = 0) -> Any:
    padding_class = getattr(ft, "Padding", None)
    if padding_class is not None:
        return padding_class(left, top, right, bottom)
    return {"left": left, "top": top, "right": right, "bottom": bottom}


def align_center() -> Any:
    alignment_class = getattr(ft, "Alignment", None)
    if alignment_class is not None:
        return alignment_class(0, 0)
    alignment_module = getattr(ft, "alignment", None)
    if alignment_module is not None and hasattr(alignment_module, "center"):
        return alignment_module.center
    return None


def border_all(width: float, border_color: str) -> Any:
    border_module = getattr(ft, "border", None)
    if border_module is not None and hasattr(border_module, "all"):
        return border_module.all(width, border_color)

    border_side_class = getattr(ft, "BorderSide", None)
    border_class = getattr(ft, "Border", None)
    if border_side_class is None or border_class is None:
        return None

    side = None
    for kwargs in ({"width": width, "color": border_color}, {"color": border_color, "width": width}):
        try:
            side = border_side_class(**kwargs)
            break
        except TypeError:
            continue
    if side is None:
        try:
            side = border_side_class(width, border_color)
        except TypeError:
            try:
                side = border_side_class(border_color, width)
            except TypeError:
                return None

    try:
        return border_class(left=side, top=side, right=side, bottom=side)
    except TypeError:
        try:
            return border_class(side, side, side, side)
        except TypeError:
            return None


def glass_shadow() -> Any:
    shadow_class = getattr(ft, "BoxShadow", None)
    offset_class = getattr(ft, "Offset", None)
    if shadow_class is None:
        return None
    try:
        offset = offset_class(0, 18) if offset_class is not None else None
        return shadow_class(
            blur_radius=34,
            spread_radius=-8,
            color=GLASS_SHADOW,
            offset=offset,
        )
    except TypeError:
        try:
            return shadow_class(34, GLASS_SHADOW)
        except TypeError:
            return None


class YtdlFletApp:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.state = AppState(settings=load_settings())
        self.state.video_quality = self.state.settings.default_video_quality
        self.state.video_codec = self.state.settings.default_video_codec
        self.state.audio_format = self.state.settings.default_audio_format
        self.history: list[str] = []
        self.status_text = "正在更新核心..."
        self.notice_text = ""
        self.log_lines: list[str] = []
        self.current_job: DownloadJob | None = None

        self.progress_ring: ft.ProgressRing | None = None
        self.progress_bar: ft.ProgressBar | None = None
        self.percent_text: ft.Text | None = None
        self.progress_detail: ft.Text | None = None
        self.progress_status: ft.Text | None = None
        self.bottom_status_text: ft.Text | None = None
        self.complete_action: ft.Control | None = None
        self.stop_button: ft.Control | None = None
        self.ui_scale: float = 1.0
        self.display_percent: float = 0.0
        self.target_percent: float = 0.0
        self.progress_done: bool = False
        self.progress_stage: str = "download"
        self.last_output_file: str | None = None
        self.percent_holder: ft.Control | None = None
        self.action_holder: ft.Control | None = None
        self.video_advanced_open: bool = False
        self.ui_thread_id = threading.get_ident()
        self.ui_events: queue.Queue[tuple[str, tuple[Any, ...]]] = queue.Queue()
        self.ui_pump_stop = threading.Event()

        startup_log(
            f"init begin frozen={is_packaged_app()} platform={sys.platform} "
            f"root={resource_root()} exe={sys.executable}"
        )
        try:
            self.configure_page()
            self.start_ui_event_pump()
            self.start_auto_update()
            self.render("url", replace=True)
            startup_log("init render url ok")
        except Exception as exc:
            startup_log(f"init FAILED: {exc!r}")
            # Packaged builds sometimes fail silently → pure black window.
            try:
                self._show_fatal_error(exc)
            except Exception as exc2:
                startup_log(f"fatal UI also failed: {exc2!r}")

    def _show_fatal_error(self, exc: BaseException) -> None:
        self.page.controls.clear()
        self.page.bgcolor = "#1a1a1a"
        self.page.padding = 24
        self.page.add(
            ft.Column(
                controls=[
                    ft.Text("YTDL failed to start", size=22, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                    ft.Text(str(exc), size=14, color="#FFB4B4", selectable=True),
                    ft.Text(
                        f"root={resource_root()}\nlog={app_data_dir() / 'startup.log'}",
                        size=12,
                        color="#CCCCCC",
                        selectable=True,
                    ),
                ],
                spacing=12,
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
        )
        self.page.update()

    def configure_page(self) -> None:
        self.page.title = "YTDL"
        ico = app_icon_ico_path()
        png = app_icon_png_path()
        icon_path = ico if ico.exists() else (png if png.exists() else None)
        if icon_path is not None:
            if hasattr(self.page, "window"):
                try:
                    self.page.window.icon = str(icon_path)
                except Exception:
                    pass
            try:
                self.page.window_icon = str(icon_path)
            except Exception:
                pass

        # Target an on-screen size of 895x1425 physical pixels. Flet/Flutter sizes
        # windows in logical pixels, so divide by the display scale (e.g. 150%)
        # otherwise the window renders much larger than intended on HiDPI screens.
        # On smaller (e.g. HD) screens, shrink window + UI proportionally to fit.
        scale_factor = dpi_scale()
        phys_w = DEFAULT_WINDOW_WIDTH
        phys_h = DEFAULT_WINDOW_HEIGHT
        self.ui_scale = 1.0
        work_area = screen_work_area()
        if work_area is not None:
            avail_w, avail_h = work_area
            fit = min(1.0, (avail_w - 20) / phys_w, (avail_h - 60) / phys_h)
            fit = max(0.5, fit)
            self.ui_scale = fit
            phys_w = int(phys_w * fit)
            phys_h = int(phys_h * fit)
        # Packaged macOS: prefer a compact window that fits laptop screens.
        if is_packaged_app() and sys.platform == "darwin":
            phys_w = min(phys_w, 720)
            phys_h = min(phys_h, 900)
            self.ui_scale = min(self.ui_scale, 0.85)
        win_w = max(1, int(round(phys_w / scale_factor)))
        win_h = max(1, int(round(phys_h / scale_factor)))
        min_w = int(win_w * 0.6)
        min_h = int(win_h * 0.6)
        if hasattr(self.page, "window"):
            self.page.window.width = win_w
            self.page.window.height = win_h
            self.page.window.min_width = min_w
            self.page.window.min_height = min_h
            try:
                self.page.window.visible = True
            except Exception:
                pass
        else:
            self.page.window_width = win_w
            self.page.window_height = win_h
            self.page.window_min_width = min_w
            self.page.window_min_height = min_h
        self.page.padding = 0
        # Slightly lighter than pure black so a "blank UI" is easier to spot.
        self.page.bgcolor = BG if not (is_packaged_app() and sys.platform == "darwin") else "#1E1E1E"
        self.page.theme_mode = ft.ThemeMode.DARK
        try:
            self.page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
            self.page.vertical_alignment = ft.MainAxisAlignment.START
        except Exception:
            pass
        # Packaged macOS Flutter often fails to pick CJK fonts → Chinese UI looks
        # like an empty black window. Force a system font stack that exists on macOS.
        if sys.platform == "darwin":
            for family in ("PingFang TC", "PingFang SC", "Hiragino Sans", "Helvetica Neue", "Helvetica"):
                try:
                    theme = ft.Theme(font_family=family)
                    self.page.theme = theme
                    self.page.dark_theme = theme
                    startup_log(f"theme font_family={family}")
                    break
                except Exception:
                    continue
        # Do not clear fonts — empty fonts map can break text rendering.
        # Skip resize-driven re-render on packaged macOS (first frames are 0x0).
        if not (is_packaged_app() and sys.platform == "darwin"):
            self.page.on_resize = self.on_resize
        startup_log(f"configure_page window={win_w}x{win_h} ui_scale={self.ui_scale}")

    def on_resize(self, _event: Any = None) -> None:
        # Packaged macOS can fire resize with 0x0 during first layout; re-rendering
        # then produces an empty/black frame that never recovers.
        try:
            w = float(getattr(self.page, "width", 0) or 0)
            h = float(getattr(self.page, "height", 0) or 0)
        except Exception:
            w, h = 0.0, 0.0
        if w < 80 or h < 80:
            startup_log(f"on_resize ignored tiny size {w}x{h}")
            return
        if self.state.current_step != "progress":
            self.render(self.state.current_step, replace=True)

    def viewport_width(self) -> float:
        width = getattr(self.page, "width", None)
        if width:
            return float(width)
        window = getattr(self.page, "window", None)
        if window is not None and getattr(window, "width", None):
            return float(window.width)
        return float(getattr(self.page, "window_width", 620) or 620)

    def viewport_height(self) -> float:
        height = getattr(self.page, "height", None)
        if height:
            return float(height)
        window = getattr(self.page, "window", None)
        if window is not None and getattr(window, "height", None):
            return float(window.height)
        return float(getattr(self.page, "window_height", 820) or 820)

    def shell_padding(self) -> Any:
        width = self.viewport_width()
        if width < 430:
            return padding_edges(18, 16, 18, 16)
        if width < 560:
            return padding_edges(24, 18, 24, 18)
        return padding_edges(34, 24, 34, 24)

    def content_width(self, max_width: int = 560, min_width: int = 260) -> int:
        width = self.viewport_width()
        horizontal_padding = 68 if width >= 560 else 48 if width >= 430 else 36
        available = int(max(min_width, width - horizontal_padding))
        return min(max_width, available)

    def compact_width(self) -> int:
        return min(300, max(220, self.content_width(max_width=300, min_width=220)))

    def option_page_scale(self) -> float:
        # Keep option cards readable when the window is shrunk to fit HD screens.
        return max(self.ui_scale, 0.95) * 0.7 * 1.3 * 0.9

    def option_page_width(self) -> int:
        content = self.content_width()
        base = int(content * 0.7 * 1.3 * 0.9)
        return min(content, max(base, min(content, 420)))

    def start_ui_event_pump(self) -> None:
        if hasattr(self.page, "run_task"):
            self.page.run_task(self.ui_event_pump)

    def post_ui_event(self, kind: str, *values: Any) -> None:
        self.ui_events.put((kind, values))

    def in_ui_thread(self) -> bool:
        return threading.get_ident() == self.ui_thread_id

    async def ui_event_pump(self) -> None:
        self.ui_thread_id = threading.get_ident()
        while not self.ui_pump_stop.is_set():
            try:
                self.flush_ui_events()
            except Exception as exc:
                self.log(f"UI 更新發生問題：{exc}")
            await asyncio.sleep(0.05)

    def flush_ui_events(self) -> None:
        did_work = False
        latest_progress: tuple[Any, ...] | None = None
        for _ in range(200):
            try:
                kind, values = self.ui_events.get_nowait()
            except queue.Empty:
                break

            if kind == "progress":
                latest_progress = values
                did_work = True
                continue

            if latest_progress is not None:
                self._apply_download_progress(*latest_progress)
                latest_progress = None

            self.handle_ui_event(kind, values)
            did_work = True

        if latest_progress is not None:
            self._apply_download_progress(*latest_progress)

        if did_work:
            self.safe_update()

    def handle_ui_event(self, kind: str, values: tuple[Any, ...]) -> None:
        if kind == "status":
            self._apply_status(str(values[0]))
        elif kind == "download_status":
            self._apply_download_status(str(values[0]))
        elif kind == "log":
            self.log(str(values[0]))
        elif kind == "done":
            self._apply_download_done(*values)
        elif kind == "render":
            self._render(str(values[0]), bool(values[1]) if len(values) > 1 else False)
        elif kind == "render_loading":
            self._render_loading(str(values[0]))
        elif kind == "toast":
            self._show_toast(str(values[0]))
        elif kind == "update":
            pass

    def start_auto_update(self) -> None:
        self.run_background(self.startup_worker)

    def run_background(self, target: Callable[..., None], *args: Any) -> None:
        if hasattr(self.page, "run_thread"):
            self.page.run_thread(lambda: target(*args))
        else:
            thread = threading.Thread(target=target, args=args, daemon=True)
            thread.start()

    def load_core(self) -> bool:
        try:
            self.state.yt_dlp = importlib.import_module("yt_dlp")
            imageio_ffmpeg = importlib.import_module("imageio_ffmpeg")
            self.state.ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            self.state.ready = True
            return True
        except Exception as exc:
            self.state.ready = False
            self.log(f"載入必要元件失敗：{exc}")
            return False

    def startup_worker(self) -> None:
        core_ready = self.load_core()
        if core_ready:
            self.set_status("就緒")
        else:
            self.set_status("正在準備核心...")

        if getattr(sys, "frozen", False):
            self.check_github_release_update()
            self.safe_update()
            return

        self.auto_update_worker()

        if self.state.yt_dlp is None:
            self.load_core()
        if self.state.yt_dlp is not None:
            self.state.ready = True
            self.set_status("就緒")
        else:
            self.state.ready = False
            self.set_status("必要元件載入失敗，請重新執行 install.bat")
        # Non-blocking for the UI thread (we are already in a background worker).
        self.check_github_release_update()
        self.safe_update()

    def check_github_release_update(self) -> None:
        """If GitHub has a newer Release than APP_VERSION, show a toast."""
        repo = GITHUB_REPO
        if not repo:
            return
        try:
            latest = fetch_latest_github_release(repo)
            if not latest:
                return
            remote_tag = latest["tag"]
            if not is_remote_version_newer(remote_tag, APP_VERSION):
                self.log(f"版本檢查：已是最新（目前 {APP_VERSION}，遠端 {remote_tag}）。")
                return
            message = (
                f"有新版本可用：{remote_tag}（目前 {APP_VERSION}）。"
                f"請到 GitHub Releases 下載更新。"
            )
            self.log(message)
            self.log(f"下載頁：{latest['url']}")
            self.toast(message)
        except Exception as exc:
            self.log(f"版本檢查略過：{exc}")

    def auto_update_worker(self) -> None:
        if self.state.yt_dlp is not None:
            self.set_status("就緒，正在更新核心...")
        else:
            self.set_status("正在更新核心...")
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-input",
            "--disable-pip-version-check",
            "--upgrade",
            "--upgrade-strategy",
            "only-if-needed",
            "yt-dlp",
            "imageio-ffmpeg",
        ]
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=75,
                creationflags=CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                self.log("自動更新完成。")
            else:
                self.log("自動更新未完成，將嘗試使用目前版本。")
                trimmed = "\n".join((result.stdout or "").splitlines()[-8:])
                if trimmed:
                    self.log(trimmed)
        except subprocess.TimeoutExpired:
            self.log("自動更新逾時，將嘗試使用目前版本。")
        except Exception as exc:
            self.log(f"自動更新發生問題：{exc}")
        if self.state.yt_dlp is not None:
            self.set_status("就緒")

    def safe_update(self) -> None:
        if not self.in_ui_thread():
            self.post_ui_event("update")
            return
        try:
            self.page.update()
        except Exception:
            pass

    def sc(self, value: float, extra: float = 1.0) -> int:
        """Scale a size by the global window scale and an optional per-page factor."""
        return max(1, int(round(value * self.ui_scale * extra)))

    def settings_note_size(self, scale: float | None = None) -> int:
        if scale is None:
            scale = self.ui_scale * 0.7
        return max(9, int(12 * scale))

    def log(self, text: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_lines.append(f"[{timestamp}] {text}")
        self.log_lines = self.log_lines[-80:]

    def public_status_text(self, text: str) -> str:
        if not text:
            return ""
        return text.replace("yt-dlp", "核心").replace("Yt-dlp", "核心")

    def set_status(self, text: str) -> None:
        if not self.in_ui_thread():
            self.post_ui_event("status", text)
            return
        self._apply_status(text)
        self.safe_update()

    def _apply_status(self, text: str) -> None:
        public_text = self.public_status_text(text)
        self.status_text = public_text
        if self.progress_status:
            self.progress_status.value = public_text
        if self.bottom_status_text:
            self.bottom_status_text.value = public_text

    def toast(self, text: str) -> None:
        if not self.in_ui_thread():
            self.post_ui_event("toast", text)
            return
        self._show_toast(text)

    def _show_toast(self, text: str) -> None:
        self.notice_text = text
        try:
            snack_bar = ft.SnackBar(text)
            if hasattr(self.page, "show_dialog"):
                self.page.show_dialog(snack_bar)
            else:
                snack_bar.open = True
                self.page.snack_bar = snack_bar
            self.page.update()
        except Exception:
            pass

    def render(self, step: str, replace: bool = False) -> None:
        if not self.in_ui_thread():
            self.post_ui_event("render", step, replace)
            return
        self._render(step, replace)

    def _render(self, step: str, replace: bool = False) -> None:
        if not replace and step != self.state.current_step:
            self.history.append(self.state.current_step)
        self.state.current_step = step
        try:
            body = self.step_content(step)
            shell = self.app_shell(body)
            self.clear_page()
            self.page.add(shell)
            self.safe_update()
            startup_log(f"render ok step={step}")
        except Exception as exc:
            startup_log(f"render FAILED step={step}: {exc!r}")
            self._show_fatal_error(exc)

    def clear_page(self) -> None:
        if hasattr(self.page, "clean"):
            self.page.clean()
        else:
            self.page.controls.clear()

    def back(self, _event: Any = None) -> None:
        if self.history:
            previous = self.history.pop()
            self.render(previous, replace=True)
        else:
            self.render("url", replace=True)

    def app_shell(self, content: ft.Control) -> ft.Control:
        can_back = self.state.current_step not in ("url", "progress")
        footer_size = self.settings_note_size()
        self.bottom_status_text = ft.Text(
            self.public_status_text(self.status_text),
            size=footer_size,
            color=TEXT_MUTED,
        )
        back_button = ft.IconButton(
            icon=icon("ARROW_BACK"),
            visible=can_back,
            tooltip="返回",
            icon_color=TEXT_SOFT,
            icon_size=17,
            on_click=self.back,
        )
        settings_visible = self.state.current_step != "settings"
        bottom_bar = ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("●", size=footer_size, color=YT_RED),
                        self.bottom_status_text,
                    ],
                    spacing=max(3, int(6 * self.ui_scale)),
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.IconButton(
                    icon=icon("SETTINGS"),
                    icon_color=TEXT_SOFT,
                    icon_size=17,
                    tooltip="設定",
                    visible=settings_visible,
                    on_click=lambda _e: self.render("settings"),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        if self.state.current_step == "settings":
            self.bottom_status_text = None
            bottom_bar = ft.Row(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text("●", size=footer_size, color=YT_RED),
                            ft.Text("v1.0", size=footer_size, color=TEXT_MUTED),
                        ],
                        spacing=max(3, int(5 * self.ui_scale)),
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Text("By WiKi", size=footer_size, color=TEXT_MUTED),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

        # Packaged macOS: nested Stack + Image often paints a solid black frame.
        # Use a simple Column shell (no background image) which is reliable.
        # Also avoid IconButton-only chrome — some builds fail to load Material icons.
        if is_packaged_app() and sys.platform == "darwin":
            settings_link = ft.TextButton(
                content="Settings",
                on_click=lambda _e: self.render("settings"),
                visible=settings_visible,
            )
            back_link = ft.TextButton(
                content="Back",
                on_click=self.back,
                visible=can_back,
            )
            return ft.Container(
                expand=True,
                bgcolor="#1E1E1E",
                padding=20,
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "YTDL",
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color="#FFFFFF",
                            font_family="Helvetica",
                        ),
                        ft.Text(
                            "macOS build — if you only saw a black window before, fonts/layout were broken.",
                            size=12,
                            color="#A0A0A0",
                            font_family="Helvetica",
                        ),
                        ft.Row(
                            controls=[back_link, settings_link],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Container(content=content, expand=True, alignment=align_center()),
                        bottom_bar,
                    ],
                    expand=True,
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
            )

        # Reserve space at top/bottom so centered content never collides with the
        # back arrow (top-left) or the settings gear (bottom-right).
        top_reserve = self.sc(48) if can_back else 0
        bottom_reserve = self.sc(44)
        foreground = ft.Container(
            content=ft.Stack(
                controls=[
                    ft.Container(
                        content=content,
                        alignment=align_center(),
                        left=0,
                        top=top_reserve,
                        right=0,
                        bottom=bottom_reserve,
                    ),
                    ft.Container(content=back_button, left=0, top=0),
                    ft.Container(content=bottom_bar, left=0, right=0, bottom=0),
                ],
                fit=ft.StackFit.EXPAND,
                expand=True,
            ),
            padding=self.shell_padding(),
            expand=True,
        )
        return ft.Stack(
            controls=[
                make_background_control(),
                ft.Container(bgcolor="0x18000000", expand=True),
                foreground,
            ],
            fit=ft.StackFit.EXPAND,
            expand=True,
        )

    def step_content(self, step: str) -> ft.Control:
        if step == "url":
            return self.url_page()
        if step == "select_items":
            return self.select_items_page()
        if step == "mode":
            return self.mode_page()
        if step == "video_options":
            return self.video_options_page()
        if step == "audio_options":
            return self.audio_options_page()
        if step == "settings":
            return self.settings_page()
        if step == "progress":
            return self.progress_page()
        return self.url_page()

    def page_title(
        self,
        eyebrow: str,
        title: str,
        body: str,
        scale: float = 1.0,
        eyebrow_color: str = YT_RED,
    ) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text(eyebrow, size=max(10, int(16 * scale)), weight=ft.FontWeight.BOLD, color=eyebrow_color),
        ]
        if title:
            controls.append(
                ft.Text(title, size=max(14, int(28 * scale)), weight=ft.FontWeight.BOLD, color=TEXT)
            )
        if body:
            controls.append(ft.Text(body, size=max(9, int(13 * scale)), color=TEXT_MUTED))
        return ft.Column(controls=controls, spacing=max(3, int(8 * scale)))

    def primary_button(
        self,
        text: str,
        on_click: Callable[..., None],
        disabled: bool = False,
        width: int | None = None,
        height: int | None = None,
        text_size: int = 20,
        pad_x: int = 28,
        pad_y: int = 18,
        show_icon: bool = True,
    ) -> ft.Control:
        return ft.FilledButton(
            content=text,
            icon=icon("ARROW_FORWARD") if show_icon else None,
            disabled=disabled,
            on_click=on_click,
            width=width,
            height=height,
            style=ft.ButtonStyle(
                bgcolor=YT_RED,
                color=TEXT,
                overlay_color=YT_RED_DARK,
                shape=ft.RoundedRectangleBorder(radius=PILL_RADIUS),
                padding=padding_symmetric(horizontal=pad_x, vertical=pad_y),
                text_style=ft.TextStyle(size=text_size, weight=ft.FontWeight.BOLD),
            ),
        )

    def secondary_button(
        self,
        text: str,
        leading_icon: str,
        on_click: Callable[..., None],
        width: int | None = None,
        height: int | None = None,
        text_size: int = 20,
        pad_x: int = 28,
        pad_y: int = 18,
    ) -> ft.Control:
        return ft.OutlinedButton(
            content=text,
            icon=leading_icon,
            on_click=on_click,
            width=width,
            height=height,
            style=ft.ButtonStyle(
                bgcolor=SURFACE,
                color=TEXT,
                overlay_color=SURFACE_STRONG,
                shape=ft.RoundedRectangleBorder(radius=PILL_RADIUS),
                padding=padding_symmetric(horizontal=pad_x, vertical=pad_y),
                text_style=ft.TextStyle(size=text_size, weight=ft.FontWeight.BOLD),
            ),
        )

    def option_tile(
        self,
        *,
        title: str,
        subtitle: str,
        leading_icon: str,
        leading_label: str | None = None,
        selected: bool,
        on_click: Callable[..., None],
        scale: float = 1.0,
        text_scale: float = 1.0,
        width: int | None = None,
    ) -> ft.Control:
        border_color = BORDER_ACTIVE if selected else BORDER
        bg = SURFACE_STRONG if selected else SURFACE
        tile_width = width if width is not None else self.content_width()
        box = max(28, int(46 * scale))
        font_scale = scale * text_scale
        leading_color = TEXT if selected else TEXT_SOFT
        leading_content: ft.Control
        if leading_label:
            leading_content = ft.Text(
                leading_label,
                color=leading_color,
                size=max(10, int(14 * scale)),
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER,
            )
        else:
            leading_content = ft.Icon(
                leading_icon, color=leading_color, size=max(16, int(26 * scale))
            )
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=leading_content,
                        width=box,
                        height=box,
                        bgcolor=YT_RED if selected else SURFACE_SOFT,
                        border_radius=PILL_RADIUS,
                        alignment=align_center(),
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(
                                title,
                                size=max(11, int(round(17 * font_scale))),
                                weight=ft.FontWeight.BOLD,
                                color=TEXT,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                subtitle,
                                size=max(8, int(round(12 * font_scale))),
                                color=TEXT_MUTED,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                        spacing=max(1, int(2 * scale)),
                        expand=True,
                    ),
                    ft.Icon(
                        icon("CHECK_CIRCLE") if selected else icon("RADIO_BUTTON_UNCHECKED"),
                        color=YT_RED if selected else TEXT_MUTED,
                        size=max(14, int(24 * scale)),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=max(6, int(12 * scale)),
            ),
            bgcolor=bg,
            border=border_all(1.5, border_color),
            border_radius=PILL_RADIUS,
            padding=max(8, int(16 * scale)),
            width=tile_width,
            shadow=glass_shadow(),
            ink=True,
            on_click=on_click,
        )

    def url_page(self) -> ft.Control:
        compact_width = self.compact_width()
        compact_scale = compact_width / 300
        input_width = int(280 * compact_scale)
        input_height = max(40, int(46 * compact_scale))
        button_width = max(80, int(92 * compact_scale))
        button_height = max(30, int(32 * compact_scale))
        compact_text_size = max(10, int(12 * compact_scale))
        compact_spacing = max(8, int(11 * compact_scale))
        input_border = getattr(ft, "InputBorder", None)
        text_field_options: dict[str, Any] = {
            "hint_text": "https://www.youtube.com/watch?v=...",
            "text_size": compact_text_size,
            "color": "0x80F9FAFB",  # 50% transparent text
            "hint_style": ft.TextStyle(color=TEXT_MUTED),
            "bgcolor": "transparent",
            "border_color": "transparent",
            "focused_border_color": "transparent",
            "content_padding": padding_symmetric(horizontal=0, vertical=0),
            "text_align": ft.TextAlign.LEFT,
            "multiline": False,
            "dense": True,
            "expand": True,
        }
        if input_border is not None and hasattr(input_border, "NONE"):
            text_field_options["border"] = input_border.NONE
        url_field = ft.TextField(
            **text_field_options,
            autofocus=True,
        )

        def do_submit() -> None:
            urls = parse_input_urls(url_field.value or "")
            if not urls:
                self.toast("請先貼上網址")
                return
            if self.state.yt_dlp is None:
                self.toast("核心正在準備，請稍候")
                return
            self.state.urls = urls
            self.render_loading("正在分析網址...")
            self.run_background(self.analyze_urls, urls)

        def submit(_event: Any = None) -> None:
            do_submit()

        async def paste(_event: Any) -> None:
            text = ""
            try:
                text = await ft.Clipboard().get()
            except Exception:
                if hasattr(self.page, "get_clipboard"):
                    text = self.page.get_clipboard()
            if text:
                url_field.value = text.strip()
                url_field.update()
                # Paste then submit immediately.
                do_submit()
            else:
                self.toast("剪貼簿沒有可貼上的文字")

        url_field.on_submit = submit

        compact_group = ft.Column(
            controls=[
                ft.Text(
                    "STEP 1",
                    size=max(11, int(13 * compact_scale)),
                    weight=ft.FontWeight.BOLD,
                    color=YT_RED,
                ),
                ft.Container(
                    content=ft.Row(
                        controls=[
                            url_field,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    width=input_width,
                    height=input_height,
                    bgcolor=SURFACE_STRONG,
                    border=border_all(1, "0xB8FFFFFF"),
                    border_radius=PILL_RADIUS,
                    padding=padding_edges(max(8, int(11 * compact_scale)), 0, max(8, int(11 * compact_scale)), 0),
                    alignment=align_center(),
                    shadow=glass_shadow(),
                ),
                ft.Row(
                    controls=[
                        self.secondary_button(
                            "貼上",
                            icon("CONTENT_PASTE"),
                            paste,
                            width=button_width,
                            height=button_height,
                            text_size=compact_text_size,
                            pad_x=8,
                            pad_y=4,
                        ),
                        self.primary_button(
                            "送出",
                            submit,
                            disabled=False,
                            width=button_width,
                            height=button_height,
                            text_size=compact_text_size,
                            pad_x=8,
                            pad_y=4,
                        ),
                    ],
                    spacing=compact_spacing,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            width=compact_width,
            spacing=max(10, int(14 * compact_scale)),
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return ft.Column(
            controls=[
                ft.Container(expand=True),
                compact_group,
                ft.Container(expand=True),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )

    def render_loading(self, message: str) -> None:
        if not self.in_ui_thread():
            self.post_ui_event("render_loading", message)
            return
        self._render_loading(message)

    def _render_loading(self, message: str) -> None:
        self.clear_page()
        self.page.add(
            self.app_shell(
                ft.Column(
                    controls=[
                        ft.Container(expand=True),
                        ft.ProgressRing(width=92, height=92, stroke_width=8),
                        ft.Text(message, size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                        ft.Text("請稍候一下", size=13, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                        ft.Container(expand=True),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    expand=True,
                )
            )
        )
        self.safe_update()

    def analyze_urls(self, urls: list[str]) -> None:
        try:
            yt_dlp = self.state.yt_dlp
            if yt_dlp is None:
                raise RuntimeError("核心尚未載入")
            try:
                YTDLP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            options = {
                "quiet": True,
                "skip_download": True,
                "extract_flat": "in_playlist",
                "ignoreerrors": False,
                "logger": QueueLogger(lambda kind, value: self.log(value) if kind == "log" else None),
                "cachedir": str(YTDLP_CACHE_DIR),
            }
            apply_js_runtime_options(options, self.log)
            all_items: list[VideoItem] = []
            errors: list[str] = []
            for url in urls:
                self.set_status(f"正在分析：{url}")
                try:
                    info = extract_info_with_cookie_fallback(
                        yt_dlp=yt_dlp,
                        base_options=options,
                        settings=self.state.settings,
                        url=url,
                        download=False,
                        log=self.log,
                    )
                    if info:
                        all_items.extend(flatten_info(info, url))
                    else:
                        errors.append(f"{url}: 核心沒有回傳影片資訊")
                except Exception as exc:
                    errors.append(f"{url}: {exc}")
                    self.log(f"分析失敗：{url}：{exc}")
            if not all_items:
                fallback_items = fallback_items_from_urls(urls)
                if fallback_items:
                    self.state.items = fallback_items
                    detail = short_error(errors[0]) if errors else "核心分析階段沒有回傳清單"
                    self.log(f"分析階段未取得清單，改用原始網址繼續：{detail}")
                    self.set_status("已保留原始網址")
                    if len(fallback_items) > 1:
                        self.render("select_items", replace=True)
                    else:
                        self.render("mode", replace=True)
                    return
                detail = short_error(errors[0]) if errors else "網址不是有效的下載連結"
                self.toast(f"沒有找到可下載的影片：{detail}")
                self.render("url", replace=True)
                return
            self.state.items = all_items
            self.log(f"已分析完成：{len(all_items)} 個項目。")
            self.set_status("分析完成")
            if len(all_items) > 1:
                self.render("select_items", replace=True)
            else:
                self.render("mode", replace=True)
        except Exception as exc:
            self.toast(f"分析失敗：{exc}")
            self.render("url", replace=True)

    def select_items_page(self) -> ft.Control:
        page_width = self.content_width()
        list_height = min(430, max(220, int(self.viewport_height() * 0.42)))
        rows: list[ft.Control] = []
        for index, item in enumerate(self.state.items):
            checkbox = ft.Checkbox(value=item.checked)

            def toggle(_event: Any, i: int = index, box: ft.Checkbox = checkbox) -> None:
                self.state.items[i].checked = bool(box.value)

            checkbox.on_change = toggle
            rows.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            checkbox,
                            ft.Column(
                                controls=[
                                    ft.Text(item.title, size=14, weight=ft.FontWeight.W_600),
                                    ft.Text(
                                        "  ".join(part for part in (item.duration, item.uploader) if part),
                                        size=11,
                                        color=TEXT_MUTED,
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                        ]
                    ),
                    bgcolor=SURFACE,
                    border=border_all(1, BORDER),
                    border_radius=CARD_RADIUS,
                    padding=10,
                    shadow=glass_shadow(),
                )
            )

        def next_step(_event: Any) -> None:
            selected = [item for item in self.state.items if item.checked]
            if not selected:
                self.toast("請至少選一個項目")
                return
            self.render("mode")

        return ft.Column(
            controls=[
                self.page_title("STEP 2", "選擇要下載的項目", "偵測到播放清單或多個項目，先勾選你要的影片。"),
                ft.Container(
                    content=ft.ListView(controls=rows, spacing=8, expand=True),
                    height=list_height,
                ),
                self.primary_button("下一步", next_step),
            ],
            width=page_width,
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        )

    def mode_page(self) -> ft.Control:
        scale = self.option_page_scale()
        tile_width = self.option_page_width()

        def choose(mode: str) -> Callable[..., None]:
            def handler(_event: Any) -> None:
                self.state.mode = mode
                self.render("video_options" if mode == "video" else "audio_options")

            return handler

        group = ft.Column(
            controls=[
                self.page_title("STEP 2", "", "", scale=scale),
                self.option_tile(
                    title="影像 + 聲音",
                    subtitle="下載影片，保留最佳可用音訊。",
                    leading_icon=icon("MOVIE"),
                    selected=self.state.mode == "video",
                    on_click=choose("video"),
                    scale=scale,
                    text_scale=1.2,
                    width=tile_width,
                ),
                self.option_tile(
                    title="只有聲音",
                    subtitle="輸出 WAV、MP3 或 AAC。",
                    leading_icon=icon("MUSIC_NOTE"),
                    selected=self.state.mode == "audio",
                    on_click=choose("audio"),
                    scale=scale,
                    text_scale=1.2,
                    width=tile_width,
                ),
            ],
            spacing=max(8, int(14 * scale)),
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return ft.Column(
            controls=[
                ft.Container(expand=True),
                group,
                ft.Container(expand=True),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )

    def video_options_page(self) -> ft.Control:
        scale = self.option_page_scale()
        tile_width = self.option_page_width()
        quality_tiles = []
        labels = {
            "AUTO": ("AUTO", "懶人首選：4K 最佳畫質轉 H.264、音訊 320k AAC，輸出 MP4。"),
            "4K": ("4K", "【AV1】畫質、壓縮效率高，舊設備可能無法播放。"),
            "HD": ("HD", "【H.264】1080P，速度與大小較平衡。"),
        }
        for quality in VIDEO_QUALITIES:
            title, subtitle = labels[quality]

            def set_quality(_event: Any, value: str = quality) -> None:
                self.state.video_quality = value
                self.render("video_options", replace=True)

            quality_tiles.append(
                self.option_tile(
                    title=title,
                    subtitle=subtitle,
                    leading_icon=icon("PLAY_ARROW") if quality == "AUTO" else icon("HIGH_QUALITY"),
                    leading_label="4K" if quality == "4K" else None,
                    selected=self.state.video_quality == quality,
                    on_click=set_quality,
                    scale=scale,
                    text_scale=1.2,
                    width=tile_width,
                )
            )

        advanced_open = self.video_advanced_open or (self.state.video_codec != "AUTO")
        advanced_visible = ft.Checkbox(
            label="進階編碼選項",
            value=advanced_open,
            label_style=ft.TextStyle(size=max(13, int(14 * self.ui_scale * 1))),
            scale=1,
        )
        codec_column = ft.Column(
            controls=[], spacing=max(6, int(10 * scale)), visible=advanced_open,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        def toggle_advanced(_event: Any) -> None:
            # Re-render so the layout can switch between centered (short) and
            # scrollable (tall) — otherwise the buttons below get pushed off-screen.
            self.video_advanced_open = bool(advanced_visible.value)
            self.render("video_options", replace=True)

        advanced_visible.on_change = toggle_advanced

        # AUTO removed from the advanced codec list per request.
        codec_labels = {
            "H264": ("H.264", "相容性最好。"),
            "AV1": ("AV1", "壓縮效率高。"),
        }
        for codec_value in ("H264", "AV1"):
            title, subtitle = codec_labels[codec_value]

            def set_codec(_event: Any, value: str = codec_value) -> None:
                self.state.video_codec = value
                self.render("video_options", replace=True)

            codec_column.controls.append(
                self.option_tile(
                    title=title,
                    subtitle=subtitle,
                    leading_icon=icon("TUNE"),
                    selected=self.state.video_codec == codec_value,
                    on_click=set_codec,
                    scale=scale,
                    text_scale=1.2,
                    width=tile_width,
                )
            )

        subs_check = ft.Checkbox(
            label="下載頻道主 CC 字幕（不含 YouTube 自動字幕）",
            value=self.state.download_manual_subs,
            label_style=ft.TextStyle(size=max(13, int(14 * self.ui_scale * 1))),
            scale=1,
        )

        def toggle_subs(_event: Any) -> None:
            self.state.download_manual_subs = bool(subs_check.value)

        subs_check.on_change = toggle_subs

        def start(_event: Any) -> None:
            self.begin_download()

        group = ft.Column(
            controls=[
                self.page_title("STEP 3", "選擇畫質", "一般直接選 AUTO；需要指定 4K 或 HD 時再切換。", scale=scale),
                *quality_tiles,
                ft.Divider(height=max(10, int(18 * scale)), color=BORDER),
                advanced_visible,
                codec_column,
                subs_check,
                self.primary_button(
                    "開始下載", start,
                    text_size=max(12, int(20 * scale)),
                    pad_x=int(28 * scale),
                    pad_y=int(18 * scale),
                    width=tile_width,
                    show_icon=False,
                ),
            ],
            width=tile_width,
            spacing=max(7, int(12 * scale)),
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        if advanced_open:
            # Tall content: make it scrollable so the lower buttons stay reachable.
            group.scroll = ft.ScrollMode.AUTO
            group.expand = True
            return group
        return ft.Column(
            controls=[
                ft.Container(expand=True),
                group,
                ft.Container(expand=True),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )

    def audio_options_page(self) -> ft.Control:
        scale = self.option_page_scale()
        tile_width = self.option_page_width()
        format_tiles = []
        labels = {
            "WAV": ("WAV", "不壓縮容器，檔案最大；來源仍受 YouTube 音源限制。"),
            "MP3": ("MP3", "相容性最好，強制目標 320k。"),
            "AAC": ("AAC", "輸出為常見 m4a/AAC，強制目標 320k。"),
        }
        for audio_format in AUDIO_FORMATS:
            title, subtitle = labels[audio_format]

            def set_format(_event: Any, value: str = audio_format) -> None:
                self.state.audio_format = value
                self.render("audio_options", replace=True)

            format_tiles.append(
                self.option_tile(
                    title=title,
                    subtitle=subtitle,
                    leading_icon=icon("GRAPHIC_EQ"),
                    selected=self.state.audio_format == audio_format,
                    on_click=set_format,
                    scale=scale,
                    text_scale=1.2,
                    width=tile_width,
                )
            )

        subs_check = ft.Checkbox(
            label="下載頻道主 CC 字幕（不含 YouTube 自動字幕）",
            value=self.state.download_manual_subs,
            label_style=ft.TextStyle(size=max(13, int(14 * self.ui_scale * 1))),
            scale=1,
        )

        def toggle_subs(_event: Any) -> None:
            self.state.download_manual_subs = bool(subs_check.value)

        subs_check.on_change = toggle_subs

        def start(_event: Any) -> None:
            self.begin_download()

        group = ft.Column(
            controls=[
                self.page_title("STEP 3", "選擇聲音格式", "MP3 與 AAC 會用 320k 目標輸出。", scale=scale),
                *format_tiles,
                subs_check,
                self.primary_button(
                    "開始轉檔", start,
                    text_size=max(12, int(20 * scale)),
                    pad_x=int(28 * scale),
                    pad_y=int(18 * scale),
                    width=tile_width,
                    show_icon=False,
                ),
            ],
            width=tile_width,
            spacing=max(7, int(12 * scale)),
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return ft.Column(
            controls=[
                ft.Container(expand=True),
                group,
                ft.Container(expand=True),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )

    def summary_box(self) -> ft.Control:
        selected_count = len([item for item in self.state.items if item.checked]) or len(self.state.urls)
        if self.state.mode == "video":
            mode_text = f"影片：{self.state.video_quality} / {self.state.video_codec}"
        else:
            mode_text = f"聲音：{self.state.audio_format}"
        summary_lines = [
            ft.Text("即將處理", size=12, color=TEXT_MUTED),
            ft.Text(f"{selected_count} 個項目", size=16, weight=ft.FontWeight.BOLD, color=TEXT),
            ft.Text(mode_text, size=13, color=TEXT_SOFT),
        ]
        if self.state.download_manual_subs:
            summary_lines.append(
                ft.Text("字幕：頻道主 CC（不含自動字幕）", size=12, color=TEXT_SOFT)
            )
        summary_lines.append(
            ft.Text(f"儲存到：{self.state.settings.output_dir}", size=12, color=TEXT_MUTED)
        )
        return ft.Container(
            content=ft.Column(
                controls=summary_lines,
                spacing=3,
            ),
            bgcolor=SURFACE,
            border=border_all(1, BORDER),
            border_radius=CARD_RADIUS,
            padding=14,
            width=self.content_width(),
            shadow=glass_shadow(),
        )

    def settings_page(self) -> ft.Control:
        scale = self.ui_scale * 0.7
        page_width = int(self.content_width() * 0.7)
        note_size = self.settings_note_size(scale)
        output_text = ft.Text(self.state.settings.output_dir, color=TEXT_SOFT, size=max(9, int(12 * scale)))

        async def choose_folder(_event: Any) -> None:
            try:
                selected = await ft.FilePicker().get_directory_path(
                    dialog_title="選擇儲存資料夾",
                    initial_directory=self.state.settings.output_dir,
                )
            except Exception as exc:
                self.toast(f"目前環境無法選擇資料夾：{exc}")
                return
            if selected:
                self.state.settings.output_dir = selected
                save_settings(self.state.settings)
                output_text.value = selected
                output_text.update()
                self.toast("已更新儲存位置")

        def reset_folder(_event: Any) -> None:
            self.state.settings.output_dir = str(get_downloads_dir())
            save_settings(self.state.settings)
            output_text.value = self.state.settings.output_dir
            output_text.update()
            self.toast("已改回下載資料夾")

        open_done = ft.Switch(value=self.state.settings.open_folder_when_done)
        delete_temp = ft.Switch(value=self.state.settings.delete_temp_source)
        prefer_nvenc = ft.Switch(value=self.state.settings.prefer_nvenc)

        def save_switches(_event: Any = None) -> None:
            self.state.settings.open_folder_when_done = bool(open_done.value)
            self.state.settings.delete_temp_source = bool(delete_temp.value)
            self.state.settings.prefer_nvenc = bool(prefer_nvenc.value)
            save_settings(self.state.settings)

        open_done.on_change = save_switches
        delete_temp.on_change = save_switches
        prefer_nvenc.on_change = save_switches

        return ft.Column(
            controls=[
                self.page_title("SETTINGS", "", "", scale=scale),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("儲存位置", size=max(10, int(14 * scale)), weight=ft.FontWeight.BOLD, color=TEXT),
                            output_text,
                            ft.Row(
                                controls=[
                                    ft.OutlinedButton(
                                        content="選擇資料夾",
                                        icon=icon("FOLDER_OPEN"),
                                        on_click=choose_folder,
                                        style=ft.ButtonStyle(
                                            color=TEXT,
                                            shape=ft.RoundedRectangleBorder(radius=PILL_RADIUS),
                                            padding=padding_symmetric(horizontal=int(18 * scale), vertical=int(12 * scale)),
                                        ),
                                    ),
                                    ft.TextButton(
                                        content="改回下載資料夾",
                                        on_click=reset_folder,
                                        style=ft.ButtonStyle(color=TEXT_MUTED),
                                    ),
                                ]
                            ),
                        ],
                        spacing=max(4, int(8 * scale)),
                    ),
                    bgcolor=SURFACE,
                    border=border_all(1, BORDER),
                    border_radius=CARD_RADIUS,
                    padding=max(8, int(14 * scale)),
                    shadow=glass_shadow(),
                ),
                self.setting_switch("完成後自動開啟資料夾", open_done, scale=scale),
                self.setting_switch("4K H.264 完成後刪除原始暫存檔", delete_temp, scale=scale),
                self.setting_switch("偵測到 NVIDIA 時優先使用 NVENC", prefer_nvenc, scale=scale),
                ft.Container(
                    content=ft.Text(
                        f"版本 {APP_VERSION}"
                        + (f"  ·  啟動時會檢查 GitHub Releases 是否有更新（{GITHUB_REPO}）。" if GITHUB_REPO else "  ·  尚未設定 GitHub 倉庫，略過更新檢查。")
                        + " 啟動時仍會自動更新核心，並使用內建 Deno 處理 YouTube 驗證。",
                        size=note_size,
                        color=TEXT_MUTED,
                    ),
                    padding=max(8, int(12 * scale)),
                    bgcolor=SURFACE_SOFT,
                    border_radius=CARD_RADIUS,
                    border=border_all(1, BORDER),
                    shadow=glass_shadow(),
                ),
            ],
            width=page_width,
            spacing=max(7, int(12 * scale)),
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
        )

    def setting_switch(self, title: str, switch: ft.Switch, scale: float = 1.0) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(title, size=max(10, int(14 * scale)), weight=ft.FontWeight.W_600, color=TEXT, expand=True),
                    switch,
                ]
            ),
            bgcolor=SURFACE,
            border=border_all(1, BORDER),
            border_radius=CARD_RADIUS,
            padding=max(8, int(14 * scale)),
            shadow=glass_shadow(),
        )

    def setting_row(self, title: str, trailing: ft.Control, scale: float = 1.0) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(title, size=max(10, int(14 * scale)), weight=ft.FontWeight.W_600, color=TEXT, expand=True),
                    trailing,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=SURFACE,
            border=border_all(1, BORDER),
            border_radius=CARD_RADIUS,
            padding=max(8, int(14 * scale)),
            shadow=glass_shadow(),
        )

    def begin_download(self) -> None:
        if self.state.yt_dlp is None:
            self.toast("核心尚未準備完成")
            return
        selected_items = [item for item in self.state.items if item.checked]
        if not selected_items:
            selected_items = [VideoItem(title=url, url=url) for url in self.state.urls]
        if not selected_items:
            self.toast("沒有可下載的項目")
            return
        output_dir = Path(self.state.settings.output_dir).expanduser()
        self.state.last_output_dir = str(output_dir)
        self.render("progress")

        callbacks = {
            "status": self.on_download_status,
            "log": self.on_download_log,
            "progress": self.on_download_progress,
            "done": self.on_download_done,
        }
        self.current_job = DownloadJob(
            yt_dlp=self.state.yt_dlp,
            ffmpeg_path=self.state.ffmpeg_path,
            settings=self.state.settings,
            items=selected_items,
            mode=self.state.mode,
            quality=self.state.video_quality,
            codec=self.state.video_codec,
            audio_format=self.state.audio_format,
            output_dir=output_dir,
            callbacks=callbacks,
            download_manual_subs=self.state.download_manual_subs,
        )
        self.run_background(self.current_job.run)

    def progress_page(self) -> ft.Control:
        progress_width = self.content_width(max_width=320, min_width=220)
        # Reset progress state for this run; displayed values come only from yt-dlp/FFmpeg.
        self.display_percent = 0.0
        self.target_percent = 0.0
        self.progress_done = False
        self.progress_stage = ""
        self.progress_ring = ft.ProgressRing(
            value=0,
            width=142,
            height=142,
            stroke_width=10,
            color=YT_RED,
            bgcolor=SURFACE_SOFT,
        )
        self.progress_bar = ft.ProgressBar(value=0, height=8, color=YT_RED, bgcolor=SURFACE_SOFT)
        self._set_progress_stage("download")
        self.percent_text = ft.Text("0%", size=34, weight=ft.FontWeight.BOLD, color=TEXT)
        self.percent_holder = ft.Container(
            content=self.percent_text,
            width=142,
            height=142,
            alignment=align_center(),
        )
        self.progress_detail = ft.Text("準備中...", size=13, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER)
        self.progress_status = ft.Text(
            self.status_text,
            size=14,
            weight=ft.FontWeight.W_600,
            color=TEXT,
            text_align=ft.TextAlign.CENTER,
            max_lines=4,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.complete_action = ft.Container(visible=False)

        self.stop_button = self._progress_text_button("停止", icon("STOP"), self.cancel_download)
        self.action_holder = ft.Container(content=self.stop_button)

        layout = ft.Column(
            controls=[
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Stack(
                        controls=[
                            self.progress_ring,
                            self.percent_holder,
                        ],
                        width=142,
                        height=142,
                    ),
                    padding=24,
                    bgcolor=SURFACE,
                    border=border_all(1, BORDER),
                    border_radius=PILL_RADIUS,
                    shadow=glass_shadow(),
                ),
                self.progress_status,
                self.progress_detail,
                ft.Container(width=progress_width, content=self.progress_bar),
                self.action_holder,
                ft.Container(expand=True),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=14,
            expand=True,
        )
        return layout

    def _progress_text_button(
        self, text: str, leading_icon: Any, on_click: Callable[..., None]
    ) -> ft.Control:
        return ft.TextButton(
            content=text,
            icon=leading_icon,
            on_click=on_click,
            style=ft.ButtonStyle(
                color=TEXT_MUTED,
                shape=ft.RoundedRectangleBorder(radius=PILL_RADIUS),
                padding=padding_symmetric(horizontal=18, vertical=12),
            ),
        )

    def _set_progress_stage(self, stage: str) -> None:
        normalized = "transcode" if stage == "transcode" else "download"
        if self.progress_stage == normalized:
            return
        self.progress_stage = normalized
        progress_color = TRANSCODE_BLUE if normalized == "transcode" else YT_RED
        try:
            if self.progress_ring is not None:
                self.progress_ring.color = progress_color
            if self.progress_bar is not None:
                self.progress_bar.color = progress_color
        except Exception:
            pass

    def _apply_progress(self, value: float) -> None:
        v = max(0.0, min(100.0, value))
        frac = v / 100.0
        try:
            if self.progress_ring is not None:
                self.progress_ring.value = frac
            if self.progress_bar is not None:
                self.progress_bar.value = frac
            if self.percent_text is not None:
                self.percent_text.value = f"{int(round(v))}%"
        except Exception:
            pass

    def on_download_status(self, text: str) -> None:
        if not self.in_ui_thread():
            self.post_ui_event("download_status", text)
            return
        self._apply_download_status(text)
        self.safe_update()

    def _apply_download_status(self, text: str) -> None:
        self.status_text = text
        if self.progress_status:
            self.progress_status.value = text

    def on_download_log(self, text: str) -> None:
        if not self.in_ui_thread():
            self.post_ui_event("log", text)
            return
        self.log(text)

    def on_download_progress(self, percent: float, text: str, stage: str = "download") -> None:
        if not self.in_ui_thread():
            self.post_ui_event("progress", percent, text, stage)
            return
        self._apply_download_progress(percent, text, stage)
        self.safe_update()

    def _apply_download_progress(self, percent: float, text: str, stage: str = "download") -> None:
        self._set_progress_stage(stage)
        if percent >= 0:
            self.target_percent = max(0.0, min(100.0, percent))
            self.display_percent = self.target_percent
        if self.progress_detail:
            self.progress_detail.value = text
        if percent >= 0:
            self._apply_progress(self.target_percent)

    def on_download_done(self, ok: bool, message: str, file_path: str | None = None) -> None:
        if not self.in_ui_thread():
            self.post_ui_event("done", ok, message, file_path)
            return
        self._apply_download_done(ok, message, file_path)
        self.safe_update()

    def _apply_download_done(self, ok: bool, message: str, file_path: str | None = None) -> None:
        self.current_job = None
        self.status_text = message
        self.last_output_file = file_path
        if ok:
            self.target_percent = 100.0
            self.display_percent = 100.0
            self.progress_done = True
            self._apply_progress(100.0)
            if self.progress_status:
                self.progress_status.value = "完成"
            if self.progress_detail:
                self.progress_detail.value = "已完成，點中間的播放鍵可直接開啟檔案。"
            # Swap the "100%" text for a play button that opens the finished file.
            if self.percent_holder is not None:
                self.percent_holder.content = ft.IconButton(
                    icon=icon("PLAY_CIRCLE_FILL"),
                    icon_color=YT_RED,
                    icon_size=72,
                    tooltip="開啟檔案",
                    on_click=lambda _e: self.open_last_file(),
                )
            self._set_stop_button_home()
            if self.state.settings.open_folder_when_done:
                self.open_output_folder()
        else:
            self.progress_done = True
            if self.progress_status:
                self.progress_status.value = message
            if self.progress_detail:
                self.progress_detail.value = "請查看記錄或重新嘗試。"
            self._set_stop_button_home()

    def _set_stop_button_home(self) -> None:
        # On completion show both "開資料夾" and "回到首頁", same style/font.
        if self.action_holder is None:
            return
        try:
            self.action_holder.content = ft.Row(
                controls=[
                    self._progress_text_button(
                        "開資料夾", icon("FOLDER_OPEN"), lambda _e: self.open_output_folder()
                    ),
                    self._progress_text_button(
                        "回到首頁", icon("HOME"), lambda _e: self.go_home()
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            )
        except Exception:
            pass

    def go_home(self, _event: Any = None) -> None:
        self.progress_done = True
        self.history.clear()
        self.render("url", replace=True)

    def open_last_file(self) -> None:
        if not self.last_output_file:
            self.open_output_folder()
            return
        path = Path(self.last_output_file)
        if not path.exists():
            self.open_output_folder()
            return
        try:
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            self.toast(f"無法開啟檔案：{exc}")

    def cancel_download(self, _event: Any = None) -> None:
        if self.current_job:
            self.current_job.cancel()
            self.on_download_status("正在停止...")

    def open_output_folder(self) -> None:
        folder = Path(self.state.last_output_dir or self.state.settings.output_dir)
        try:
            if os.name == "nt":
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as exc:
            self.toast(f"無法開啟資料夾：{exc}")


def main(page: ft.Page) -> None:
    enable_high_dpi()
    ensure_js_runtime_on_path()
    YtdlFletApp(page)


if __name__ == "__main__":
    enable_high_dpi()
    ensure_js_runtime_on_path()
    if hasattr(ft, "run"):
        ft.run(main, name="YTDL")
    else:
        ft.app(target=main, name="YTDL")
