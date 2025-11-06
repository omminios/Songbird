output "s3_bucket_name" {
  description = "Name of the S3 bucket for Songbird configuration"
  value       = aws_s3_bucket.songbird_bucket.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.songbird_bucket.arn
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.sync_manager.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.sync_manager.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for Lambda logs"
  value       = aws_cloudwatch_log_group.songbird_logs.name
}

output "eventbridge_rule_name" {
  description = "Name of the EventBridge rule for scheduled syncs"
  value       = aws_cloudwatch_event_rule.songbird_daily_sync.name
}
