from pathlib import Path
from typing import Literal
import json
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Personal(StrictModel):
    full_name: str
    email: str
    phone: str | None = None
    city: str | None = None
    linkedin: str | None = None


class Education(StrictModel):
    school: str
    degree: str
    field: str
    graduation_year: int


class Experience(StrictModel):
    employer: str
    title: str
    start_date: str
    end_date: str | None = None
    description: str


class Resume(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Answer(StrictModel):
    question: str
    value: str
    verified: bool
    verified_at: str | None = None
    source: str


class Profile(StrictModel):
    schema_version: Literal[1] = 1
    candidate_id: str
    synthetic: bool = True
    personal: Personal
    education: list[Education]
    work_experience: list[Experience]
    skills: list[str]
    resume_files: list[Resume]
    verified_answers: list[Answer]

    @classmethod
    def load(cls, path: Path):
        return cls.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def facts(self) -> dict[str, str]:
        """No inferred summaries, dates, eligibility, or demographic answers."""
        facts = {f"personal.{k}": v for k, v in self.personal.model_dump().items() if v}
        for section in ("education", "work_experience"):
            for i, entry in enumerate(getattr(self, section)):
                for k, v in entry.model_dump().items():
                    if v is not None:
                        facts[f"{section}.{i}.{k}"] = str(v)
        if self.skills:
            facts["skills"] = ", ".join(self.skills)
        for i, answer in enumerate(self.verified_answers):
            if answer.verified and answer.verified_at and answer.value:
                facts[f"verified_answers.{i}"] = answer.value
        return facts
