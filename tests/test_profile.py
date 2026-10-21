import copy
from pathlib import Path
import pytest
from auto_apply.forms import match
from auto_apply.profile import Profile
from auto_apply.safety import local_origin

PROFILE = Path(__file__).resolve().parents[1] / "profiles/dummy.json"


def field(label, type="text"):
    return {"label": label, "type": type}


def test_known_and_unknown_answers():
    p = Profile.load(PROFILE)
    assert match(field("Email address"), p) == "personal.email"
    assert match(field("Desired salary"), p) is None
    assert match(field("Why do you want this job?"), p) is None
    assert match(field("Are you authorized to work in the United States?"), p) == "verified_answers.0"


def test_unverified_and_conflicting_answers_stay_empty():
    p = Profile.load(PROFILE)
    p.verified_answers[0].verified = False
    assert match(field(p.verified_answers[0].question), p) is None
    p.verified_answers[0].verified = True
    p.verified_answers.append(copy.deepcopy(p.verified_answers[0]))
    p.verified_answers[1].value = "No"
    assert match(field(p.verified_answers[0].question), p) is None


def test_multiple_education_and_resumes_require_human():
    p = Profile.load(PROFILE)
    p.education.append(copy.deepcopy(p.education[0]))
    p.resume_files.append(copy.deepcopy(p.resume_files[0]))
    assert match(field("School"), p) is None
    assert match(field("Resume", "file"), p) is None


@pytest.mark.parametrize("url", ["https://employer.example/apply", "http://localhost:8080", "http://127.0.0.1.evil.test:80", "file:///etc/passwd", "http://user@127.0.0.1:8080"])
def test_external_targets_rejected(url):
    with pytest.raises(ValueError):
        local_origin(url)
