import hashlib
import json
from pathlib import Path

import pytest

from auto_apply.worker import collect_result, prepare_profile


def test_worker_rejects_resume_on_other_host_or_other_tenant(tmp_path, monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://sample.supabase.co')
    profile = json.loads(Path('profiles/dummy.json').read_text())
    profile['resume'] = {'path': 'candidate/resume.txt', 'name': 'resume.txt', 'sha256': hashlib.sha256(b'resume').hexdigest()}
    for url in ['https://evil.test/storage/v1/object/sign/resumes/candidate/resume.txt',
                'https://sample.supabase.co/storage/v1/object/sign/resumes/another/resume.txt']:
        with pytest.raises(ValueError, match='Invalid private resume'):
            prepare_profile({'profile': profile, 'user_id': 'candidate', 'resume_url': url}, tmp_path)


def test_result_returns_only_independently_verified_fields(tmp_path):
    run = tmp_path / 'run'
    run.mkdir()
    (run / 'result.json').write_text(json.dumps({'policy': 'openwebrl_visual', 'submitted': False,
        'filled': [{'field_id': 'full_name', 'correct': True}, {'field_id': 'email', 'correct': False}]}))
    (run / 'review.json').write_text(json.dumps([
        {'id': 'full_name', 'type': 'text', 'value': 'Alex'},
        {'id': 'email', 'type': 'email', 'value': 'wrong@example.test'},
        {'id': 'salary', 'type': 'text', 'value': 'invented'},
    ]))
    result = collect_result(tmp_path, {'profile': {'resume': None}})
    assert result['answers'] == {'full_name': 'Alex'}
    assert result['resume'] is None


def test_worker_rejects_submitted_or_baseline_result(tmp_path):
    run = tmp_path / 'run'
    run.mkdir()
    for result in [{'policy': 'baseline', 'submitted': False}, {'policy': 'openwebrl_visual', 'submitted': True}]:
        (run / 'result.json').write_text(json.dumps(result))
        with pytest.raises(ValueError, match='Unexpected runner'):
            collect_result(tmp_path, {})
