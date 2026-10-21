import re
from .profile import Profile

DISCOVER = """() => [...document.querySelectorAll('input,select,textarea')]
 .filter(e => !['submit','button','hidden','reset'].includes(e.type) && !e.disabled &&
              e.getClientRects().length && e.id)
 .map(e => ({id:e.id, name:e.name, type:e.type, tag:e.tagName.toLowerCase(),
 label:[...(e.labels||[])].map(l=>{const c=l.cloneNode(true);
 c.querySelectorAll('input,select,textarea,button').forEach(n=>n.remove());return c.textContent.trim()}).join(' ') || e.getAttribute('aria-label') || '',
 required:e.required, options:e.options?[...e.options].map(o=>({label:o.label,value:o.value})):[]}))"""


def normalize(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


ALIASES = {
    "full name": "personal.full_name", "name": "personal.full_name",
    "email": "personal.email", "email address": "personal.email",
    "phone": "personal.phone", "phone number": "personal.phone",
    "city": "personal.city", "linkedin": "personal.linkedin",
    "skills": "skills",
}


def match(field: dict, profile: Profile):
    question = normalize(field["label"])
    if field["type"] == "file":
        return "resume_files.0" if question in {"resume", "upload resume"} and len(profile.resume_files) == 1 else None
    paths = set()
    path = ALIASES.get(question)
    if path and path in profile.facts():
        paths.add(path)
    for section, aliases in (("education", {"school":"school", "degree":"degree", "field of study":"field"}),
                             ("work_experience", {"most recent employer":"employer", "most recent job title":"title"})):
        entries = getattr(profile, section)
        # Multiple entries require a human decision; never guess "most recent".
        if len(entries) == 1 and question in aliases:
            paths.add(f"{section}.0.{aliases[question]}")
    for i, answer in enumerate(profile.verified_answers):
        if normalize(answer.question) == question and f"verified_answers.{i}" in profile.facts():
            paths.add(f"verified_answers.{i}")
    return next(iter(paths)) if len(paths) == 1 else None
