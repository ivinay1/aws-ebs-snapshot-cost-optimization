
import os
import boto3
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError

# AWS clients
ec2 = boto3.client("ec2")
sns = boto3.client("sns")

# Configuration
RETENTION_DAYS = 30
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]

# Safety switch: deletion is OFF by default
CLEANUP_ENABLED = (
    os.environ.get("CLEANUP_ENABLED", "false").lower() == "true"
)


def lambda_handler(event, context):
    cutoff = datetime.now(timezone.utc) - timedelta(
        days=RETENTION_DAYS
    )

    paginator = ec2.get_paginator("describe_snapshots")

    scanned = 0
    candidates = 0
    deleted = 0
    errors = 0
    candidate_ids = []

    print(f"Cleanup enabled: {CLEANUP_ENABLED}")
    print(f"Snapshots older than: {cutoff.isoformat()}")

    for page in paginator.paginate(OwnerIds=["self"]):
        for snapshot in page["Snapshots"]:
            scanned += 1
            snapshot_id = snapshot["SnapshotId"]

            tags = {
                tag["Key"]: tag["Value"]
                for tag in snapshot.get("Tags", [])
            }

            # Require an explicit approval tag
            if tags.get("Cleanup", "").lower() != "approved":
                continue

            # Skip recent snapshots
            if snapshot["StartTime"] > cutoff:
                continue

            candidates += 1
            candidate_ids.append(snapshot_id)

            # Default behavior: report, do not delete
            if not CLEANUP_ENABLED:
                print(f"DRY RUN: Would delete {snapshot_id}")
                continue

            try:
                ec2.delete_snapshot(SnapshotId=snapshot_id)
                deleted += 1
                print(f"DELETE REQUESTED: {snapshot_id}")

            except ClientError as error:
                errors += 1
                print(
                    f"ERROR for {snapshot_id}: "
                    f"{error.response['Error']['Code']} - "
                    f"{error.response['Error']['Message']}"
                )

    result = {
        "scanned": scanned,
        "candidates": candidates,
        "candidate_snapshot_ids": candidate_ids,
        "deleted": deleted,
        "errors": errors,
        "dry_run": not CLEANUP_ENABLED,
    }

    print(f"Summary: {result}")

    # Prepare SNS email report
    message = (
        "EBS Snapshot Cleanup Report\n\n"
        f"Snapshots scanned: {scanned}\n"
        f"Cleanup candidates: {candidates}\n"
        f"Snapshot IDs: {', '.join(candidate_ids) if candidate_ids else 'None'}\n"
        f"Snapshots deleted: {deleted}\n"
        f"Errors: {errors}\n"
        f"Dry-run mode: {not CLEANUP_ENABLED}\n\n"
        "Review the candidates and verify backup requirements "
        "before approving any deletion."
    )

    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="EBS Snapshot Cleanup Report",
            Message=message
        )
        print("SNS notification sent successfully.")

    except ClientError as error:
        print(
            "SNS notification failed: "
            f"{error.response['Error']['Code']} - "
            f"{error.response['Error']['Message']}"
        )
        raise

    return result
