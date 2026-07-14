# How to publish a GitHub Release

This project ships **source on git** and **portable ZIP on Releases**.

## One-time GitHub setup

1. Create a new public repository (empty, no README if you already have local files).
2. From this folder:

   ```bat
   git init
   git add .
   git status
   git commit -m "Initial open-source release"
   git branch -M main
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```

3. Confirm large/local folders are **not** staged: `python/`, `runtime/`, `bin/`, `dist/`, `.venv/`, `cache/`.

## Every release

### 1. Bump app version (source)

Edit `src/ytdl_gui.py`:

```python
APP_VERSION = "1.0.1"          # must match the Release tag (v1.0.1 or 1.0.1)
GITHUB_REPO = "yourname/YTDL"  # required for in-app update toast
```

Older installs compare their local `APP_VERSION` against the latest GitHub Release tag. If remote is newer, the app shows a toast on startup (no auto-download).

```bat
git add -A
git commit -m "Prepare v1.0.1"
git push
```

### 2. Build the portable ZIP (Windows build machine)

Prerequisites on the build PC:

- `.venv` with `pip install -r requirements.txt`
- `bin\deno.exe` (or run `tools\install_deno.ps1`)
- `runtime\flet\` present (Flet desktop runtime used by packaging)

```powershell
.\package.ps1
```

Artifact:

```text
dist\YTDL-GUI.zip
```

### 3. Create the GitHub Release

1. GitHub → **Releases** → **Draft a new release**
2. **Choose a tag**: `v1.0.0` (create new tag on publish)
3. **Title**: `v1.0.0`
4. **Describe** user-facing changes (Chinese or English is fine)
5. **Attach** `dist\YTDL-GUI.zip`
6. Publish

### 4. README link

The main README points users to Releases for the ZIP. After the first release exists, the download link works for visitors.

## Checklist before upload

- [ ] Unzip `YTDL-GUI.zip` on a clean folder and run `01.Install.bat`
- [ ] Launch via shortcut / `02.RUN.bat`
- [ ] Download one short public video
- [ ] Optional: test “下載頻道主 CC 字幕”
- [ ] Confirm ZIP size is reasonable (typically hundreds of MB because of embedded Python)

## What not to do

- Do not commit `dist\YTDL-GUI.zip` into the repo
- Do not commit `python\` or `runtime\`
- Do not upload only `src\` without the packaging layout if you intend “double-click for non-devs”
