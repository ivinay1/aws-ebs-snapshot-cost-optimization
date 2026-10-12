# AWS EBS Snapshot Cost Optimization

A serverless AWS automation project that identifies potentially stale Amazon EBS snapshots, reports cleanup candidates, and sends email notifications using Amazon SNS.

The project uses Python and Boto3 to automate snapshot assessment, with a dry-run safety mechanism enabled by default.

## Architecture

```text
Amazon EventBridge Scheduler
            |
            v
      AWS Lambda
      Python + Boto3
            |
            v
    Amazon EC2 / EBS
   Discover snapshots
   Check age and tags
            |
            v
     Cleanup Report
        /       \
       v         v
CloudWatch Logs  Amazon SNS
                 Email Alert
```

## AWS Services Used

- **AWS Lambda:** Executes the Python automation.
- **Amazon EventBridge Scheduler:** Invokes Lambda on a schedule.
- **Amazon EC2 / EBS:** Provides snapshot metadata and snapshot deletion APIs.
- **Amazon SNS:** Sends email notifications containing scan results.
- **Amazon CloudWatch:** Stores Lambda execution logs.
- **AWS IAM:** Controls permissions between AWS services.

## Features

- Automatically discovers EBS snapshots owned by the AWS account.
- Uses pagination when retrieving snapshots.
- Identifies cleanup candidates based on a configurable age threshold and an explicit `Cleanup=approved` tag.
- Supports dry-run mode to report candidates without deleting snapshots.
- Sends email reports through Amazon SNS.
- Logs scan results, deletion requests, and API errors.
- Uses IAM permissions to control access to AWS resources.

## How It Works

1. EventBridge Scheduler invokes the Lambda function.
2. Lambda retrieves EBS snapshots owned by the account.
3. The function checks whether each snapshot has the required cleanup approval tag.
4. Snapshots newer than the configured retention period are skipped.
5. Eligible snapshots are reported as cleanup candidates.
6. If dry-run mode is enabled, no snapshots are deleted.
7. Lambda publishes a summary report to SNS.
8. CloudWatch Logs records execution details for troubleshooting.

## Configuration

The Lambda function uses these environment variables:

| Variable | Example | Purpose |
|---|---|---|
| `CLEANUP_ENABLED` | `false` | Controls whether deletion is enabled |
| `SNS_TOPIC_ARN` | Your SNS topic ARN | Identifies the notification topic |

The retention period is currently configured in the Python source:

```python
RETENTION_DAYS = 30
```

### Dry-Run Safety

Deletion is disabled by default.

```text
CLEANUP_ENABLED=false
```

When dry-run mode is enabled, the function reports eligible candidates without deleting them.

The cleanup approval tag is:

```text
Key: Cleanup
Value: approved
```

The tag indicates that a snapshot has been nominated for cleanup; it does not prove that deletion is safe. Backup retention requirements and snapshot dependencies must be reviewed before enabling deletion.

## Setup

### 1. Create the Lambda Function

Create an AWS Lambda function using a compatible Python runtime and add the project code.

### 2. Configure IAM Permissions

The Lambda execution role requires permissions to:

- Describe EBS snapshots.
- Publish messages to the configured SNS topic.
- Delete snapshots only if deletion functionality is intentionally enabled.

Scope permissions to the required resources and actions wherever supported.

The Lambda execution role also needs the standard permissions required to write execution logs to CloudWatch.

### 3. Create an SNS Topic

Create an SNS Standard topic and subscribe an email address.

Confirm the email subscription before testing notifications.

Set the `SNS_TOPIC_ARN` environment variable to the topic's full ARN.

### 4. Configure EventBridge Scheduler

Create a schedule that invokes the Lambda function at the desired interval.

Verify the schedule's timezone, target function, and execution role.

### 5. Test the Function

Run a Lambda test event and inspect the execution result and CloudWatch Logs.

Confirm that dry-run mode is enabled and that the SNS email report arrives successfully.

## Example Output

```json
{
  "scanned": 2,
  "candidates": 0,
  "candidate_snapshot_ids": [],
  "deleted": 0,
  "errors": 0,
  "dry_run": true
}
```

The values above are an example of a successful dry-run execution, not a guarantee of the results in every account.

## Security and Limitations

- Keep deletion disabled until the cleanup criteria have been thoroughly tested.
- An old snapshot or a snapshot whose original volume no longer exists may still be an important backup.
- This version does not fully validate AWS Backup retention policies or all snapshot dependencies.
- Candidate selection based on age and tags is not sufficient on its own to authorize deletion.
- Actual storage savings have not been measured by this project.
- Never commit AWS access keys, secret credentials, account-specific secrets, or sensitive resource information to GitHub.

## Future Improvements

- Add automated unit tests using mocked Boto3 responses.
- Add stronger validation of snapshot dependencies and backup retention.
- Improve error reporting and CloudWatch alarms.
- Move configuration values into environment variables.
- Add an explicit approval workflow before deletion.
- Use infrastructure as code to deploy the AWS resources.

## Learning Outcomes

This project provided hands-on practice with Python automation, Boto3, serverless architecture, EventBridge scheduling, IAM permissions, SNS notifications, CloudWatch logging, and AWS troubleshooting.

## Disclaimer

This is a learning and portfolio project. It is not a production-ready snapshot deletion system. Review backup policies, dependencies, permissions, and recovery requirements before using any cleanup automation on important AWS resources.
