from __future__ import annotations

from fastapi import FastAPI

from cms_platform.api.routes import benchmarks, beneficiary, cohorts
from cms_platform.common.config import get_settings
from cms_platform.common.logging import configure_logging

app = FastAPI(title="CMS Claims Platform", version="0.1.0")

app.include_router(cohorts.router)
app.include_router(beneficiary.router)
app.include_router(benchmarks.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run("cms_platform.api.main:app", host="0.0.0.0", port=8000, reload=True)
