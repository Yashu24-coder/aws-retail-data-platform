output "raw_bucket" {
  description = "Landing bucket for bronze"
  value       = module.storage.raw_bucket_id
}

output "curated_bucket" {
  description = "Bucket holding silver and gold parquet"
  value       = module.storage.curated_bucket_id
}

output "glue_database" {
  description = "Glue catalog database name"
  value       = module.catalog_etl.glue_database_name
}

output "glue_job_names" {
  description = "Names of the two ETL jobs"
  value       = module.catalog_etl.glue_job_names
}

output "athena_workgroup" {
  description = "Workgroup analysts should select in the Athena console"
  value       = module.analytics.athena_workgroup_name
}

output "athena_results_prefix" {
  description = "S3 prefix Athena writes query results to"
  value       = module.analytics.athena_results_prefix
}

output "redshift_endpoint" {
  description = "Redshift Serverless endpoint, null when create_redshift is false"
  value       = module.analytics.redshift_endpoint
}
