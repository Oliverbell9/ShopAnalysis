locals {
  github_repository = "Oliverbell9@92740323/ShopAnalysis@1401892624"

  environments = {
    dev = {
      allow_delete = true
    }
    ci = {
      allow_delete = true
    }
    prod = {
      allow_delete = false
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
      "s3:PutObject"
    ]

    resources = [
      "${aws_s3_bucket.shopanalysis.arn}/${each.key}/*"
    ]
  }

  dynamic "statement" {
    for_each = each.value.allow_delete ? [1] : []

    content {
      sid    = "DeleteEnvironmentObjects"
      effect = "Allow"

      actions = [
        "s3:DeleteObject"
      ]

      resources = [
        "${aws_s3_bucket.shopanalysis.arn}/${each.key}/*"
      ]
    }
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
