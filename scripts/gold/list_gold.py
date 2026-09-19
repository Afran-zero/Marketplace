from prefect_aws import AwsCredentials
import boto3

creds = AwsCredentials.load("aws-credentials")
s3 = creds.get_boto3_session().client("s3")

bucket = "alphavantage-medallion-kaif12589"
prefix = "gold/stock_analytics/"

print(f"Listing s3://{bucket}/{prefix}\n")

paginator = s3.get_paginator("list_objects_v2")
count = 0
for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
    for obj in page.get("Contents", []):
        print(f"  {obj['Key']}  ({obj['Size']} bytes)")
        count += 1
        if count >= 15:
            break
    if count >= 15:
        break

print(f"\n(Showing first 15 objects. Total may be more.)")