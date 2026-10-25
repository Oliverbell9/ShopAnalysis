import base64
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ingestion.object_store.offline_governance_exercise import exercise
from ingestion.object_store.governance_evidence import verify_audit_seal
from ingestion.object_store.protected_batch_governance import AuthorizationError


def fixture(tmp_path):
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    approval = dict(approval_ref='synthetic-1', approver_id='synthetic-owner',
                    environment='ci', bucket='synthetic-bucket', key='synthetic/key',
                    reason='synthetic exercise only')
    raw = json.dumps(approval, sort_keys=True, separators=(',', ':'),
                     ensure_ascii=False, allow_nan=False).encode()
    envelope = {'approval': approval,
                'signature_b64': base64.b64encode(private.sign(raw)).decode()}
    params = dict(envelope=envelope, trusted_public_key=public,
                  owner_id='synthetic-owner', environment='ci',
                  bucket='synthetic-bucket', key='synthetic/key',
                  registry_path=tmp_path/'registry.sqlite',
                  audit_path=tmp_path/'audit.jsonl', seal_path=tmp_path/'audit.seal',
                  hmac_key=b'synthetic-key-material-not-for-production-000000')
    return params


def test_integrated_exercise_seals_and_verifies(tmp_path):
    params = fixture(tmp_path)
    result = exercise(**params)
    assert result['status'] == 'PASS'
    assert result['object_deletion_performed'] is False
    assert verify_audit_seal(params['audit_path'], params['seal_path'],
                             hmac_key=params['hmac_key'])
    event = json.loads(params['audit_path'].read_text())
    assert event['authorization_ref'] == 'synthetic-1'
    assert event['outcome'] == 'APPROVAL_CONSUMED_NO_DELETION'


def test_replay_rejected_and_evidence_not_overwritten(tmp_path):
    params = fixture(tmp_path)
    exercise(**params)
    original = params['audit_path'].read_bytes()
    with pytest.raises(FileExistsError):
        exercise(**params)
    assert params['audit_path'].read_bytes() == original


def test_replay_rejected_even_with_fresh_evidence_paths(tmp_path):
    params = fixture(tmp_path)
    exercise(**params)
    params['audit_path'] = tmp_path/'audit2.jsonl'
    params['seal_path'] = tmp_path/'audit2.seal'
    with pytest.raises(AuthorizationError, match='already been consumed'):
        exercise(**params)
    assert not params['audit_path'].exists()


def test_forged_approval_rejected_without_outputs(tmp_path):
    params = fixture(tmp_path)
    params['envelope']['approval']['key'] = 'other'
    with pytest.raises(AuthorizationError):
        exercise(**params)
    assert not params['audit_path'].exists()


def test_audit_tampering_detected(tmp_path):
    params = fixture(tmp_path)
    exercise(**params)
    with params['audit_path'].open('ab') as stream:
        stream.write(b'{}\n')
    with pytest.raises(ValueError, match='changed'):
        verify_audit_seal(params['audit_path'], params['seal_path'],
                          hmac_key=params['hmac_key'])


def test_rejects_same_paths_before_consumption(tmp_path):
    params = fixture(tmp_path)
    params['seal_path'] = params['audit_path']
    with pytest.raises(ValueError, match='distinct'):
        exercise(**params)
    assert not params['registry_path'].exists()
