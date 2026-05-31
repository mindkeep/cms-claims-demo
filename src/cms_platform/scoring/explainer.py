from dataclasses import dataclass

from openai import OpenAI

from cms_platform.common.config import Settings


@dataclass
class CareGapExplanation:
    patient_id: str
    gaps: list[str]
    summary: str
    model_used: str


def _stub_explanation(patient_id: str, gaps: list[str]) -> CareGapExplanation:
    if not gaps:
        summary = "No open care gaps identified for this patient."
    else:
        listed = ", ".join(gaps[:3])
        tail = f" (and {len(gaps) - 3} more)" if len(gaps) > 3 else ""
        summary = (
            f"Patient has {len(gaps)} open care gap(s): {listed}{tail}. "
            "Clinical review recommended."
        )
    return CareGapExplanation(patient_id=patient_id, gaps=gaps, summary=summary, model_used="stub")


def _build_prompt(patient_id: str, gaps: list[str]) -> str:
    if not gaps:
        return f"Patient {patient_id} has no open care gaps. Confirm in one sentence."
    gap_list = "\n".join(f"- {g}" for g in gaps)
    return (
        f"You are a clinical care coordinator. Patient {patient_id} has "
        f"{len(gaps)} open care gap(s):\n{gap_list}\n\n"
        "Write 2-3 sentences summarising these gaps and recommending next steps. "
        "Be concise and clinical. Do not add invented medical details."
    )


def explain_care_gaps(
    patient_id: str,
    gaps: list[str],
    settings: Settings,
) -> CareGapExplanation:
    """Compose a natural-language care-gap summary via Ollama.

    Falls back to a deterministic stub when Ollama is unreachable — the demo
    runs fully offline without any LLM infrastructure.
    TODO(future-llm): add retry with exponential backoff for transient failures.
    """
    try:
        client = OpenAI(base_url=settings.ollama_base_url, api_key="ollama")
        response = client.chat.completions.create(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": _build_prompt(patient_id, gaps)}],
            timeout=30,
        )
        content = response.choices[0].message.content or ""
        return CareGapExplanation(
            patient_id=patient_id, gaps=gaps, summary=content, model_used=settings.ollama_model
        )
    except Exception:
        return _stub_explanation(patient_id, gaps)
