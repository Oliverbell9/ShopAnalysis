# Enforce legal-hold-on-create for protected Olist objects in every environment.
# Other prefixes retain their existing behavior; this policy grants no access.
# Explicit denies are intentional and must be reviewed before any deployment.
data "aws_iam_policy_document" "protected_olist_bucket" {
  statement {
    sid     = "DenyUnprotectedOlistUpload"
    effect  = "Deny"
    actions = ["s3:PutObject"]
    resources = [for env in keys(local.environments) :
      "${aws_s3_bucket.shopanalysis.arn}/${env}/raw/olist/*"
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "StringNotEquals"
      variable = "s3:object-lock-legal-hold"
      values   = ["ON"]
    }
  }

  # No principal may release a hold under protected prefixes using this policy.
  # A future exception workflow requires a separate reviewed policy change.
  statement {
    sid     = "DenyOlistLegalHoldRelease"
    effect  = "Deny"
    actions = ["s3:PutObjectLegalHold"]
    resources = [for env in keys(local.environments) :
      "${aws_s3_bucket.shopanalysis.arn}/${env}/raw/olist/*"
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "StringEquals"
      variable = "s3:object-lock-legal-hold"
      values   = ["OFF"]
    }
  }

  statement {
    sid     = "DenyOlistDeleteMarkersAndVersionDeletes"
    effect  = "Deny"
    actions = ["s3:DeleteObject", "s3:DeleteObjectVersion"]
    resources = [for env in keys(local.environments) :
      "${aws_s3_bucket.shopanalysis.arn}/${env}/raw/olist/*"
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
  }
}

resource "aws_s3_bucket_policy" "shopanalysis_protected_olist" {
  bucket = aws_s3_bucket.shopanalysis.id
  policy = data.aws_iam_policy_document.protected_olist_bucket.json

  depends_on = [aws_s3_bucket_public_access_block.shopanalysis]
}
