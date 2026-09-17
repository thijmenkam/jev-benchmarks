import hashlib
import math
import random
import time

from ..answer_types import ModelResponse, QuestionResult, normalize_answer
from ..tasks import label_to_reference


class MockModelClient:
    provider = "mock"

    def __init__(self, name, accuracy, median_latency_ms, temperature, malformed_rate=0.0, token_scale=1.0, seed=0):
        self.name = name
        self.accuracy = accuracy
        self.median_latency_ms = median_latency_ms
        self.temperature = temperature
        self.malformed_rate = malformed_rate
        self.token_scale = token_scale
        self.seed = seed

    @property
    def display_name(self):
        return self.name

    def timed_evaluate(self, state, questions, label=None, call_seed=0):
        start = time.perf_counter()
        response = self.evaluate(state, questions, label=label, call_seed=call_seed)
        response.latency_ms = (time.perf_counter() - start) * 1000.0
        return response

    def _rng(self, state_text, question_id, call_seed):
        h = hashlib.sha256(f"{self.seed}|{self.name}|{state_text}|{question_id}|{call_seed}".encode()).hexdigest()
        return random.Random(int(h[:12], 16))

    def evaluate(self, state, questions, label=None, call_seed=0):
        state_text = state if isinstance(state, str) else irepr(state)
        rng = random.Random(f"{self.seed}|{self.name}|{state_text}|{call_seed}")
        answers = {}
        malformed = 0
        for qid, qdef in questions.items():
            qtype = qdef["type"]
            if rng.random() < self.malformed_rate:
                malformed += 1
            raw = self._answer(qid, qtype, qdef, label, state_text, call_seed)
            result = normalize_answer(qid, qtype, raw)
            answers[qid] = result
        latency = random.lognormvariate(math.log(self.median_latency_ms), 0.35)
        state_len = len(state_text)
        input_tokens = int(120 + state_len / 4 * self.token_scale)
        output_tokens = int(220 * self.token_scale)
        price_in, price_out = self._prices()
        cost = input_tokens * price_in / 1e6 + output_tokens * price_out / 1e6
        return ModelResponse(
            model=self.display_name,
            answers=answers,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            n_retries=malformed,
            malformed_retries=malformed,
            raw={"mock": True, "latency_ms": latency},
        )

    def _prices(self):
        if "jev" in self.name or self.provider == "typesafe":
            return 0.042, 0.0

        from .llm_adapter import _price_for

        return _price_for(self.name.replace("-mock", ""))

    def _answer(self, qid, qtype, qdef, label, state_text, call_seed):
        rng = self._rng(state_text, qid, call_seed)
        if qtype == "choice":
            options = list(qdef.get("criteria", {}).keys())
            if not options:
                options = ["other"]
            correct = None
            if label and qid in label:
                correct = label_to_reference(qtype, label[qid])
            if correct in options:
                chosen = correct if rng.random() < self.accuracy else rng.choice([o for o in options if o != correct])
            else:
                chosen = rng.choice(options)
            peak = self._peak(rng)
            probs = self._spread(options, chosen, peak, rng)
            return {
                "type": "choice",
                "choice": chosen,
                "probabilities": probs,
                "confidence": probs[chosen],
            }
        if qtype == "score":
            levels = list(qdef.get("criteria", []))
            n = len(levels)
            correct = None
            if label and qid in label:
                correct = str(int(label[qid]))
            chosen = None
            if correct is not None and 0 <= int(correct) < n:
                chosen = correct if rng.random() < self.accuracy else str(rng.choice([i for i in range(n) if str(i) != correct]))
            else:
                chosen = str(rng.randrange(n))
            probs = {}
            peak = self._peak(rng)
            chosen_idx = int(chosen)
            for i in range(n):
                dist = abs(i - chosen_idx)
                probs[str(i)] = peak * (0.5 ** dist)
            total = sum(probs.values())
            probs = {k: v / total for k, v in probs.items()}
            score = sum(i * probs[str(i)] for i in range(n))
            legend = {str(i): str(levels[i]) for i in range(n)}
            return {
                "type": "score",
                "score": round(score, 3),
                "legend": legend,
                "probabilities": probs,
                "confidence": probs[str(chosen_idx)],
            }
        if qtype == "noul":
            truth = bool(label[qid]) if label and qid in label else bool(rng.random() < 0.5)
            base = 0.5 + self.accuracy / 2 - 0.0
            p_yes = base if truth else 1.0 - base
            jitter = (rng.random() - 0.5) * 0.06 * self.temperature
            p_yes = min(0.985, max(0.015, p_yes + jitter))
            return {"type": "noul", "noul": round(p_yes, 4)}
        return {"type": qtype}

    def _peak(self, rng):
        base = 0.75 + 0.12 * (self.accuracy - 0.8) * 2
        return min(0.99, max(0.55, base + (rng.random() - 0.5) * 0.2 * self.temperature))

    def _spread(self, options, chosen, peak, rng):
        others = [o for o in options if o != chosen]
        probs = {chosen: peak}
        if others:
            weights = [rng.random() * (1.0 - peak) for _ in others]
            total = sum(weights) or 1.0
            for option, weight in zip(others, weights):
                probs[option] = (1.0 - peak) * weight / total
        return {k: round(float(v), 4) for k, v in probs.items()}


def irepr(obj):
    import json

    try:
        return json.dumps(obj, sort_keys=True)
    except TypeError:
        return repr(obj)