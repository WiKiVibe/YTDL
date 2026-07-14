from __future__ import annotations

import traceback
from pathlib import Path

import flet as ft


def _early_log(message: str) -> None:
    """Log before ytdl_gui import (packaged builds may fail on import)."""
    try:
        log_dir = Path.home() / "Library" / "Application Support" / "YTDL"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "startup.log").open("a", encoding="utf-8") as fh:
            fh.write(message + "\n")
    except Exception:
        pass


def main(page: ft.Page) -> None:
    # Packaged Flet apps call this entry (and sometimes also run as __main__).
    _early_log("main(page) entered")
    try:
        from src.ytdl_gui import (
            enable_high_dpi,
            ensure_js_runtime_on_path,
            main as app_main,
            startup_log,
        )
    except Exception as exc:
        _early_log(f"import ytdl_gui FAILED: {exc!r}\n{traceback.format_exc()}")
        page.bgcolor = "#111111"
        page.padding = 20
        page.add(
            ft.Text("YTDL import failed", size=22, color="white"),
            ft.Text(str(exc), size=14, color="#ffaaaa", selectable=True),
            ft.Text(
                "See ~/Library/Application Support/YTDL/startup.log",
                size=12,
                color="#cccccc",
            ),
        )
        page.update()
        return

    try:
        enable_high_dpi()
        ensure_js_runtime_on_path()
    except Exception as exc:
        startup_log(f"main() pre-init warning: {exc!r}")
    startup_log("main(page) calling app_main")
    app_main(page)


if __name__ == "__main__":
    # Do not call enable_high_dpi here without imports — packaged Flet runs this
    # file as __main__ and previously crashed with NameError (black window).
    _early_log("__main__ starting ft.run")
    if hasattr(ft, "run"):
        ft.run(main, name="YTDL")
    else:
        ft.app(target=main, name="YTDL")
