"""
Image upload helper for Supabase Storage using the official Supabase Python client only.

"""

from __future__ import annotations

import os
import uuid
from typing import Optional, Dict, Any


def _try_import_boto3():
    return None, None  # boto3 not used


def _try_import_supabase():
    try:
        from supabase import create_client  # type: ignore
        return create_client
    except Exception:
        return None


def _secure_filename(name: str) -> str:
    # Minimal filename sanitizer to avoid adding werkzeug dependency
    keep = "-_.()abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    cleaned = "".join(c if c in keep else "_" for c in name)
    # Avoid empty
    return cleaned or str(uuid.uuid4())


def _guess_content_type(filename: str, default: str = "application/octet-stream") -> str:
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
    }.get(ext, default)


def _build_public_url(bucket: str, object_path: str) -> Optional[str]:
    supabase_url = os.environ.get("SUPABASE_URL")
    if supabase_url:
        return f"{supabase_url.rstrip('/')}/storage/v1/object/public/{bucket}/{object_path}"
    return None


def _get_bucket_name() -> Optional[str]:
    return os.environ.get("SUPABASE_BUCKET")


def _get_supabase_client():
    create_client = _try_import_supabase()
    if not create_client:
        return None
    url = os.environ.get("SUPABASE_URL")
    key = (
        # os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        # or os.environ.get("SUPABASE_ANON_KEY")
        os.environ.get("SUPABASE_S3_KEY")
    )
    if not (url and key):
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


# boto3 path removed


def _upload_via_supabase_client(
    image_bytes: bytes,
    bucket: str,
    object_path: str,
    content_type: str,
) -> Dict[str, Any]:
    client = _get_supabase_client()
    if not client:
        return {"success": False, "error": "Supabase client not available or misconfigured"}
    try:
        # Latest Supabase storage API approach
        file_options = {
            "content-type": content_type,
            "x-upsert": "true"
        }
        
        response = client.storage.from_(bucket).upload(
            object_path,
            image_bytes,
            file_options
        )
        return {"success": True, "client": client}
    except Exception as e:
        return {"success": False, "error": f"Supabase upload failed: {e}"}


def upload_image(
    image_bytes: bytes,
    filename: str,
    content_type: Optional[str] = None,
    folder: Optional[str] = None,
) -> Dict[str, Any]:
    """Upload image bytes to Supabase Storage.

    Returns dict with:
    - success (bool)
    - bucket, object_path
    - public_url (if resolvable)
    - method ("boto3" | "supabase")
    - error (on failure)
    """
    bucket = _get_bucket_name()
    if not bucket:
        return {"success": False, "error": "Bucket not configured (S3_BUCKET_NAME or SUPABASE_BUCKET)"}

    safe_name = _secure_filename(filename or "image.jpg")
    folder = _secure_filename(folder or os.environ.get("S3_UPLOAD_FOLDER", "avatars"))
    object_path = f"{folder}/{uuid.uuid4()}_{safe_name}"
    ctype = content_type or _guess_content_type(safe_name)

    # Supabase client only
    client = None
    method = None  # Initialize method variable
    last_error = None  # Initialize error variable
    
    r = _upload_via_supabase_client(image_bytes, bucket, object_path, ctype)
    if r.get("success"):
        method = "supabase"
        client = r.get("client")
    else:
        last_error = r.get("error")

    if not method:
        return {
            "success": False,
            "bucket": bucket,
            "object_path": object_path,
            "error": last_error or "No suitable upload method available",
        }

    # Resolve public URL using latest Supabase API
    public_url: Optional[str] = None
    try:
        if client is not None:
            public_url = client.storage.from_(bucket).get_public_url(object_path)
        if not public_url:
            public_url = _build_public_url(bucket, object_path)
    except Exception:
        public_url = _build_public_url(bucket, object_path)

    return {
        "success": True,
        "bucket": bucket,
        "object_path": object_path,
        "public_url": public_url,
        "method": method,
        "content_type": ctype,
    }


__all__ = ["upload_image"]
