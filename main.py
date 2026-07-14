from __future__ import annotations

import sys
import traceback
from pathlib import Path

import flet as ft


def _early_log(message: str) -> None:
    try:
        log_dir = Path.home() / "Library" / "Application Support" / "YTDL"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "startup.log").open("a", encoding="utf-8") as fh:
            fh.write(message + "\n")
    except Exception:
        pass


def _is_mac_app_bundle() -> bool:
    if getattr(sys, "frozen", False):
        return True
    try:
        exe = str(Path(sys.executable).resolve()).replace("\\", "/")
        return sys.platform == "darwin" and ".app/Contents/MacOS" in exe
    except Exception:
        return False


def _show_boot_screen(page: ft.Page, detail: str = "") -> None:
    """Ultra-simple first paint. If THIS is still black, Flet/Flutter view is broken."""
    page.controls.clear()
    page.padding = 30
    page.bgcolor = "#B71C1C"  # bright red — impossible to mistake for "empty dark UI"
    try:
        page.window.bgcolor = "#B71C1C"
    except Exception:
        pass
    try:
        page.theme_mode = ft.ThemeMode.LIGHT
    except Exception:
        pass
    controls: list[ft.Control] = [
        ft.Text("YTDL BOOT", size=36, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
        ft.Text(
            "If you see RED background + this text, the window can draw UI.",
            size=16,
            color="#FFEB3B",
        ),
        ft.Text(
            detail or "Loading full app next…",
            size=14,
            color="#FFFFFF",
            selectable=True,
        ),
    ]
    page.add(ft.Column(controls=controls, spacing=12, expand=True, scroll=ft.ScrollMode.AUTO))
    page.update()
    _early_log("boot screen painted")


def main(page: ft.Page) -> None:
    _early_log(
        f"main(page) entered frozen={getattr(sys, 'frozen', False)} "
        f"exe={sys.executable} platform={sys.platform}"
    )

    # Always paint a loud boot screen first on macOS app bundles so a pure-black
    # window means the Flutter client itself is not compositing (not our widgets).
    mac_app = _is_mac_app_bundle() or (sys.platform == "darwin" and getattr(sys, "frozen", False))
    if mac_app:
        try:
            _show_boot_screen(page, detail=f"exe={sys.executable}")
        except Exception as exc:
            _early_log(f"boot screen FAILED: {exc!r}\n{traceback.format_exc()}")

    try:
        from src.ytdl_gui import (
            enable_high_dpi,
            ensure_js_runtime_on_path,
            main as app_main,
            startup_log,
        )
    except Exception as exc:
        _early_log(f"import ytdl_gui FAILED: {exc!r}\n{traceback.format_exc()}")
        try:
            _show_boot_screen(page, detail=f"import failed:\n{exc}")
        except Exception:
            pass
        return

    try:
        enable_high_dpi()
        ensure_js_runtime_on_path()
    except Exception as exc:
        startup_log(f"main() pre-init warning: {exc!r}")

    if mac_app:
        # Give the boot frame a moment to show, then load real UI via a button so
        # we can tell whether full UI is what turns the window black.
        def _load_full(_e: object | None = None) -> None:
            try:
                startup_log("loading full app_main from boot screen")
                page.controls.clear()
                app_main(page)
            except Exception as exc:
                startup_log(f"app_main FAILED: {exc!r}\n{traceback.format_exc()}")
                _show_boot_screen(page, detail=f"full UI crashed:\n{exc}")

        page.add(
            ft.ElevatedButton(
                content="Open full YTDL UI",
                on_click=_load_full,
                bgcolor="#FFFFFF",
                color="#B71C1C",
            )
        )
        page.update()
        startup_log("waiting for user to open full UI (or auto in 0s via button only)")
        return

    startup_log("main(page) calling app_main (non-mac-app path)")
    try:
        app_main(page)
    except Exception as exc:
        startup_log(f"app_main FAILED: {exc!r}\n{traceback.format_exc()}")
        _show_boot_screen(page, detail=f"full UI crashed:\n{exc}")


if __name__ == "__main__":
    _early_log("__main__ starting ft.run")
    if hasattr(ft, "run"):
        ft.run(main, name="YTDL")
    else:
        ft.app(target=main, name="YTDL")
