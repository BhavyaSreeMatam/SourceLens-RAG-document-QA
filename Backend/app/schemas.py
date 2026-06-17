from pydantic import BaseModel
from typing import List


class AskRequest(BaseModel):
    question: str
    top_k: int = 5


class EvaluateRequest(BaseModel):
    question: str
    answer: str
    contexts: List[str]