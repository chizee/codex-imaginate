"""Pipeline state machine — tracks phase completion, supports resume."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class Phase(Enum):
    SCRIPT = "script"
    CHARACTER_REFS = "character_refs"
    SCENE_IMAGES = "scene_images"
    NARRATION = "narration"
    VIDEO = "video"
    EXPORT = "export"


PHASE_ORDER = [
    Phase.SCRIPT,
    Phase.CHARACTER_REFS,
    Phase.SCENE_IMAGES,
    Phase.NARRATION,
    Phase.VIDEO,
    Phase.EXPORT,
]


@dataclass
class PhaseRecord:
    phase: str  # Phase.value
    status: str = "pending"  # pending | running | done | failed
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> PhaseRecord:
        return cls(**d)


@dataclass
class PipelineState:
    """
    Persistable pipeline state.

    Saved as ``{output_dir}/{slug}/{slug}_pipeline.json`` after each phase
    so the pipeline can resume if interrupted.
    """

    slug: str
    prompt: str = ""
    age_group: str = "kids"
    output_dir: str = ""
    phases: dict[str, PhaseRecord] = field(default_factory=dict)

    def __post_init__(self):
        if not self.phases:
            self.phases = {p.value: PhaseRecord(p.value) for p in PHASE_ORDER}

    @property
    def current_phase(self) -> Optional[str]:
        """First phase that is not 'done'."""
        for p_name, rec in self.phases.items():
            if rec.status != "done":
                return p_name
        return None

    @property
    def all_done(self) -> bool:
        return all(r.status == "done" for r in self.phases.values())

    def mark_done(self, phase: Phase) -> None:
        self.phases[phase.value].status = "done"

    def mark_failed(self, phase: Phase, error: str) -> None:
        self.phases[phase.value].status = "failed"
        self.phases[phase.value].error = error

    def mark_running(self, phase: Phase) -> None:
        self.phases[phase.value].status = "running"

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "prompt": self.prompt,
            "age_group": self.age_group,
            "output_dir": self.output_dir,
            "phases": {k: v.to_dict() for k, v in self.phases.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> PipelineState:
        phases = {}
        for k, v in d.get("phases", {}).items():
            phases[k] = PhaseRecord.from_dict(v)
        return cls(
            slug=d["slug"],
            prompt=d.get("prompt", ""),
            age_group=d.get("age_group", "kids"),
            output_dir=d.get("output_dir", ""),
            phases=phases,
        )

    # ---- persistence ----

    def save(self, path: str) -> str:
        """Persist to ``{path}/{slug}_pipeline.json``."""
        os.makedirs(path, exist_ok=True)
        filepath = os.path.join(path, f"{self.slug}_pipeline.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return filepath

    @classmethod
    def load(cls, slug: str, path: str) -> Optional[PipelineState]:
        """Load from ``{path}/{slug}_pipeline.json``."""
        filepath = os.path.join(path, f"{slug}_pipeline.json")
        if not os.path.exists(filepath):
            return None
        with open(filepath, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
