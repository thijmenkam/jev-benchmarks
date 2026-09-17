import json
import time

import requests

from .. import config
from ..answer_types import ModelResponse, normalize_answer

APPROX_PRICE_USD_PER_MT = {
    "openai/gpt-5-mini": (1.25, 10.0),
    "openai/gpt-5": (1.25, 10.0),
    "openai/gpt-5-pro": (2.0, 12.0),
    "anthropic/claude-sonnet-4.5": (3.0, 15.0),
    "anthropic/claude-opus-4.1": (15.0, 75.0),
    "google/gemini-2.5-pro": (1.25, 10.0),
}

N_OPTION_MARKER = "__n__"


def _price_for(model):
    exact = config.PRICE_PER_MT_IN_USD > 0 or config.PRICE_PER_MT_OUT_USD > 0
    if exact:
        return config.PRICE_PER_MT_IN_USD, config.PRICE_PER_MT_OUT_USD
    short = model.rsplit("/", 1)[-1] if model else ""
    for key, price in APPROX_PRICE_USD_PER_MT.items():
        key_short = key.rsplit("/", 1)[-1]
        if model == key or short == key_short:
            return price
    return config.DEFAULT_PRICE_IN_MT, config.DEFAULT_PRICE_OUT_MT


def build_system_prompt():
    return (
        "You are an automated decision engine. You receive a state (text or JSON) and a set of typed "
        "questions. Answer every question about the state in a single JSON response with the exact "
        "schema you are given. Do not add commentary. "
        "Question types:\n"
        "- choice: pick exactly one option; return it under \"choice\", a probability for EVERY option "
        "under \"probabilities\" (must sum to 1), and \"confidence\" (0..1, how peaked your belief is).\n"
        "- score: the levels are an ordered rubric (index 0 is the lowest). Return \"score\" (the "
        "probability-weighted position on the level scale, may be fractional), \"probabilities\" for every "
        "level index as a string key (must sum to 1), \"legend\" mapping each index to its description, "
        "and \"confidence\" (0..1).\n"
        "- noul: return \"noul\", a single number from 0 to 1 representing the probability that the "
        "statement is true (1 = definitely yes, 0 = definitely no, 0.5 = exactly uncertain).\n"
        "Return a JSON object shaped as: {\"answers\": {<question id>: <typed answer>}}."
    )


def build_schema(questions):
    properties = {}
    for qid, qdef in questions.items():
        qtype = qdef["type"]
        if qtype == "choice":
            options = list(qdef.get("criteria", {}).keys())
            answer = {
                "type": "object",
                "properties": {
                    "type": {"const": "choice"},
                    "choice": {"enum": options},
                    "probabilities": {
                        "type": "object",
                        "propertyNames": {"enum": options},
                        "additionalProperties": {"type": "number"},
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["choice", "probabilities", "confidence"],
                "additionalProperties": False,
            }
        elif qtype == "score":
            levels = qdef.get("criteria", [])
            level_keys = [str(i) for i in range(len(levels))]
            answer = {
                "type": "object",
                "properties": {
                    "type": {"const": "score"},
                    "score": {"type": "number", "minimum": 0},
                    "probabilities": {
                        "type": "object",
                        "propertyNames": {"enum": level_keys},
                        "additionalProperties": {"type": "number"},
                    },
                    "legend": {
                        "type": "object",
                        "propertyNames": {"enum": level_keys},
                        "additionalProperties": {"type": "string"},
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["score", "probabilities", "legend", "confidence"],
                "additionalProperties": False,
            }
        else:
            answer = {
                "type": "object",
                "properties": {
                    "type": {"const": "noul"},
                    "noul": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["noul"],
                "additionalProperties": False,
            }
        properties[qid] = answer
    return {
        "type": "object",
        "properties": {
            "answers": {
                "type": "object",
                "properties": properties,
                "required": list(questions.keys()),
                "additionalProperties": False,
            }
        },
        "required": ["answers"],
        "additionalProperties": False,
    }


class LLMAdapterClient:
    provider = "openrouter"

    def __init__(
        self,
        model,
        base_url=None,
        api_key=None,
        structured_outputs=True,
        llm_answer_mode="probabilities",
        normalize_probabilities=True,
        n_retry_malformed_structure=1,
        max_retries=None,
        timeout=None,
    ):
        self.model = model
        self.base_url = (base_url or config.LLM_BASE_URL).rstrip("/")
        self.api_key = api_key or config.OPENROUTER_API_KEY or config.OPENAI_API_KEY
        self.structured_outputs = structured_outputs
        self.llm_answer_mode = llm_answer_mode
        self.normalize_probabilities = normalize_probabilities
        self.n_retry_malformed_structure = n_retry_malformed_structure
        self.max_retries = max_retries or config.MAX_RETRIES
        self.timeout = timeout or config.HTTP_TIMEOUT_SECONDS

    @property
    def display_name(self):
        return self.model

    def timed_evaluate(self, state, questions, label=None, call_seed=0):
        start = time.perf_counter()
        response = self.evaluate(state, questions)
        response.latency_ms = (time.perf_counter() - start) * 1000.0
        return response

    def evaluate(self, state, questions, label=None, call_seed=0):
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY / OPENAI_API_KEY is not set; run in mock mode or export the key")
        schema = build_schema(questions)
        system = build_system_prompt()
        state_json = state if isinstance(state, str) else json.dumps(state)
        encoded_questions = []
        for qid, qdef in questions.items():
            criteria = qdef.get("criteria")
            if isinstance(criteria, dict):
                criteria = {str(k): v for k, v in criteria.items()}
            elif isinstance(criteria, list):
                criteria = [str(v) for v in criteria]
            encoded_questions.append({
                "id": qid,
                "type": qdef["type"],
                "instructions": qdef.get("instructions", ""),
                "criteria": criteria,
            })
        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": json.dumps({"state": state_json, "questions": encoded_questions}),
            },
        ]
        total_retries = 0
        malformed = 0
        input_tokens = 0
        output_tokens = 0
        last_data = None
        for attempt in range(self.max_retries + 1 + self.n_retry_malformed_structure):
            if attempt:
                total_retries += 1
            response_format = None
            if self.structured_outputs:
                response_format = {
                    "type": "json_schema",
                    "json_schema": {"name": "system_one_answers", "schema": schema, "strict": True},
                }
            else:
                response_format = {"type": "json_object"}
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.0,
                "response_format": response_format,
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            if self.model.startswith(("o1", "o3", "o4", "gpt-5")):
                payload.pop("temperature", None)
            resp = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers, timeout=self.timeout)
            if resp.status_code >= 400:
                if resp.status_code in (429, 502, 503, 504) and attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise RuntimeError(f"LLM API error {resp.status_code}: {resp.text[:500]}")
            data = resp.json()
            usage = data.get("usage") or {}
            input_tokens += int(usage.get("prompt_tokens", 0) or 0)
            output_tokens += int(usage.get("completion_tokens", 0) or 0)
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed, error = self._parse(content, questions)
            if parsed is not None:
                last_data = data
                break
            malformed += 1
            if malformed > self.n_retry_malformed_structure:
                last_data = data
                break
            messages.append({"role": "assistant", "content": content or "{}"})
            messages.append({
                "role": "user",
                "content": f"The previous response was not schema-valid ({error}). Return only the JSON in the exact requested schema.",
            })
        else:
            raise RuntimeError("LLM request failed after retries")
        parsed = self._parse(last_data.get("choices", [{}])[0].get("message", {}).get("content", ""), questions)[0]
        if parsed is None:
            raise RuntimeError("LLM output did not validate after corrective retries")
        price_in, price_out = _price_for(self.model)
        cost = input_tokens * price_in / 1e6 + output_tokens * price_out / 1e6
        return ModelResponse(
            model=self.display_name,
            answers=parsed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            n_retries=total_retries,
            malformed_retries=malformed,
            raw=last_data,
        )

    def _parse(self, content, questions):
        if not content:
            return None, "empty response"
        try:
            data = json.loads(content)
        except ValueError:
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None, "not valid JSON"
            try:
                data = json.loads(content[start : end + 1])
            except ValueError:
                return None, "not valid JSON"
        answers = data.get("answers")
        if not isinstance(answers, dict):
            return None, "missing answers object"
        normalized = {}
        for qid, qdef in questions.items():
            raw = answers.get(qid)
            if not isinstance(raw, dict):
                return None, f"question {qid}: missing answer"
            raw = dict(raw)
            raw["type"] = qdef["type"]
            raw = self._normalize_raw(raw, qdef)
            try:
                result = normalize_answer(qid, qdef["type"], raw)
            except (TypeError, ValueError):
                return None, f"question {qid}: unparseable answer"
            if not result.valid:
                return None, f"question {qid}: invalid answer"
            normalized[qid] = result
        return normalized, None

    def _normalize_raw(self, raw, qdef):
        qtype = qdef["type"]
        if qtype == "choice":
            probs = raw.get("probabilities")
            if isinstance(probs, dict):
                raw["probabilities"] = self._fix_probs(probs)
        elif qtype == "score":
            probs = raw.get("probabilities")
            if isinstance(probs, dict):
                raw["probabilities"] = self._fix_probs(probs)
        return raw

    def _fix_probs(self, probs):
        fixed = {}
        total = 0.0
        for k, v in probs.items():
            try:
                value = float(v)
            except (TypeError, ValueError):
                value = 0.0
            value = max(0.0, value)
            fixed[str(k)] = value
            total += value
        if self.normalize_probabilities and total > 0:
            fixed = {k: v / total for k, v in fixed.items()}
        return fixed