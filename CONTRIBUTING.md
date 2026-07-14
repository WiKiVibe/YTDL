# Contributing

Thanks for your interest in YTDL.

## Development

1. Fork and clone the repo.
2. Create a virtualenv and install dependencies:

   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Run from source:

   ```bat
   run.bat
   ```

4. Keep changes focused. Prefer small PRs over large refactors.

## Code notes

- Main application logic lives in `src/ytdl_gui.py`.
- Download options are assembled in `build_download_options` / helpers next to it.
- Manual (uploader) subtitles use yt-dlp `writesubtitles` + `writeautomaticsub=False`. Do not add auto-caption fallback unless it is an explicit, separate UI option.

## Release ZIP (maintainers)

Portable builds are **not** committed. Maintainers build on Windows:

```powershell
.\package.ps1
```

Upload `dist\YTDL-GUI.zip` to a GitHub Release. See `README.md` for details.

## Issues

When reporting download failures, include:

- App version or git commit
- yt-dlp version (if known)
- OS version
- A **public** sample URL if possible (or a clear description if the URL cannot be shared)
- Log lines from the app (redact personal paths if needed)

## License

By contributing, you agree that your contributions are licensed under the MIT License.
