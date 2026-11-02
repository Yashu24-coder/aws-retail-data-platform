resource "aws_athena_workgroup" "analysts" {
  name        = "${var.name_prefix}-analysts"
  description = "Analyst workgroup with an enforced scan cap"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    bytes_scanned_cutoff_per_query     = var.athena_bytes_scanned_cutoff

    result_configuration {
      output_location = "s3://${var.curated_bucket_id}/athena-results/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }
}

# ---------------------------------------------------------------- redshift
data "aws_vpc" "default" {
  count   = var.create_redshift && var.vpc_id == "" ? 1 : 0
  default = true
}

data "aws_subnets" "default" {
  count = var.create_redshift && length(var.subnet_ids) == 0 ? 1 : 0

  filter {
    name   = "vpc-id"
    values = [var.vpc_id != "" ? var.vpc_id : data.aws_vpc.default[0].id]
  }
}

locals {
  vpc_id     = var.vpc_id != "" ? var.vpc_id : try(data.aws_vpc.default[0].id, "")
  subnet_ids = length(var.subnet_ids) > 0 ? var.subnet_ids : try(data.aws_subnets.default[0].ids, [])
}

resource "aws_security_group" "redshift" {
  count       = var.create_redshift ? 1 : 0
  name        = "${var.name_prefix}-redshift"
  description = "Redshift Serverless - allow BI tools only"
  vpc_id      = local.vpc_id

  ingress {
    description = "Redshift port from inside the VPC"
    from_port   = 5439
    to_port     = 5439
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_iam_policy_document" "redshift_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["redshift.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "redshift_loader" {
  count              = var.create_redshift ? 1 : 0
  name               = "${var.name_prefix}-redshift-loader"
  assume_role_policy = data.aws_iam_policy_document.redshift_assume.json
}

data "aws_iam_policy_document" "redshift_s3" {
  statement {
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = [var.curated_bucket_arn, "${var.curated_bucket_arn}/*"]
  }
}

resource "aws_iam_role_policy" "redshift_s3" {
  count  = var.create_redshift ? 1 : 0
  name   = "${var.name_prefix}-redshift-s3"
  role   = aws_iam_role.redshift_loader[0].id
  policy = data.aws_iam_policy_document.redshift_s3.json
}

resource "aws_redshiftserverless_namespace" "this" {
  count                 = var.create_redshift ? 1 : 0
  namespace_name        = "${var.name_prefix}-ns"
  db_name               = "analytics"
  admin_username        = "biadmin"
  manage_admin_password = true
  iam_roles             = [aws_iam_role.redshift_loader[0].arn]
  default_iam_role_arn  = aws_iam_role.redshift_loader[0].arn
}

resource "aws_redshiftserverless_workgroup" "bi" {
  count               = var.create_redshift ? 1 : 0
  namespace_name      = aws_redshiftserverless_namespace.this[0].namespace_name
  workgroup_name      = "${var.name_prefix}-bi"
  base_capacity       = var.redshift_base_capacity
  publicly_accessible = false
  subnet_ids          = local.subnet_ids
  security_group_ids  = [aws_security_group.redshift[0].id]

  config_parameter {
    parameter_key   = "enable_user_activity_logging"
    parameter_value = "true"
  }
}
