"""Document storage: local folder by default, Amazon S3 when S3_BUCKET is set."""
import os
import re

ALLOWED_EXTENSIONS = (".txt", ".md")
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


def safe_name(name):
    """Return a validated file name or raise ValueError (blocks paths like ../../etc/passwd)."""
    if not isinstance(name, str) or not _SAFE_NAME.match(name):
        raise ValueError("name may contain only letters, digits, '.', '_' and '-' (max 100 chars)")
    if not name.lower().endswith(ALLOWED_EXTENSIONS):
        raise ValueError("only .txt and .md files are supported")
    return name


class LocalStorage:
    def __init__(self, root):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def list_names(self):
        return sorted(n for n in os.listdir(self.root) if n.lower().endswith(ALLOWED_EXTENSIONS))

    def read(self, name):
        with open(os.path.join(self.root, safe_name(name)), encoding="utf-8") as f:
            return f.read()

    def write(self, name, text):
        with open(os.path.join(self.root, safe_name(name)), "w", encoding="utf-8") as f:
            f.write(text)


class S3Storage:
    """Stores documents as objects under `prefix` in an S3 bucket. Credentials come from the
    standard AWS chain (an IAM role on AWS; never hard-code keys)."""

    def __init__(self, bucket, prefix="docs/"):
        import boto3  # lazy import

        self._s3 = boto3.client("s3")
        self._bucket = bucket
        self._prefix = prefix

    def list_names(self):
        names = []
        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=self._prefix):
            for obj in page.get("Contents", []):
                name = obj["Key"][len(self._prefix):]
                if name.lower().endswith(ALLOWED_EXTENSIONS) and "/" not in name:
                    names.append(name)
        return sorted(names)

    def read(self, name):
        obj = self._s3.get_object(Bucket=self._bucket, Key=self._prefix + safe_name(name))
        return obj["Body"].read().decode("utf-8")

    def write(self, name, text):
        self._s3.put_object(Bucket=self._bucket, Key=self._prefix + safe_name(name), Body=text.encode("utf-8"))


def make_storage():
    bucket = os.environ.get("S3_BUCKET")
    if bucket:
        return S3Storage(bucket, os.environ.get("S3_PREFIX", "docs/"))
    return LocalStorage(os.environ.get("DOCS_DIR", "sample_docs"))
