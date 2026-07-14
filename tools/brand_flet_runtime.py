from __future__ import annotations

import ctypes
import os
import shutil
import struct
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
ICON_PATH = APP_ROOT / "pic" / "YTDL_LOGO.ico"
RUNTIME_DIR = APP_ROOT / "runtime" / "flet"
RUNTIME_EXE = RUNTIME_DIR / "flet.exe"
MARKER_PATH = RUNTIME_DIR / ".ytdl-runtime-version"

APP_NAME = "YTDL Downloader"
APP_VERSION = "1.0.0.0"
COPYRIGHT = "YTDL Downloader"

RT_ICON = 3
RT_GROUP_ICON = 14
RT_VERSION = 16
LANG_NEUTRAL = 0
LANG_EN_US = 0x0409


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def ensure_windows() -> bool:
    return os.name == "nt"


def source_runtime() -> tuple[Path, str]:
    import flet_desktop
    import flet_desktop.version

    cache_dir = Path(flet_desktop.ensure_client_cached())
    source_dir = cache_dir / "flet"
    source_exe = source_dir / "flet.exe"
    if not source_exe.exists():
        raise FileNotFoundError(f"Flet runtime not found: {source_exe}")
    return source_dir, flet_desktop.version.version


def is_inside(child: Path, parent: Path) -> bool:
    child = child.resolve()
    parent = parent.resolve()
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def copy_runtime_if_needed(source_dir: Path, source_version: str) -> None:
    current_marker = ""
    if MARKER_PATH.exists():
        current_marker = MARKER_PATH.read_text(encoding="utf-8", errors="ignore").strip()

    if RUNTIME_EXE.exists() and current_marker == source_version:
        return

    if RUNTIME_DIR.exists():
        if not is_inside(RUNTIME_DIR, APP_ROOT):
            raise RuntimeError(f"Refusing to remove path outside app root: {RUNTIME_DIR}")
        shutil.rmtree(RUNTIME_DIR)

    RUNTIME_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, RUNTIME_DIR)
    MARKER_PATH.write_text(source_version, encoding="utf-8")


def read_ico(path: Path) -> tuple[list[dict[str, int]], list[bytes]]:
    data = path.read_bytes()
    if len(data) < 6:
        raise ValueError("ICO file is too small")
    reserved, icon_type, count = struct.unpack_from("<HHH", data, 0)
    if reserved != 0 or icon_type != 1 or count <= 0:
        raise ValueError("Unsupported ICO file")

    entries: list[dict[str, int]] = []
    images: list[bytes] = []
    offset = 6
    for index in range(count):
        entry_offset = offset + index * 16
        width, height, colors, reserved_byte, planes, bit_count, size, image_offset = struct.unpack_from(
            "<BBBBHHII", data, entry_offset
        )
        image = data[image_offset : image_offset + size]
        if len(image) != size:
            raise ValueError("ICO image data is truncated")
        entries.append(
            {
                "width": width,
                "height": height,
                "colors": colors,
                "reserved": reserved_byte,
                "planes": planes,
                "bit_count": bit_count,
                "size": size,
            }
        )
        images.append(image)
    return entries, images


def build_group_icon(entries: list[dict[str, int]]) -> bytes:
    group = bytearray(struct.pack("<HHH", 0, 1, len(entries)))
    for resource_id, entry in enumerate(entries, start=1):
        group.extend(
            struct.pack(
                "<BBBBHHIH",
                entry["width"],
                entry["height"],
                entry["colors"],
                entry["reserved"],
                entry["planes"],
                entry["bit_count"],
                entry["size"],
                resource_id,
            )
        )
    return bytes(group)


def utf16z(text: str) -> bytes:
    return text.encode("utf-16le") + b"\x00\x00"


def pad4(data: bytes) -> bytes:
    return data + (b"\x00" * ((4 - len(data) % 4) % 4))


def version_block(
    key: str,
    value: bytes = b"",
    children: list[bytes] | None = None,
    value_type: int = 1,
    value_length: int | None = None,
) -> bytes:
    children = children or []
    body = b"\x00" * 6 + utf16z(key)
    body = pad4(body)
    body += value
    body = pad4(body)
    body += b"".join(children)
    if value_length is None:
        value_length = len(value) // 2 if value_type == 1 else len(value)
    return struct.pack("<HHH", len(body), value_length, value_type) + body[6:]


def string_value(key: str, value: str) -> bytes:
    return version_block(key, utf16z(value), value_type=1)


def make_version_resource() -> bytes:
    version_ms = (1 << 16) | 0
    version_ls = (0 << 16) | 0
    fixed = struct.pack(
        "<13I",
        0xFEEF04BD,
        0x00010000,
        version_ms,
        version_ls,
        version_ms,
        version_ls,
        0x0000003F,
        0,
        0x00040004,
        0x00000001,
        0,
        0,
        0,
    )

    strings = [
        string_value("CompanyName", APP_NAME),
        string_value("FileDescription", APP_NAME),
        string_value("FileVersion", APP_VERSION),
        string_value("InternalName", "YTDL Downloader"),
        string_value("LegalCopyright", COPYRIGHT),
        string_value("OriginalFilename", "YTDL Downloader.exe"),
        string_value("ProductName", APP_NAME),
        string_value("ProductVersion", APP_VERSION),
    ]
    string_table = version_block("040904B0", children=strings)
    string_file_info = version_block("StringFileInfo", children=[string_table])
    translation = version_block(
        "Translation",
        struct.pack("<HH", LANG_EN_US, 1200),
        value_type=0,
        value_length=4,
    )
    var_file_info = version_block("VarFileInfo", children=[translation])
    return version_block(
        "VS_VERSION_INFO",
        fixed,
        children=[string_file_info, var_file_info],
        value_type=0,
        value_length=len(fixed),
    )


def update_resource(handle: int, resource_type: int, resource_name: int, lang: int, data: bytes) -> None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    update = kernel32.UpdateResourceW
    update.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_ushort,
        ctypes.c_void_p,
        ctypes.c_uint,
    ]
    update.restype = ctypes.c_bool
    buffer = ctypes.create_string_buffer(data)
    ok = update(
        handle,
        ctypes.c_void_p(resource_type),
        ctypes.c_void_p(resource_name),
        lang,
        buffer,
        len(data),
    )
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())


def patch_exe(exe_path: Path, icon_path: Path) -> None:
    if not icon_path.exists():
        raise FileNotFoundError(f"Icon not found: {icon_path}")
    entries, images = read_ico(icon_path)
    group_icon = build_group_icon(entries)
    version = make_version_resource()

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    begin = kernel32.BeginUpdateResourceW
    begin.argtypes = [ctypes.c_wchar_p, ctypes.c_bool]
    begin.restype = ctypes.c_void_p
    end = kernel32.EndUpdateResourceW
    end.argtypes = [ctypes.c_void_p, ctypes.c_bool]
    end.restype = ctypes.c_bool

    handle = begin(str(exe_path), False)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())

    discard = True
    try:
        for lang in (LANG_EN_US, LANG_NEUTRAL):
            for resource_id, image in enumerate(images, start=1):
                update_resource(handle, RT_ICON, resource_id, lang, image)
            update_resource(handle, RT_GROUP_ICON, 1, lang, group_icon)
            update_resource(handle, RT_GROUP_ICON, 32512, lang, group_icon)
            update_resource(handle, RT_VERSION, 1, lang, version)
        discard = False
    finally:
        if not end(handle, discard):
            raise ctypes.WinError(ctypes.get_last_error())


def main() -> int:
    if not ensure_windows():
        return 0
    try:
        source_dir, source_version = source_runtime()
        copy_runtime_if_needed(source_dir, source_version)
        patch_exe(RUNTIME_EXE, ICON_PATH)
        print(f"Prepared branded Flet runtime: {RUNTIME_EXE}")
        return 0
    except Exception as exc:
        return fail(f"Could not prepare branded Flet runtime: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
