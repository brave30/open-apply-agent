import hashlib
import io
import json
import pytest
from auto_apply.cloud import download_profile


def cloud_environment(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://fixture.supabase.co')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY', 'sb_publishable_fixture')
    monkeypatch.setenv('SUPABASE_ACCESS_TOKEN', 'candidate-session-fixture')


def test_cloud_profile_uses_candidate_jwt_and_checks_resume(tmp_path, monkeypatch):
    cloud_environment(monkeypatch)
    resume = b'Synthetic resume contents'
    candidate = '11111111-1111-4111-8111-111111111111'
    p = {'personal': {'full_name': 'Test Candidate', 'email': 'candidate@example.test'}, 'education': [], 'work_experience': [], 'skills': [], 'verified_answers': [], 'resume': {'path': candidate + '/resume.txt', 'name': 'resume.txt', 'sha256': hashlib.sha256(resume).hexdigest()}}
    seen = []
    def opener(req, timeout):
        seen.append(req)
        assert req.get_header('Authorization') == 'Bearer candidate-session-fixture'
        assert req.get_header('Apikey') == 'sb_publishable_fixture'
        if req.full_url.endswith('/auth/v1/user'):
            return io.BytesIO(json.dumps({'id': candidate}).encode())
        if '/rest/v1/candidate_profiles?' in req.full_url:
            assert req.full_url.endswith('user_id=eq.' + candidate)
            return io.BytesIO(json.dumps([p]).encode())
        assert req.full_url.endswith('/storage/v1/object/authenticated/resumes/' + candidate + '/resume.txt')
        return io.BytesIO(resume)
    monkeypatch.setattr('auto_apply.cloud.urlopen', opener)
    path = download_profile(tmp_path)
    saved = json.loads(path.read_text())
    assert saved['candidate_id'] == candidate
    assert saved['synthetic'] is False
    assert saved['resume_files'][0]['sha256'] == hashlib.sha256(resume).hexdigest()
    assert (tmp_path / 'resume.txt').read_bytes() == resume
    assert len(seen) == 3
    p['resume']['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='hash mismatch'):
        download_profile(tmp_path)


@pytest.mark.parametrize('key', ['sb_secret_should_never_be_used', 'invalid-key'])
def test_secret_and_invalid_cloud_keys_rejected(tmp_path, monkeypatch, key):
    cloud_environment(monkeypatch)
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY', key)
    with pytest.raises(ValueError):
        download_profile(tmp_path)


def test_cloud_origin_must_be_project_https_origin(tmp_path, monkeypatch):
    cloud_environment(monkeypatch)
    monkeypatch.setenv('SUPABASE_URL', 'https://fixture.supabase.co.evil.example')
    with pytest.raises(ValueError):
        download_profile(tmp_path)
