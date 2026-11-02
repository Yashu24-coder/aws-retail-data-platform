output "athena_workgroup_name" {
  value = aws_athena_workgroup.analysts.name
}

output "athena_results_prefix" {
  value = "s3://${var.curated_bucket_id}/athena-results/"
}

output "redshift_endpoint" {
  value       = var.create_redshift ? aws_redshiftserverless_workgroup.bi[0].endpoint : null
  description = "Null when create_redshift is false"
}
