import os
import json
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

CONFIG_FILE = "config.json"

if not os.path.exists(CONFIG_FILE):
    raise FileNotFoundError(
        f"Missing {CONFIG_FILE}. Create it with your credentials."
    )

with open(CONFIG_FILE, "r") as f:
    cfg = json.load(f)

ACCESS_KEY   = cfg["ACCESS_KEY"]
SECRET_KEY   = cfg["SECRET_KEY"]
ENDPOINT_URL = cfg["ENDPOINT_URL"]
BUCKET_NAME  = cfg["BUCKET_NAME"]
PREFIX       = cfg.get("PREFIX", "")
LOCAL_DIR    = cfg["LOCAL_DIR"]
MANIFEST_FILE = "download_manifest.json"



def load_manifest():
    """Load record of already-downloaded files."""
    if not os.path.exists(MANIFEST_FILE):
        return set()

    with open(MANIFEST_FILE, "r") as f:
        return set(json.load(f))


def save_manifest(done_set):
    """Save record of completed downloads."""
    with open(MANIFEST_FILE, "w") as f:
        json.dump(list(done_set), f)


def main():

    # Ensure local path exists
    os.makedirs(LOCAL_DIR, exist_ok=True)

    # S3 client for S3-compatible storage
    s3 = boto3.client(
        "s3",
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(signature_version="s3v4")
    )

    print("Loading resume manifest...")
    downloaded = load_manifest()
    print(f"Already downloaded: {len(downloaded)} files")

    print("Listing bucket contents...")
    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=PREFIX):

        if "Contents" not in page:
            continue

        for obj in page["Contents"]:
            key = obj["Key"]

            # skip "dirs"
            if key.endswith("/"):
                continue

            if key in downloaded:
                print(f"[skip] Already downloaded: {key}")
                continue

            # local file path
            local_path = os.path.join(LOCAL_DIR, key.replace(PREFIX, "", 1))
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            print(f"Downloading: {key}")
            try:
                s3.download_file(BUCKET_NAME, key, local_path)

                downloaded.add(key)
                save_manifest(downloaded)

            except ClientError as e:
                print(f"ERROR downloading {key}: {e}")
                continue

    print("Done.")
    print(f"Total downloaded: {len(downloaded)}")


if __name__ == "__main__":
    main()
