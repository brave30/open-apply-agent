"""Read a signed-in user's Supabase profile with their JWT, never a service key."""
import getpass
import base64
import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen


def download_profile(directory: Path) -> Path:
    origin = os.environ.get('SUPABASE_URL', '').rstrip('/')
    key = os.environ.get('SUPABASE_PUBLISHABLE_KEY', '')
    parsed = urlsplit(origin)
    if parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.supabase.co') or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.port:
        raise ValueError('SUPABASE_URL must be your HTTPS Supabase project origin.')
    if not key or key.startswith('sb_secret_'):
        raise ValueError('Set SUPABASE_PUBLISHABLE_KEY to the public client key, not a secret key.')
    if not key.startswith('sb_publishable_'):
        try:
            claims = json.loads(base64.urlsafe_b64decode(key.split('.')[1] + '==='))
        except (IndexError, ValueError):
            raise ValueError('Expected a Supabase publishable key or legacy anon key.') from None
        if claims.get('role') != 'anon':
            raise ValueError('Only a public anon key is allowed; never use a service-role key.')

    def request(path, *, token=None, data=None, binary=False):
        headers = {'apikey': key}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        if data is not None:
            headers['Content-Type'] = 'application/json'
        req = Request(origin + path, headers=headers, data=json.dumps(data).encode() if data is not None else None)
        try:
            with urlopen(req, timeout=30) as response:
                raw = response.read(5 * 1024 * 1024 + 1)
                if len(raw) > 5 * 1024 * 1024:
                    raise ValueError('Cloud response exceeds the 5 MB limit.')
                return raw if binary else json.loads(raw)
        except HTTPError as exc:
            raise RuntimeError(f'Supabase request failed ({exc.code}). Check sign-in and project configuration.') from None

    token = os.environ.get('SUPABASE_ACCESS_TOKEN')
    if not token:
        email = input('Supabase candidate email: ').strip()
        password = getpass.getpass('Candidate password (not saved): ')
        auth = request('/auth/v1/token?grant_type=password', data={'email': email, 'password': password})
        token = auth['access_token']
    user = request('/auth/v1/user', token=token)
    user_id = user['id']
    profiles = request('/rest/v1/candidate_profiles?select=*&user_id=eq.' + quote(user_id, safe=''), token=token)
    if len(profiles) != 1:
        raise ValueError('Create and save your profile on the website first.')
    p = profiles[0]
    directory.mkdir(parents=True, exist_ok=True)
    resumes = []
    if p.get('resume'):
        resume = p['resume']
        if not resume['path'].startswith(user_id + '/'):
            raise ValueError('Resume does not belong to this candidate.')
        raw = request('/storage/v1/object/authenticated/resumes/' + quote(resume['path'], safe='/'), token=token, binary=True)
        if hashlib.sha256(raw).hexdigest() != resume['sha256']:
            raise ValueError('Cloud resume hash mismatch.')
        name = Path(resume['name']).name
        if name in {'', '.', '..'} or '/' in name or '\\' in name or Path(name).suffix.lower() not in {'.txt', '.pdf', '.docx'}:
            raise ValueError('Invalid resume filename.')
        (directory / name).write_bytes(raw)
        resumes = [{'path': name, 'sha256': resume['sha256']}]
    profile = {'schema_version': 1, 'candidate_id': user_id, 'synthetic': False, 'personal': p['personal'], 'education': p['education'], 'work_experience': p['work_experience'], 'skills': p['skills'], 'verified_answers': p['verified_answers'], 'resume_files': resumes}
    path = directory / 'profile.json'
    path.write_text(json.dumps(profile, indent=2), encoding='utf-8')
    return path
