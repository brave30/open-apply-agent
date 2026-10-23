"""Outbound-only Supabase job worker. No inbound HTTP server or user passwords."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from urllib.parse import urlsplit, unquote
from urllib.request import Request, urlopen

from .profile import Profile


def rpc(name, payload):
    origin = os.environ['SUPABASE_URL'].rstrip('/')
    request = Request(origin + '/rest/v1/rpc/' + name,
                      data=json.dumps({'worker_token': os.environ['OPEN_APPLY_WORKER_TOKEN'], **payload}).encode(),
                      headers={'apikey': os.environ['SUPABASE_PUBLISHABLE_KEY'], 'Content-Type': 'application/json'})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def prepare_profile(job, directory):
    """Materialize the enqueue-time snapshot; validate URL, ownership and file bytes."""
    p = job['profile']
    resume = p.get('resume')
    resumes = []
    directory.mkdir(parents=True, exist_ok=True)
    if resume:
        origin = os.environ['SUPABASE_URL'].rstrip('/')
        url = job['resume_url']
        parsed = urlsplit(url)
        expected = '/storage/v1/object/sign/resumes/' + resume['path']
        if (parsed.scheme != 'https' or parsed.netloc != urlsplit(origin).netloc or
                unquote(parsed.path) != expected or parsed.fragment or
                not resume['path'].startswith(job['user_id'] + '/')):
            raise ValueError('Invalid private resume URL.')
        # Redirects are rejected so a signed URL cannot redirect to another host.
        from urllib.request import HTTPRedirectHandler, build_opener
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                raise ValueError('Resume redirects are not allowed.')
        with build_opener(NoRedirect).open(url, timeout=30) as response:
            raw = response.read(5 * 1024 * 1024 + 1)
        if not raw or len(raw) > 5 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != resume['sha256']:
            raise ValueError('Resume size or hash mismatch.')
        suffix = Path(resume['name']).suffix.lower()
        if suffix not in {'.pdf', '.docx', '.txt'}:
            raise ValueError('Unsupported resume file.')
        name = 'resume' + suffix
        (directory / name).write_bytes(raw)
        resumes = [{'path': name, 'sha256': resume['sha256']}]
    profile = Profile.model_validate({
        'schema_version': 1, 'candidate_id': job['user_id'], 'synthetic': False,
        **{k: p[k] for k in ('personal', 'education', 'work_experience', 'skills', 'verified_answers')},
        'resume_files': resumes,
    })
    path = directory / 'profile.json'
    path.write_text(profile.model_dump_json(indent=2), encoding='utf-8')
    return path


def progress(output):
    runs = sorted(output.glob('*'))
    if not runs:
        return 'Loading the OpenWebRL model on GPU 0…', None
    run = runs[-1]
    images = sorted(run.glob('model-*.png'))
    preview = None
    if images:
        from PIL import Image
        try:
            with Image.open(images[-1]) as im:
                im.thumbnail((960, 800))
                buffer = io.BytesIO()
                im.convert('RGB').save(buffer, format='JPEG', quality=65)
                preview = 'data:image/jpeg;base64,' + base64.b64encode(buffer.getvalue()).decode()
        except (OSError, ValueError):
            pass  # A screenshot may still be being written.
    return f'OpenWebRL is working · observation {len(images)}', preview


def collect_result(output, job):
    paths = sorted(output.glob('*/result.json'))
    if not paths:
        raise ValueError('Runner did not produce a result. See server logs.')
    result = json.loads(paths[-1].read_text())
    if result.get('policy') != 'openwebrl_visual' or result.get('submitted'):
        raise ValueError('Unexpected runner policy or submission state.')
    review = json.loads((paths[-1].parent / 'review.json').read_text())
    correct = {f['field_id'] for f in result['filled'] if f['correct']}
    result['answers'] = {f['id']: f['value'] for f in review
                         if f['id'] in correct and f['type'] != 'file' and f['value']}
    result['resume'] = job['profile'].get('resume') if any(
        f['id'] in correct and f['type'] == 'file' and f['files'] for f in review) else None
    return result


def stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def handle(job, root):
    directory = root / 'jobs' / job['id']
    output = directory / 'runs'
    output.mkdir(parents=True, exist_ok=True)
    lease = {'job_id': job['id'], 'lease_id': job['lease_id']}
    process = None
    try:
        path = prepare_profile(job, directory / 'candidate')
        with (directory / 'runner.log').open('w') as log:
            # All arguments are trusted constants or validated IDs/paths, never shell strings.
            process = subprocess.Popen([str(root / 'run-agent.sh'), '--application-id', job['application_id'],
                                        '--profile', str(path), '--personal-profile', '--output', str(output)],
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            started = time.monotonic()
            while process.poll() is None:
                message, preview = progress(output)
                state = rpc('agent_worker_report', {**lease, 'new_status': 'running',
                            'message': message, 'job_result': None, 'preview': preview})
                if state != 'running' or time.monotonic() - started > 2100:
                    stop(process)
                    if state == 'running':
                        raise TimeoutError('Agent exceeded its run time limit.')
                    return
                time.sleep(5)
        if process.returncode == 42:
            rpc('agent_worker_report', {**lease, 'new_status': 'queued',
                'message': 'Waiting for GPU 0 to become available.', 'job_result': None, 'preview': None})
            return
        result = collect_result(output, job)
        _, preview = progress(output)
        rpc('agent_worker_report', {**lease, 'new_status': 'completed', 'message': 'Ready for your review.',
                                   'job_result': result, 'preview': preview})
    except Exception as exc:
        if process:
            stop(process)
        print(f"Job {job['id']} failed: {type(exc).__name__}", flush=True)
        rpc('agent_worker_report', {**lease, 'new_status': 'failed',
            'message': 'The agent could not finish. Please retry; server diagnostics were saved.',
            'job_result': None, 'preview': None})


def main():
    root = Path(os.environ.get('OPEN_APPLY_ROOT', '/data01/tmalekar/open-apply'))
    os.umask(0o077)
    print('Open Apply outbound worker starting.', flush=True)
    while True:
        try:
            job = rpc('agent_worker_claim', {})
            if job:
                handle(job, root)
        except Exception as exc:
            print(f'Worker connection error: {type(exc).__name__}', flush=True)
        time.sleep(5)


if __name__ == '__main__':
    main()
