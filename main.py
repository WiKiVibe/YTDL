from __future__ import annotations

import flet as ft

from src.ytdl_gui import enable_high_dpi, ensure_js_runtime_on_path, main as app_main, startup_log


def main(page: ft.Page) -> None:
    # Packaged Flet apps call this entry directly (not always __main__).
    try:
        enable_high_dpi()
        ensure_js_runtime_on_path()
    except Exception as exc:
        startup_log(f"main() pre-init warning: {exc!r}")
    startup_log("main(page) entered")
    app_main(page)


if __name__ == "__main__":
    enable_high_dpi()
    ensure_js_runtime_on_path()
    if hasattr(ft, "run"):
        ft.run(main, name="YTDL")
    else:
        ft.app(target=main, name="YTDL")
