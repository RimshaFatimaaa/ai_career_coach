from pathlib import Path
from uuid import uuid4

from app.config import get_settings

settings = get_settings()


def _r2_client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def save_bytes(data: bytes, filename: str, folder: str = "uploads") -> str:
    suffix = Path(filename).suffix.lower() or ".bin"
    name = f"{uuid4().hex}{suffix}"
    key = f"{folder}/{name}"
    if settings.r2_enabled:
        _r2_client().put_object(Bucket=settings.r2_bucket, Key=key, Body=data)
        return f"r2://{settings.r2_bucket}/{key}"
    dest_dir = settings.storage_dir / folder
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / name
    path.write_bytes(data)
    return str(path)


def read_path(path: str) -> bytes:
    if path.startswith("r2://"):
        rest = path.removeprefix("r2://")
        bucket, _, key = rest.partition("/")
        obj = _r2_client().get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()
    return Path(path).read_bytes()


def delete_path(path: str) -> bool:
    """Best-effort removal so deleted resumes do not leave files behind."""
    if not path:
        return False
    try:
        if path.startswith("r2://"):
            bucket, _, key = path.removeprefix("r2://").partition("/")
            _r2_client().delete_object(Bucket=bucket, Key=key)
            return True
        target = Path(path).resolve()
        root = Path(settings.storage_dir).resolve()
        if root not in target.parents:
            return False
        target.unlink(missing_ok=True)
        return True
    except Exception:
        return False
