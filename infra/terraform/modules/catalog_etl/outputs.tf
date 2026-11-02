output "glue_database_name" {
  value = aws_glue_catalog_database.this.name
}

output "glue_job_names" {
  value = [
    aws_glue_job.bronze_to_silver.name,
    aws_glue_job.silver_to_gold.name,
  ]
}

output "glue_role_arn" {
  value = aws_iam_role.glue.arn
}
