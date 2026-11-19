import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import settings


IMAGE_LIMIT = 10 * 1024 * 1024
VIDEO_LIMIT = 100 * 1024 * 1024
MEDIA_NAME_PATTERN = re.compile(r"^[a-f0-9]{32}\.(?:jpg|jpeg|png|webp|mp4|webm)$")

MEDIA_TYPES = {
    ".jpg": ("image", "image/jpeg"),
    ".jpeg": ("image", "image/jpeg"),
    ".png": ("image", "image/png"),
    ".webp": ("image", "image/webp"),
    ".mp4": ("video", "video/mp4"),
    ".webm": ("video", "video/webm"),
}


def media_path(filename: str) -> Path | None:
    if not MEDIA_NAME_PATTERN.fullmatch(filename):
        return None
    return settings.MEDIA_ROOT / filename


def _signature_matches(mime_type: str, header: bytes) -> bool:
    if mime_type == "image/jpeg":
        return header.startswith(b"\xff\xd8\xff")
    if mime_type == "image/png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/webp":
        return header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    if mime_type == "video/mp4":
        return len(header) >= 12 and header[4:8] == b"ftyp"
    if mime_type == "video/webm":
        return header.startswith(b"\x1a\x45\xdf\xa3")
    return False


async def store_upload(upload: UploadFile, *, expected_type: str | None = None) -> dict:
    extension = Path(upload.filename or "").suffix.lower()
    media_type, mime_type = MEDIA_TYPES.get(extension, (None, None))
    if not media_type or (expected_type and media_type != expected_type):
        raise HTTPException(status_code=400, detail="Choose a supported JPG, PNG, WEBP, MP4, or WEBM file.")

    content_type = (upload.content_type or "").lower()
    if content_type and content_type not in {mime_type, "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="The uploaded file type does not match its extension.")

    max_bytes = IMAGE_LIMIT if media_type == "image" else VIDEO_LIMIT
    filename = f"{uuid.uuid4().hex}{extension}"
    path = settings.MEDIA_ROOT / filename
    size_bytes = 0
    header = b""

    settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    await upload.seek(0)
    completed = False
    try:
        with path.open("xb") as destination:
            while chunk := await upload.read(1024 * 1024):
                size_bytes += len(chunk)
                if size_bytes > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Files must be no larger than {max_bytes // (1024 * 1024)} MB.",
                    )
                if len(header) < 16:
                    header += chunk[:16 - len(header)]
                destination.write(chunk)

        if not size_bytes or not _signature_matches(mime_type, header):
            raise HTTPException(status_code=400, detail="The file contents do not match a supported media format.")
        completed = True
        return {
            "filename": filename,
            "url": f"/api/v1/posts/media/{filename}",
            "media_type": media_type,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
        }
    finally:
        if not completed:
            path.unlink(missing_ok=True)


def delete_media_files(items: list[dict]) -> None:
    for item in items:
        path = media_path(item.get("filename", ""))
        if path is not None:
            path.unlink(missing_ok=True)
