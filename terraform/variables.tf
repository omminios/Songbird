variable "aws_region" {
  description = "AWS Region for resources"
  type        = string
  default     = "us-east-1"
}

variable "songbird_bucket_name" {
  description = "S3 bucket name for Songbird configuration (from SONGBIRD_CONFIG_BUCKET env var)"
  type        = string
  default     = "songbird3565"
}

variable "spotify_client_id" {
  description = "Spotify OAuth Client ID"
  type        = string
  sensitive   = true
}

variable "spotify_client_secret" {
  description = "Spotify OAuth Client Secret"
  type        = string
  sensitive   = true
}
