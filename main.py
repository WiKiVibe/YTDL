from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

import flet as ft


APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


def _startup_log(message: str) -> None:
    """Log failures that otherwise appear as an empty packaged window."""
    try:
        log_dir = Path.home() / "Library" / "Application Support" / "YTDL"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "startup.log").open("a", encoding="utf-8") as stream:
            stream.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except Exception:
        pass


def _use_private_macos_flet_cache() -> None:
    """Keep the packaged YTDL desktop client separate from Flet's shared cache."""
    if sys.platform != "darwin" or not getattr(sys, "frozen", False):
        return

    try:
        import flet_desktop
        import flet_desktop.version

        cache_dir = (
            Path.home()
            / ".flet"
            / "client"
            / f"ytdl-desktop-1.0.1-flet-{flet_desktop.version.version}"
        )

        def ytdl_client_storage_dir() -> Path:
            return cache_dir

        setattr(flet_desktop, "__get_client_storage_dir", ytdl_client_storage_dir)
        _startup_log(f"using private Flet client cache: {cache_dir}")
    except Exception as exc:
        _startup_log(f"private Flet client cache setup FAILED: {exc!r}")


_use_private_macos_flet_cache()


_startup_log(
    f"entrypoint loaded name={__name__} exe={sys.executable} file={__file__} "
    f"frozen={getattr(sys, 'frozen', False)} "
    f"FLET_APP_CONSOLE={os.environ.get('FLET_APP_CONSOLE', '')}"
)

try:
    from src.ytdl_gui import main as app_main
except Exception as exc:
    _startup_log(f"entrypoint import FAILED: {exc!r}\n{traceback.format_exc()}")
    raise


def main(page: ft.Page) -> None:
    _startup_log("Flet page connected")
    try:
        app_main(page)
    except Exception as exc:
        _startup_log(f"app main FAILED: {exc!r}\n{traceback.format_exc()}")
        page.controls.clear()
        page.bgcolor = "#1E1E1E"
        page.padding = 24
        page.add(
            ft.Column(
                controls=[
                    ft.Text(
                        "YTDL failed to start",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        color="#FFFFFF",
                    ),
                    ft.Text(str(exc), color="#FFB4B4", selectable=True),
                    ft.Text(
                        "Log: ~/Library/Application Support/YTDL/startup.log",
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
        page.update()


if __name__ == "__main__":
    _startup_log("starting ft.run(main)")
    ft.run(main, name="YTDL")
