"""Password gate for secure vault archive, restore, download, and delete."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.auth.auth_utils import get_password_hash, verify_password

MIN_ARCHIVE_PASSWORD_LENGTH = 6


class ArchivePasswordError(ValueError):
    """Raised when archive password validation fails."""


def validate_archive_password(password: str) -> None:
    if not password or len(password.strip()) < MIN_ARCHIVE_PASSWORD_LENGTH:
        raise ArchivePasswordError(
            f"Archive password must be at least {MIN_ARCHIVE_PASSWORD_LENGTH} characters."
        )


def hash_archive_password(password: str) -> str:
    validate_archive_password(password)
    return get_password_hash(password.strip())


def file_is_archived(file_doc: Dict[str, Any]) -> bool:
    return (file_doc.get("vault_status") or "active") == "archived"


def archive_password_required(file_doc: Dict[str, Any]) -> bool:
    return file_is_archived(file_doc) and bool(file_doc.get("archive_password_hash"))


def verify_archived_file_access(
    file_doc: Dict[str, Any],
    archive_password: Optional[str],
) -> bool:
    """Return True when the file is not archived or the archive password matches."""
    if not file_is_archived(file_doc):
        return True
    stored_hash = file_doc.get("archive_password_hash")
    if not stored_hash:
        return True
    if not archive_password:
        return False
    return verify_password(archive_password.strip(), stored_hash)


def require_archived_file_access(
    file_doc: Dict[str, Any],
    archive_password: Optional[str],
) -> None:
    if verify_archived_file_access(file_doc, archive_password):
        return
    raise ArchivePasswordError("Incorrect archive password.")
