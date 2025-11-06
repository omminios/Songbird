provider "aws" {
  profile = "default"
  region  = var.aws_region
}

# S3 Bucket for Songbird configuration and tokens
resource "aws_s3_bucket" "songbird_bucket" {
  bucket = var.songbird_bucket_name

  tags = {
    Name        = "Songbird Config Storage"
    Environment = "production"
    Project     = "Songbird"
  }
}

# Block public access to S3 bucket
resource "aws_s3_bucket_public_access_block" "songbird_block" {
  bucket = aws_s3_bucket.songbird_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Server-side encryption for S3 bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "songbird_encryption" {
  bucket = aws_s3_bucket.songbird_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# IAM role for Lambda execution
resource "aws_iam_role" "songbird_lambda_execution" {
  name = "songbird-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Name    = "Songbird Lambda Execution Role"
    Project = "Songbird"
  }
}

# Attach CloudWatch Logs policy for Lambda
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.songbird_lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# S3 access policy for Lambda
resource "aws_iam_role_policy" "songbird_s3_policy" {
  name = "songbird-s3-access"
  role = aws_iam_role.songbird_lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ]
      Resource = [
        aws_s3_bucket.songbird_bucket.arn,
        "${aws_s3_bucket.songbird_bucket.arn}/*"
      ]
    }]
  })
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "songbird_logs" {
  name              = "/aws/lambda/songbird-sync-manager"
  retention_in_days = 7

  tags = {
    Name    = "Songbird Lambda Logs"
    Project = "Songbird"
  }
}

# Lambda deployment package
# Note: Run 'python build_lambda.py' before 'terraform apply' to create the package
data "local_file" "lambda_package" {
  filename = "${path.module}/lambda_deployment.zip"
}

# Lambda function for sync manager
resource "aws_lambda_function" "sync_manager" {
  filename      = data.local_file.lambda_package.filename
  function_name = "songbird-sync-manager"
  role          = aws_iam_role.songbird_lambda_execution.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 512

  source_code_hash = filebase64sha256(data.local_file.lambda_package.filename)

  environment {
    variables = {
      SONGBIRD_CONFIG_BUCKET = aws_s3_bucket.songbird_bucket.id
      SPOTIFY_CLIENT_ID      = var.spotify_client_id
      SPOTIFY_CLIENT_SECRET  = var.spotify_client_secret
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.songbird_logs,
    aws_iam_role_policy_attachment.lambda_logs,
    aws_iam_role_policy.songbird_s3_policy
  ]

  tags = {
    Name    = "Songbird Sync Manager"
    Project = "Songbird"
  }
}

# EventBridge rule for daily sync schedule
resource "aws_cloudwatch_event_rule" "songbird_daily_sync" {
  name                = "songbird-daily-sync"
  description         = "Trigger Songbird sync daily at 2 AM UTC"
  schedule_expression = "cron(0 2 * * ? *)"

  tags = {
    Name    = "Songbird Daily Sync Schedule"
    Project = "Songbird"
  }
}

# EventBridge target pointing to Lambda
resource "aws_cloudwatch_event_target" "songbird_lambda_target" {
  rule      = aws_cloudwatch_event_rule.songbird_daily_sync.name
  target_id = "songbird-sync-manager"
  arn       = aws_lambda_function.sync_manager.arn
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sync_manager.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.songbird_daily_sync.arn
}