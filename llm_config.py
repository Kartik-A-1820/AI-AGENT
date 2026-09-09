import os

import dotenv
from langchain_openai import ChatOpenAI


dotenv.load_dotenv()

OMNIROUTE_BASE_URL = os.getenv("OMNIROUTE_BASE_URL", "http://localhost:20128/v1")
OMNIROUTE_MODEL = os.getenv("OMNIROUTE_MODEL", "auto")
OMNIROUTE_API_KEY = os.getenv("OMNIROUTE_API_KEY") or os.getenv("OPENAI_API_KEY") or "omniroute-local"
LLM_TEMPERATURE = float(os.getenv("AI_AGENT_TEMPERATURE", "0.2"))
LLM_TIMEOUT = int(os.getenv("AI_AGENT_TIMEOUT", "120"))


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} not set in .env")
    return value


def create_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=OMNIROUTE_MODEL,
        base_url=OMNIROUTE_BASE_URL,
        api_key=OMNIROUTE_API_KEY,
        temperature=LLM_TEMPERATURE,
        timeout=LLM_TIMEOUT,
    )


def estimate_llm_cost(prompt_tokens: int, completion_tokens: int) -> float:
    input_cost = float(os.getenv("OMNIROUTE_INPUT_COST_PER_MILLION", "0"))
    output_cost = float(os.getenv("OMNIROUTE_OUTPUT_COST_PER_MILLION", "0"))

    prompt_cost = (prompt_tokens / 1_000_000) * input_cost
    completion_cost = (completion_tokens / 1_000_000) * output_cost

    return prompt_cost + completion_cost
