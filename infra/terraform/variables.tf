variable "aws_region" {
  description = "Region for every resource"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Short name used as a prefix on every resource"
  type        = string
  default     = "retail-platform"
}

variable "environment" {
  description = "dev, staging or prod"
  type        = string
  default     = "dev"
}

variable "raw_bucket_name" {
  description = "Bucket for the bronze layer. Must be globally unique."
  type        = string
  default     = "retail-platform-raw"
}

variable "curated_bucket_name" {
  description = "Bucket for silver and gold. Must be globally unique."
  type        = string
  default     = "retail-platform-curated"
}

variable "glue_database_name" {
  description = "Glue catalog database"
  type        = string
  default     = "retail_platform"
}

variable "glue_worker_type" {
  description = "Glue worker size: G.1X, G.2X or G.4X"
  type        = string
  default     = "G.1X"
}

variable "glue_number_of_workers" {
  description = "Workers per Glue job. 2 is enough for the demo volume."
  type        = number
  default     = 2
}

variable "schedule_expression" {
  description = "Cron for the daily trigger, in UTC. 20:30 UTC = 02:00 IST."
  type        = string
  default     = "cron(30 20 * * ? *)"
}

variable "athena_bytes_scanned_cutoff" {
  description = "Hard cap per Athena query, in bytes. 1 GB stops runaway scans."
  type        = number
  default     = 1073741824
}

variable "create_redshift" {
  description = "Create Redshift Serverless. BILLABLE FROM CREATION - leave false unless demoing."
  type        = bool
  default     = false
}

variable "redshift_base_capacity" {
  description = "Redshift Serverless base RPU capacity (8 is the minimum)"
  type        = number
  default     = 8
}

variable "vpc_id" {
  description = "VPC for Redshift Serverless. Empty uses the default VPC."
  type        = string
  default     = ""
}

variable "subnet_ids" {
  description = "Subnets for Redshift Serverless. Empty uses the default VPC subnets."
  type        = list(string)
  default     = []
}
