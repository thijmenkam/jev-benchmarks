from dataclasses import dataclass, field
from typing import Any


@dataclass
class QuestionResult:
    qid: str
    qtype: str
    prediction: str
    probabilities: dict
    confidence: float
    valid: bool
    raw: dict = field(default_factory=dict)

    def probability_of(self, label):
        return float(self.probabilities.get(str(label), 0.0))


@dataclass
class ModelResponse:
    model: str
    answers: dict
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    n_retries: int = 0
    malformed_retries: int = 0
    raw: Any = None


def normalize_answer(qid, qtype, raw):
    if qtype == "choice":
        probs = raw.get("probabilities", {})
        choice = raw.get("choice")
        probs = {str(k): float(v) for k, v in probs.items()}
        if not probs:
            return QuestionResult(qid, qtype, str(choice), {}, 0.0, False, dict(raw))
        ordered = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
        predicted = str(ordered[0][0])
        confidence = float(raw.get("confidence", ordered[0][1]))
        confidence = min(max(confidence, ordered[0][1]), 1.0)
        return QuestionResult(qid, qtype, str(choice) if choice is not None else predicted, probs, confidence, True, dict(raw))
    if qtype == "score":
        probs = {str(k): float(v) for k, v in raw.get("probabilities", {}).items()}
        if not probs:
            return QuestionResult(qid, qtype, "", {}, 0.0, False, dict(raw))
        predicted = max(probs.items(), key=lambda kv: kv[1])[0]
        confidence = float(raw.get("confidence", probs[predicted]))
        confidence = min(max(confidence, probs[predicted]), 1.0)
        return QuestionResult(qid, qtype, predicted, probs, confidence, True, dict(raw))
    if qtype == "noul":
        value = float(raw.get("noul", raw.get("value", 0.0)))
        probs = {"yes": max(0.0, min(1.0, value)), "no": max(0.0, min(1.0, 1.0 - value))}
        predicted = "yes" if value >= 0.5 else "no"
        return QuestionResult(qid, qtype, predicted, probs, max(probs["yes"], probs["no"]), True, dict(raw))
    return QuestionResult(qid, qtype, "", {}, 0.0, False, dict(raw))