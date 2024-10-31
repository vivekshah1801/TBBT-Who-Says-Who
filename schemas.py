from dataclasses import dataclass
from typing import Optional


@dataclass
class Transcript:
    season: int
    episode: int
    title: int
    link: str
    html_text: str = ""
    raw_text: str = ""


@dataclass
class Dialogue:
    speaker: str
    text: str
    transcript: Optional[Transcript]
    speaker_supporting_text: Optional[str] = ""


@dataclass
class Scene:
    description: str
    transcript: Optional[Transcript]