"""Offline contract tests for ingestion.object_store.aws_legal_hold.

No AWS credentials or network calls are used. Run from the ShopAnalysis root.
"""
from __future__ import annotations

import base64
import hashlib
import io
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from ingestion.object_store.aws_legal_hold import upload_aws_legal_hold

MODULE = 'ingestion.object_store.aws_legal_hold.append_audit_event'
BUCKET = 'example-bucket'
KEY = 'dev/raw/olist/orders/ingest_date=2026-10-25/batch_id=abc/part-00000.parquet'
VERSION = 'v-123'
DATA = b'example parquet payload for mocked tests'


class Body:
    def __init__(self, data):
        self.data = data
        self.closed = False

    def iter_chunks(self, chunk_size):
        yield self.data

    def close(self):
        self.closed = True


def error(code, status):
    return ClientError({'Error': {'Code': code, 'Message': code},
                        'ResponseMetadata': {'HTTPStatusCode': status}}, 'PutObject')


@pytest.fixture
def case(tmp_path):
    path = tmp_path / 'part-00000.parquet'
    path.write_bytes(DATA)
    s3 = Mock()
    s3.put_object.return_value = {'VersionId': VERSION}
    s3.get_object_legal_hold.return_value = {'LegalHold': {'Status': 'ON'}}
    s3.get_object.side_effect = lambda **kwargs: {'Body': Body(DATA)}
    s3.head_object.return_value = {'VersionId': VERSION}
    return s3, path, tmp_path / 'audit.jsonl'


def call(case):
    s3, path, audit = case
    return upload_aws_legal_hold(s3, BUCKET, KEY, path,
                                 {'batch-id': 'abc', 'entity': 'orders'}, audit_path=audit)


def test_created_requests_hold_atomically_and_verifies_exact_version(case):
    s3, _, _ = case
    with patch(MODULE) as audit:
        assert call(case) == 'CREATED'
    args = s3.put_object.call_args.kwargs
    assert args['IfNoneMatch'] == '*'
    assert args['ObjectLockLegalHoldStatus'] == 'ON'
    assert args['ContentLength'] == len(DATA)
    assert args['ContentMD5'] == base64.b64encode(hashlib.md5(DATA, usedforsecurity=False).digest()).decode('ascii')
    assert args['Metadata']['sha256'] == hashlib.sha256(DATA).hexdigest()
    assert s3.get_object_legal_hold.call_args.kwargs['VersionId'] == VERSION
    assert s3.get_object.call_args.kwargs['VersionId'] == VERSION
    assert [c.kwargs['outcome'] for c in audit.call_args_list] == ['ATTEMPTED', 'CREATED']


@pytest.mark.parametrize('version', [None, '', 'null'])
def test_missing_create_version_fails_closed(case, version):
    s3, _, _ = case
    s3.put_object.return_value = {'VersionId': version}
    with patch(MODULE) as audit, pytest.raises(RuntimeError, match='MISSING_VERSION_ID_AFTER_CREATE'):
        call(case)
    s3.get_object_legal_hold.assert_not_called()
    assert [c.kwargs['outcome'] for c in audit.call_args_list] == ['ATTEMPTED', 'VERIFICATION_FAILED']


def test_hold_off_fails_closed(case):
    s3, _, _ = case
    s3.get_object_legal_hold.return_value = {'LegalHold': {'Status': 'OFF'}}
    with patch(MODULE) as audit, pytest.raises(RuntimeError, match='LEGAL_HOLD_NOT_VERIFIED'):
        call(case)
    assert [c.kwargs['outcome'] for c in audit.call_args_list] == ['ATTEMPTED', 'VERIFICATION_FAILED']


def test_created_content_mismatch_fails_closed(case):
    s3, _, _ = case
    s3.get_object.side_effect = lambda **kwargs: {'Body': Body(b'different')}
    with patch(MODULE), pytest.raises(RuntimeError, match='REMOTE_CONTENT_MISMATCH'):
        call(case)


def test_identical_replay_requires_held_current_version(case):
    s3, _, _ = case
    s3.put_object.side_effect = error('PreconditionFailed', 412)
    with patch(MODULE) as audit:
        assert call(case) == 'IDENTICAL_REPLAY'
    assert s3.head_object.call_args.kwargs == {'Bucket': BUCKET, 'Key': KEY}
    assert s3.get_object_legal_hold.call_args.kwargs['VersionId'] == VERSION
    assert s3.get_object.call_args.kwargs['VersionId'] == VERSION
    assert [c.kwargs['outcome'] for c in audit.call_args_list] == ['ATTEMPTED', 'IDENTICAL_REPLAY']


def test_conflicting_replay_rejected(case):
    s3, _, _ = case
    s3.put_object.side_effect = error('PreconditionFailed', 412)
    s3.get_object.side_effect = lambda **kwargs: {'Body': Body(b'different')}
    with patch(MODULE) as audit, pytest.raises(RuntimeError, match='PROTECTED_BATCH_CONFLICT'):
        call(case)
    assert [c.kwargs['outcome'] for c in audit.call_args_list] == ['ATTEMPTED', 'PROTECTED_BATCH_CONFLICT']


def test_unheld_replay_rejected(case):
    s3, _, _ = case
    s3.put_object.side_effect = error('PreconditionFailed', 412)
    s3.get_object_legal_hold.return_value = {'LegalHold': {'Status': 'OFF'}}
    with patch(MODULE), pytest.raises(RuntimeError, match='LEGAL_HOLD_NOT_VERIFIED'):
        call(case)
    s3.get_object.assert_not_called()


def test_replay_missing_version_rejected(case):
    s3, _, _ = case
    s3.put_object.side_effect = error('PreconditionFailed', 412)
    s3.head_object.return_value = {}
    with patch(MODULE), pytest.raises(RuntimeError, match='MISSING_VERSION_ID'):
        call(case)


def test_unexpected_s3_error_propagates(case):
    s3, _, _ = case
    s3.put_object.side_effect = error('AccessDenied', 403)
    with patch(MODULE), pytest.raises(ClientError):
        call(case)
    s3.head_object.assert_not_called()


def test_audit_failure_prevents_upload(case):
    s3, _, _ = case
    with patch(MODULE, side_effect=OSError('audit unavailable')), pytest.raises(OSError, match='audit unavailable'):
        call(case)
    s3.put_object.assert_not_called()


def test_audit_failure_after_write_does_not_report_success(case):
    s3, _, _ = case
    def audit_side_effect(*args, **kwargs):
        if kwargs['outcome'] == 'CREATED':
            raise OSError('audit unavailable after write')
    with patch(MODULE, side_effect=audit_side_effect), pytest.raises(OSError, match='after write'):
        call(case)
    s3.put_object.assert_called_once()
