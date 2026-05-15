"""
Document Storage — S3 with local filesystem fallback.
Set AWS_* env vars to enable S3; otherwise files stay local.
"""
import os

AWS_KEY    = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET = os.environ.get("AWS_S3_BUCKET")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
USE_S3     = all([AWS_KEY, AWS_SECRET, AWS_BUCKET])

DOCS_LOCAL = os.environ.get("DOCS_OUTPUT_PATH", "/app/generated_docs")
os.makedirs(DOCS_LOCAL, exist_ok=True)


def _s3():
    import boto3
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET,
        region_name=AWS_REGION,
    )


def upload_document(local_path: str, filename: str) -> str:
    """
    Upload a generated PDF to S3 (if configured) or keep it local.
    Returns the S3 key or local path.
    """
    if not USE_S3:
        return local_path

    key = f"documents/{filename}"
    try:
        _s3().upload_file(
            local_path, AWS_BUCKET, key,
            ExtraArgs={"ContentType": "application/pdf"},
        )
        return key
    except Exception as exc:
        print(f"[storage] S3 upload failed, keeping local: {exc}")
        return local_path


def get_download_url(filename: str) -> str:
    """
    Return a signed S3 URL (1 hour) or the local API endpoint.
    """
    if not USE_S3:
        return f"/api/documents/{filename}"

    try:
        url = _s3().generate_presigned_url(
            "get_object",
            Params={"Bucket": AWS_BUCKET, "Key": f"documents/{filename}"},
            ExpiresIn=3600,
        )
        return url
    except Exception as exc:
        print(f"[storage] Presigned URL failed: {exc}")
        return f"/api/documents/{filename}"


def storage_backend() -> str:
    return "s3" if USE_S3 else "local"
