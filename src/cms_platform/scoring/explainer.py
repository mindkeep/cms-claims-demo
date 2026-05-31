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


def _build_prompt(beneficiary_id: str, gaps: list[str]) -> str:
    if not gaps:
        return (
            f"Beneficiary {beneficiary_id} has no open care gaps. "
            "Write one sentence confirming they are up to date."
        )
    gap_list = "\n".join(f"- {g}" for g in gaps)
    return (
        f"You are a clinical care coordinator assistant. Beneficiary {beneficiary_id} "
        f"has {len(gaps)} open care gap(s):\n{gap_list}\n\n"
        "Write 2-3 sentences summarizing these gaps and recommending next steps. "
        "Be concise and clinical. Do not add invented medical details."
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
    """
    try:
        _client = OpenAI(base_url=settings.ollama_base_url, api_key="ollama")
        response = _client.chat.completions.create(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": _build_prompt(beneficiary_id, gaps)}],
            timeout=30,
        )
        content = response.choices[0].message.content or ""
        return CareGapExplanation(
            beneficiary_id=beneficiary_id,
            gaps=gaps,
            summary=content,
            model_used=settings.ollama_model,
        )
    except Exception:
        return _stub_explanation(beneficiary_id, gaps)
