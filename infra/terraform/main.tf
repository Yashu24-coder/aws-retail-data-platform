locals {
  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  name_prefix = "${var.project_name}-${var.environment}"
}

data "aws_caller_identity" "current" {}

module "storage" {
  source = "./modules/storage"

  name_prefix         = local.name_prefix
  raw_bucket_name     = var.raw_bucket_name
  curated_bucket_name = var.curated_bucket_name
}

module "catalog_etl" {
  source = "./modules/catalog_etl"

  name_prefix        = local.name_prefix
  raw_bucket_id      = module.storage.raw_bucket_id
  raw_bucket_arn     = module.storage.raw_bucket_arn
  curated_bucket_id  = module.storage.curated_bucket_id
  curated_bucket_arn = module.storage.curated_bucket_arn
  scripts_bucket_id  = module.storage.scripts_bucket_id

  glue_database_name     = var.glue_database_name
  glue_worker_type       = var.glue_worker_type
  glue_number_of_workers = var.glue_number_of_workers
  schedule_expression    = var.schedule_expression
}

module "analytics" {
  source = "./modules/analytics"

  name_prefix        = local.name_prefix
  curated_bucket_id  = module.storage.curated_bucket_id
  curated_bucket_arn = module.storage.curated_bucket_arn
  glue_database_name = var.glue_database_name

  athena_bytes_scanned_cutoff = var.athena_bytes_scanned_cutoff
  create_redshift             = var.create_redshift
  redshift_base_capacity      = var.redshift_base_capacity
  account_id                  = data.aws_caller_identity.current.account_id
  aws_region                  = var.aws_region
  vpc_id                      = var.vpc_id
  subnet_ids                  = var.subnet_ids
}
