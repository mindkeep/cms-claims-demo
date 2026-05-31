from pathlib import Path


def test_dockerfile_exists() -> None:
    assert (Path(__file__).parent.parent / "Dockerfile").exists()


def test_ci_yml_has_three_jobs() -> None:
    ci_path = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"
    content = ci_path.read_text()
    assert "quality:" in content
    assert "test:" in content
    assert "docker:" in content
    assert "mypy" in content
    assert "pytest" in content


def test_ci_yml_parseable() -> None:
    import yaml

    ci_path = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"
    assert ci_path.exists()
    data = yaml.safe_load(ci_path.read_text())
    assert "jobs" in data
    assert "quality" in data["jobs"]
    assert "test" in data["jobs"]
    assert "docker" in data["jobs"]


def test_docker_compose_has_healthcheck() -> None:
    dc_path = Path(__file__).parent.parent / "docker-compose.yml"
    content = dc_path.read_text()
    assert "healthcheck:" in content
    assert "ollama" in content
    assert "restart: unless-stopped" in content


def test_docker_compose_parseable() -> None:
    import yaml

    dc_path = Path(__file__).parent.parent / "docker-compose.yml"
    assert dc_path.exists()
    data = yaml.safe_load(dc_path.read_text())
    assert "services" in data
    assert "api" in data["services"]
    assert "ollama" in data["services"]
    assert "healthcheck" in data["services"]["api"]
    assert "volumes" in data
    assert "ollama_data" in data["volumes"]
