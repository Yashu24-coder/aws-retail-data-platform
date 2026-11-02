data "aws_iam_policy_document" "glue_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "glue" {
  name               = "${var.name_prefix}-glue-role"
  assume_role_policy = data.aws_iam_policy_document.glue_assume.json
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

data "aws_iam_policy_document" "glue_data" {
  statement {
    sid     = "ReadRaw"
    actions = ["s3:GetObject", "s3:ListBucket"]
    resources = [
      var.raw_bucket_arn,
      "${var.raw_bucket_arn}/*",
    ]
  }

  statement {
    sid     = "WriteCurated"
    actions = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
    resources = [
      var.curated_bucket_arn,
      "${var.curated_bucket_arn}/*",
    ]
  }

  statement {
    sid       = "Scripts"
    actions   = ["s3:GetObject"]
    resources = ["arn:aws:s3:::${var.scripts_bucket_id}/*"]
  }
}

resource "aws_iam_role_policy" "glue_data" {
  name   = "${var.name_prefix}-glue-data"
  role   = aws_iam_role.glue.id
  policy = data.aws_iam_policy_document.glue_data.json
}

resource "aws_glue_catalog_database" "this" {
  name        = var.glue_database_name
  description = "Retail platform - bronze, silver and gold tables"
}

resource "aws_glue_crawler" "bronze" {
  name          = "${var.name_prefix}-bronze"
  role          = aws_iam_role.glue.arn
  database_name = aws_glue_catalog_database.this.name
  table_prefix  = "bronze_"

  s3_target {
    path = "s3://${var.raw_bucket_id}/bronze/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = { AddOrUpdateBehavior = "InheritFromTable" }
    }
  })
}

resource "aws_glue_job" "bronze_to_silver" {
  name              = "${var.name_prefix}-bronze-to-silver"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "4.0"
  worker_type       = var.glue_worker_type
  number_of_workers = var.glue_number_of_workers
  timeout           = 60

  command {
    name            = "glueetl"
    script_location = "s3://${var.scripts_bucket_id}/jobs/bronze_to_silver.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"        = "python"
    "--glue_database"       = aws_glue_catalog_database.this.name
    "--curated_bucket"      = var.curated_bucket_id
    "--enable-job-insights" = "true"
    "--job-bookmark-option" = "job-bookmark-enable"
    "--TempDir"             = "s3://${var.scripts_bucket_id}/tmp/"
  }
}

resource "aws_glue_job" "silver_to_gold" {
  name              = "${var.name_prefix}-silver-to-gold"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "4.0"
  worker_type       = var.glue_worker_type
  number_of_workers = var.glue_number_of_workers
  timeout           = 60

  command {
    name            = "glueetl"
    script_location = "s3://${var.scripts_bucket_id}/jobs/silver_to_gold.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"        = "python"
    "--glue_database"       = aws_glue_catalog_database.this.name
    "--curated_bucket"      = var.curated_bucket_id
    "--enable-job-insights" = "true"
    "--job-bookmark-option" = "job-bookmark-enable"
    "--TempDir"             = "s3://${var.scripts_bucket_id}/tmp/"
  }
}

resource "aws_glue_trigger" "daily" {
  name          = "${var.name_prefix}-daily"
  schedule      = var.schedule_expression
  type          = "SCHEDULED"
  start_on_creation = true

  actions {
    job_name = aws_glue_job.bronze_to_silver.name
  }
}

resource "aws_glue_trigger" "after_silver" {
  name     = "${var.name_prefix}-after-silver"
  type     = "CONDITIONAL"
  enabled  = true

  predicate {
    conditions {
      job_name = aws_glue_job.bronze_to_silver.name
      state    = "SUCCEEDED"
    }
  }

  actions {
    job_name = aws_glue_job.silver_to_gold.name
  }
}

resource "aws_cloudwatch_metric_alarm" "job_failed_tasks" {
  for_each = {
    bronze_to_silver = aws_glue_job.bronze_to_silver.name
    silver_to_gold   = aws_glue_job.silver_to_gold.name
  }

  alarm_name          = "${each.value}-failed-tasks"
  namespace           = "Glue"
  metric_name         = "glue.driver.aggregate.numFailedTasks"
  dimensions          = { JobName = each.value }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
}
