import json
import os
import platform

TYPESAFE_API_KEY = os.environ.get("TYPESAFE_API_KEY", "") or os.environ.get("JEV_API_KEY", "")
TYPESAFE_BASE_URL = os.environ.get("TYPESAFE_BASE_URL", "https://api.typesafe.ai/v1/systemone")
TYPESAFE_MODEL = os.environ.get("TYPESAFE_MODEL", "jev-latest")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_MODELS = [
    m.strip()
    for m in os.environ.get("LLM_MODELS", "openai/gpt-5-mini anthropic/claude-sonnet-4.5").split()
    if m.strip()
]
LLM_USER_AGENT = os.environ.get("LLM_USER_AGENT", "jev-benchmarks/0.1")
LLM_EXTRA_HEADERS = json.loads(os.environ.get("LLM_EXTRA_HEADERS", "{}"))
LLM_STRUCTURED_OUTPUTS = os.environ.get("LLM_STRUCTURED_OUTPUTS", "json_schema").strip().lower()
LLM_RESPONSES_MODELS = [
    m.strip()
    for m in os.environ.get("LLM_RESPONSES_MODELS", "gpt-5.6-luna grok-4.6").split()
    if m.strip()
]

PRICE_PER_MT_IN_USD = float(os.environ.get("PRICE_PER_MT_IN_USD", "0.0"))
PRICE_PER_MT_OUT_USD = float(os.environ.get("PRICE_PER_MT_OUT_USD", "0.0"))

TYPESAFE_PRICE_IN_MT = 0.042
TYPESAFE_PRICE_OUT_MT = 0.0

DEFAULT_PRICE_IN_MT = 1.25
DEFAULT_PRICE_OUT_MT = 10.0

HTTP_TIMEOUT_SECONDS = float(os.environ.get("HTTP_TIMEOUT_SECONDS", "60"))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))


def has_jev_key():
    return bool(TYPESAFE_API_KEY)


def has_llm_key():
    return bool(OPENROUTER_API_KEY or OPENAI_API_KEY)


def platform_tag():
    return platform.platform()