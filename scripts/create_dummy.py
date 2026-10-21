"""Rebuild synthetic profile, its JSON Schema, and the text resume fixture."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from auto_apply.profile import Profile  # noqa: E402

directory = ROOT / "profiles"
directory.mkdir(exist_ok=True)
resume = directory / "dummy-resume.txt"
resume.write_text("SYNTHETIC CANDIDATE - NOT A REAL PERSON\nAlex Example\nalex@example.test\nSoftware Engineer at Example Widgets (2022-01 to 2025-12).\nBSc Computer Science, Example University, 2022.\nSkills: Python, SQL, Playwright.\n", encoding="utf-8")
data = {
    "schema_version": 1, "candidate_id": "synthetic-alex", "synthetic": True,
    "personal": {"full_name": "Alex Example", "email": "alex@example.test", "phone": "+1-202-555-0148", "city": "Example City"},
    "education": [{"school": "Example University", "degree": "BSc", "field": "Computer Science", "graduation_year": 2022}],
    "work_experience": [{"employer": "Example Widgets", "title": "Software Engineer", "start_date": "2022-01", "end_date": "2025-12", "description": "Built synthetic test services."}],
    "skills": ["Python", "SQL", "Playwright"],
    "resume_files": [{"path": resume.name, "sha256": hashlib.sha256(resume.read_bytes()).hexdigest()}],
    "verified_answers": [{"question": "Are you authorized to work in the United States?", "value": "Yes", "verified": True, "verified_at": "2026-10-20", "source": "Synthetic fixture author"}]
}
Profile.model_validate(data)
(directory / "dummy.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
(directory / "profile.schema.json").write_text(json.dumps(Profile.model_json_schema(), indent=2), encoding="utf-8")
