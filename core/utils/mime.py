"""MIME validation by magic bytes for supported image types.

Per AGENTS.md: validate file signatures (magic bytes), not file extension.
Used at scan start to reject non-image or unsupported files before loading.
"""

from __future__ import annotations

from pathlib import Path

# Magic-byte signatures (prefix bytes) for supported image types.
# Order matters: longer prefixes must be checked before shorter ones that could match.
_IMAGE_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),  # WEBP: RIFF....WEBP; we check RIFF then bytes 8:12 in get_image_mime
]

# Max bytes to read for signature detection (enough for PNG, JPEG, WebP, HEIC/HEIF ftyp).
_READ_LEN = 16

# HEIC/HEIF (Apple, ISO Base Media): bytes 4-8 = 'ftyp', bytes 8-12 = brand.
_HEIC_BRANDS = frozenset({b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"})


def _webp_check(header: bytes) -> bool:
    """True if header looks like WebP: RIFF + length + WEBP at offset 8."""
    if len(header) < 12 or not header.startswith(b"RIFF"):
        return False
    return header[8:12] == b"WEBP"


def _heic_check(header: bytes) -> bool:
    """True if header looks like HEIC/HEIF: ftyp box at offset 4, HEIC/HEIF brand at 8."""
    if len(header) < 12:
        return False
    return header[4:8] == b"ftyp" and header[8:12] in _HEIC_BRANDS


def get_image_mime(path: Path) -> str | None:
    """Return MIME type if the file has supported image magic bytes, else None.

    Uses only file signature (magic bytes); ignores extension. Returns None for
    missing files, zero-byte files, truncated/corrupted files, or non-image content.
    """
    path = Path(path).resolve()
    if not path.is_file():
        return None
    try:
        with path.open("rb") as f:
            header = f.read(_READ_LEN)
    except OSError:
        return None
    if len(header) == 0:
        return None

    # WebP has signature at offset 8
    if _webp_check(header):
        return "image/webp"

    # HEIC/HEIF (Apple, ISO Base Media) use ftyp box
    if _heic_check(header):
        return "image/heic"

    for signature, mime in _IMAGE_SIGNATURES:
        if signature == b"RIFF":
            continue  # already handled
        if len(header) >= len(signature) and header[: len(signature)] == signature:
            return mime

    return None


def is_supported_image(path: Path) -> bool:
    """Return True if the file is a supported image type by magic bytes."""
    return get_image_mime(path) is not None


def supported_image_mime_types() -> tuple[str, ...]:
    """Return the set of MIME types considered supported images (for documentation/config)."""
    return tuple({mime for _, mime in _IMAGE_SIGNATURES} | {"image/webp", "image/heic"})
