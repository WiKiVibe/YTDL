from __future__ import annotations

import os
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


def _is_packaged() -> bool:
    if getattr(sys, "frozen", False):
        return True
    try:
        exe = str(Path(sys.executable).resolve()).replace("\\", "/")
        if ".app/Contents/MacOS" in exe:
            return True
    except Exception:
        pass
    # Flet extract dir
    try:
        p = str(Path(__file__).resolve()).replace("\\", "/")
        if "/Application Support/" in p and "/flet/app/" in p:
            return True
    except Exception:
        pass
    return False


def _show_boot_screen(page: ft.Page, detail: str = "") -> None:
    page.controls.clear()
    page.padding = 30
    page.bgcolor = "#B71C1C"
    try:
        page.window.bgcolor = "#B71C1C"
    except Exception:
        pass
    page.add(
        ft.Column(
            controls=[
                ft.Text("YTDL BOOT", size=36, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                ft.Text(
                    "Red screen = Python UI is connected.",
                    size=16,
                    color="#FFEB3B",
                ),
                ft.Text(detail or "", size=13, color="#FFFFFF", selectable=True),
            ],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
    )
    page.update()
    _early_log("boot screen painted")


def main(page: ft.Page) -> None:
    """Flet entry. Packaged hosts and ft.run/ft.app all call this."""
    _early_log(
        f"main(page) entered packaged={_is_packaged()} "
        f"exe={sys.executable} file={__file__}"
    )

    packaged = _is_packaged()
    if packaged:
        try:
            _show_boot_screen(page, detail="Loading…")
        except Exception as exc:
            _early_log(f"boot FAILED: {exc!r}\n{traceback.format_exc()}")

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
        startup_log(f"pre-init warning: {exc!r}")

    if packaged:
        def _load_full(_e: object | None = None) -> None:
            try:
                startup_log("loading full app_main")
                page.controls.clear()
                app_main(page)
            except Exception as exc:
                startup_log(f"app_main FAILED: {exc!r}\n{traceback.format_exc()}")
                _show_boot_screen(page, detail=f"full UI crashed:\n{exc}")

        try:
            page.add(
                ft.ElevatedButton(
                    content="Open full YTDL UI",
                    on_click=_load_full,
                    bgcolor="#FFFFFF",
                    color="#B71C1C",
                )
            )
            page.update()
            startup_log("boot UI ready (button to open full app)")
        except Exception as exc:
            startup_log(f"boot button failed, calling app_main directly: {exc!r}")
            app_main(page)
        return

    startup_log("dev mode → app_main")
    try:
        app_main(page)
    except Exception as exc:
        startup_log(f"app_main FAILED: {exc!r}\n{traceback.format_exc()}")
        _show_boot_screen(page, detail=f"full UI crashed:\n{exc}")


def _start() -> None:
    """Start Flet. Prefer ft.app in packaged builds (ft.run may never call main)."""
    flet_env = {k: v for k, v in os.environ.items() if "FLET" in k.upper()}
    _early_log(f"_start packaged={_is_packaged()} FLET_env={list(flet_env.keys())}")

    packaged = _is_packaged()
    try:
        if packaged:
            # Desktop bundle: ft.app connects to the embedded Flutter view more reliably.
            _early_log("using ft.app(target=main) for packaged build")
            if hasattr(ft, "app"):
                ft.app(target=main, name="YTDL")
            else:
                ft.run(main, name="YTDL")
        else:
            _early_log("using ft.run(main) for development")
            if hasattr(ft, "run"):
                ft.run(main, name="YTDL")
            else:
                ft.app(target=main, name="YTDL")
    except Exception as exc:
        _early_log(f"_start FAILED: {exc!r}\n{traceback.format_exc()}")
        raise


# Flet "flet build" / serious_python often executes this file as __main__.
if __name__ == "__main__":
    _early_log("__main__ → _start()")
    _start()
