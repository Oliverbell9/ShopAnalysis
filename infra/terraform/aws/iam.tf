locals {
  github_repository = "Oliverbell9/ShopAnalysis"

  environments = {
    dev = {
    }
    ci = {
    }
    prod = {
    }
  }
}

data "aws_iam_policy_document" "github_oidc_trust" {
  for_each = local.environments

  statement {
    sid     = "GitHubActionsOIDC"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type = "Federated"

      identifiers = [
        aws_iam_openid_connect_provider.github.arn
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"

      values = [
        "sts.amazonaws.com"
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"

      values = [
        "repo:${local.github_repository}:environment:${each.key}"
      ]
    }
  }
}

resource "aws_iam_role" "github_s3" {
  for_each = local.environments

  name = "shopanalysis-${each.key}-s3-role"

  assume_role_policy = data.aws_iam_policy_document.github_oidc_trust[
    each.key
  ].json

  tags = {
    Project     = "ShopAnalysis"
    Environment = each.key
    ManagedBy   = "Terraform"
  }
}

data "aws_iam_policy_document" "environment_s3" {
  for_each = local.environments

  statement {
    sid    = "ListEnvironmentPrefix"
    effect = "Allow"

    actions = [
      "s3:ListBucket"
    ]

    resources = [
      aws_s3_bucket.shopanalysis.arn
    ]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"

      values = [
        each.key,
        "${each.key}/",
        "${each.key}/*"
      ]
    }
  }

  statement {
    sid    = "ReadAndUploadEnvironmentObjects"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:GetObjectLegalHold",
      "s3:PutObject",
      "s3:PutObjectLegalHold"
    ]

    resources = [
      "${aws_s3_bucket.shopanalysis.arn}/${each.key}/*"
    ]
  }

  # An uploader may create a legal hold ON, but must never release one.
  statement {
    sid       = "DenyReleaseOfLegalHold"
    effect    = "Deny"
    actions   = ["s3:PutObjectLegalHold"]
    resources = ["${aws_s3_bucket.shopanalysis.arn}/${each.key}/*"]

    condition {
      test     = "StringEquals"
      variable = "s3:object-lock-legal-hold"
      values   = ["OFF"]
    }
  }

  # Normal CI/ingestion roles cannot delete protected history, including versions.
  statement {
    sid       = "DenyDeleteEnvironmentObjects"
    effect    = "Deny"
    actions   = ["s3:DeleteObject", "s3:DeleteObjectVersion"]
    resources = ["${aws_s3_bucket.shopanalysis.arn}/${each.key}/*"]
  }

}

resource "aws_iam_role_policy" "environment_s3" {
  for_each = local.environments

  name = "shopanalysis-${each.key}-s3-access"
  role = aws_iam_role.github_s3[each.key].id

  policy = data.aws_iam_policy_document.environment_s3[
    each.key
  ].json
}
