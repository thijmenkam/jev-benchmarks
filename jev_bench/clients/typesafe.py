import time

import requests

from .. import config
from ..answer_types import ModelResponse, normalize_answer


class TypeSafeClient:
    provider = "typesafe"
    model = "jev"

    def __init__(self, model=None, base_url=None, api_key=None, timeout=None, max_retries=None):
        self.model = model or config.TYPESAFE_MODEL
        self.base_url = base_url or config.TYPESAFE_BASE_URL
        self.api_key = api_key or config.TYPESAFE_API_KEY
        self.timeout = timeout or config.HTTP_TIMEOUT_SECONDS
        self.max_retries = max_retries or config.MAX_RETRIES

    @property
    def display_name(self):
        return f"jev ({self.model})"

    def timed_evaluate(self, state, questions, label=None, call_seed=0):
        start = time.perf_counter()
        response = self.evaluate(state, questions)
        response.latency_ms = (time.perf_counter() - start) * 1000.0
        return response

    def evaluate(self, state, questions, label=None, call_seed=0):
        if not self.api_key:
            raise RuntimeError("TYPESAFE_API_KEY is not set; run in mock mode or export the key")
        payload = {"state": state, "model": self.model, "questions": questions}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        total_retries = 0
        malformed = 0
        last_error = None
        for attempt in range(self.max_retries + 1):
            if attempt:
                total_retries += 1
                time.sleep(min(2 ** attempt, 8))
            try:
                resp = requests.post(self.base_url, json=payload, headers=headers, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
                continue
            if resp.status_code in (429, 529, 502, 503, 504):
                last_error = RuntimeError(f"HTTP {resp.status_code}")
                continue
            if resp.status_code >= 400:
                raise RuntimeError(f"TypeSafe API error {resp.status_code}: {resp.text[:500]}")
            data = resp.json()
            break
        else:
            raise RuntimeError(f"TypeSafe request failed after retries: {last_error}")
        answers = data.get("answers", data)
        normalized = {}
        for qid, qdef in questions.items():
            raw = answers.get(qid)
            if raw is None:
                raw = {"type": qdef["type"]}
                malformed += 1
            result = normalize_answer(qid, qdef["type"], raw)
            normalized[qid] = result
        usage = data.get("usage", {}) or {}
        input_tokens = int(usage.get("input_tokens", 0) or 0)
        output_tokens = int(usage.get("output_tokens", 0) or 0)
        cost = input_tokens * config.TYPESAFE_PRICE_IN_MT / 1e6 + output_tokens * config.TYPESAFE_PRICE_OUT_MT / 1e6
        return ModelResponse(
            model=self.display_name,
            answers=normalized,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            n_retries=total_retries,
            malformed_retries=malformed,
            raw=data,
        )