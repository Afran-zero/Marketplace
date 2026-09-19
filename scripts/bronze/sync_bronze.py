from pathlib import Path
from prefect_aws.s3 import S3Bucket

S3_PREFIX = "bronze/alpha_vantage/daily_prices/"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_BRONZE = PROJECT_ROOT / "data" / "bronze"


def main():
    LOCAL_BRONZE.mkdir(parents=True, exist_ok=True)

    bucket = S3Bucket.load("bronze-bucket")
    print(f"Syncing from s3://{bucket.bucket_name}/{S3_PREFIX}")
    print(f"Into            {LOCAL_BRONZE}")

    objects = bucket.list_objects(folder=S3_PREFIX)
    downloaded = 0

    for obj in objects:
        key = obj["Key"]
        size = obj["Size"]
        if not key.endswith(".json"):
            continue

        relative = key[len(S3_PREFIX):]
        local_file = LOCAL_BRONZE / relative
        local_file.parent.mkdir(parents=True, exist_ok=True)

        if local_file.exists() and local_file.stat().st_size == size:
            continue  # already downloaded

        client = bucket.credentials.get_boto3_session().client("s3")
        client.download_file(bucket.bucket_name, key, str(local_file))
        downloaded += 1
        print(f"  ↓ {key}  ({size} bytes)")

    print(f"\nDone. Downloaded {downloaded} new files.")


if __name__ == "__main__":
    main()