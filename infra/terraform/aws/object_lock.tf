# ADR-001: enabling Object Lock on an existing bucket is irreversible.
# No default retention period. Protected uploads request legal hold ON.
# This file is for local review; do not apply without separate authorization.
resource "aws_s3_bucket_object_lock_configuration" "shopanalysis" {
  bucket              = aws_s3_bucket.shopanalysis.id
  object_lock_enabled = "Enabled"

  depends_on = [aws_s3_bucket_versioning.shopanalysis]
}
