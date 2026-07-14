from __future__ import annotations

import flet as ft

from src.ytdl_gui import enable_high_dpi, ensure_js_runtime_on_path, main as app_main


def main(page: ft.Page) -> None:
    app_main(page)


if __name__ == "__main__":
    enable_high_dpi()
    ensure_js_runtime_on_path()
    if hasattr(ft, "run"):
        ft.run(main, name="YTDL Downloader")
    else:
        ft.app(target=main, name="YTDL Downloader")
