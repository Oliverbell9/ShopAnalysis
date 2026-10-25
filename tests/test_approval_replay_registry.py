import base64
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ingestion.object_store.approval_replay_registry import consume_signed_approval
from ingestion.object_store.protected_batch_governance import AuthorizationError


def setup():
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw)
    approval = dict(approval_ref='ref-1', approver_id='owner', environment='dev',
                    bucket='bucket', key='raw/object', reason='exceptional owner authorization')
    def sign(record):
        raw = json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                         allow_nan=False).encode()
        return {'approval': record, 'signature_b64': base64.b64encode(private.sign(raw)).decode()}
    return public, approval, sign


def call(tmp_path, envelope, public, **overrides):
    params = dict(trusted_public_key=public, owner_id='owner', environment='dev',
                  bucket='bucket', key='raw/object', registry_path=tmp_path/'registry.sqlite')
    params.update(overrides)
    return consume_signed_approval(envelope, **params)


def test_first_use_then_replay_rejected(tmp_path):
    public, approval, sign = setup()
    assert call(tmp_path, sign(approval), public) == 'ref-1'
    with pytest.raises(AuthorizationError, match='already been consumed'):
        call(tmp_path, sign(approval), public)


def test_reuse_ref_different_signed_payload_rejected(tmp_path):
    public, approval, sign = setup()
    call(tmp_path, sign(approval), public)
    with pytest.raises(AuthorizationError, match='already been consumed'):
        call(tmp_path, sign({**approval, 'reason': 'different reason'}), public)


def test_tampered_approval_not_consumed(tmp_path):
    public, approval, sign = setup()
    envelope = sign(approval)
    envelope['approval'] = {**approval, 'reason': 'tampered'}
    with pytest.raises(AuthorizationError):
        call(tmp_path, envelope, public)
    assert call(tmp_path, sign(approval), public) == 'ref-1'


def test_wrong_object_scope_rejected(tmp_path):
    public, approval, sign = setup()
    with pytest.raises(AuthorizationError):
        call(tmp_path, sign(approval), public, key='other')


def test_concurrent_consumption_allows_exactly_one(tmp_path):
    public, approval, sign = setup()
    envelope = sign(approval)
    def attempt(_):
        try:
            call(tmp_path, envelope, public)
            return True
        except AuthorizationError:
            return False
    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(attempt, range(6)))
    assert results.count(True) == 1
    assert results.count(False) == 5


def test_missing_parent_does_not_create_directories(tmp_path):
    public, approval, sign = setup()
    with pytest.raises(FileNotFoundError):
        call(tmp_path, sign(approval), public, registry_path=tmp_path/'missing'/'registry.sqlite')


def test_symlink_registry_rejected(tmp_path):
    public, approval, sign = setup()
    target = tmp_path/'target.sqlite'
    target.touch()
    link = tmp_path/'registry.sqlite'
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip('symlinks unavailable')
    with pytest.raises(AuthorizationError, match='Unsafe'):
        call(tmp_path, sign(approval), public)
