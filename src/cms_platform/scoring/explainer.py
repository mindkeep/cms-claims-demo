from dataclasses import dataclass

from openai import OpenAI

from cms_platform.common.config import Settings


@dataclass
class CareGapExplanation:
    beneficiary_id: str
    gaps: list[str]
    summary: str
    model_used: str


def _stub_explanation(beneficiary_id: str, gaps: list[str]) -> CareGapExplanation:
    if not gaps:
        summary = "No open care gaps identified for this beneficiary."
    else:
        listed = ", ".join(gaps[:3])
        tail = f" (and {len(gaps) - 3} more)" if len(gaps) > 3 else ""
        summary = (
            f"Beneficiary has {len(gaps)} open care gap(s): {listed}{tail}. "
            "Clinical review recommended."
        )
    return CareGapExplanation(
        beneficiary_id=beneficiary_id,
        gaps=gaps,
        summary=summary,
        model_used="stub",
    )


def explain_care_gaps(
    beneficiary_id: str,
    gaps: list[str],
    settings: Settings,
) -> CareGapExplanation:
    """Compose a natural-language care-gap summary via Ollama.

    Uses the OpenAI-compatible API at settings.ollama_base_url.
    Falls back to a deterministic stub if Ollama is unreachable — the demo
    runs fully offline without any LLM infrastructure.

    WP4 replaces the NotImplementedError with the actual LLM call.
    """
    try:
        _client = OpenAI(base_url=settings.ollama_base_url, api_key="ollama")
        # WP4: build prompt and replace this error with:
        # response = _client.chat.completions.create(
        #     model=settings.ollama_model,
        #     messages=[{"role": "user", "content": _build_prompt(beneficiary_id, gaps)}],
        # )
        # return CareGapExplanation(
        #     beneficiary_id=beneficiary_id,
        #     gaps=gaps,
        #     summary=response.choices[0].message.content or "",
        #     model_used=settings.ollama_model,
        # )
        raise NotImplementedError("WP4")
    except NotImplementedError:
        return _stub_explanation(beneficiary_id, gaps)
    except Exception:
        return _stub_explanation(beneficiary_id, gaps)
