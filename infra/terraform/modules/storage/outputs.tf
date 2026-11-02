output "raw_bucket_id" {
  value = aws_s3_bucket.raw.id
}

output "raw_bucket_arn" {
  value = aws_s3_bucket.raw.arn
}

output "curated_bucket_id" {
  value = aws_s3_bucket.curated.id
}

output "curated_bucket_arn" {
  value = aws_s3_bucket.curated.arn
}

output "scripts_bucket_id" {
  value = aws_s3_bucket.scripts.id
}
