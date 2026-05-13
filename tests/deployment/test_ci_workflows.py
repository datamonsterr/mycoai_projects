import yaml
from pathlib import Path

MONOREPO = Path(__file__).resolve().parents[2]


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.load(f, Loader=yaml.BaseLoader)


def test_ci_workflow_exists() -> None:
    path = MONOREPO / ".github/workflows/ci.yml"
    assert path.exists(), "Missing CI workflow"


def test_ci_workflow_parses() -> None:
    path = MONOREPO / ".github/workflows/ci.yml"
    config = _load_yaml(path)

    assert config["name"] == "CI"
    jobs = config["jobs"]
    assert "backend" in jobs
    assert "frontend" in jobs
    assert "docker-dry-run" in jobs

    backend_steps = [s.get("run", "") for s in jobs["backend"]["steps"]]
    assert any("ruff check" in s for s in backend_steps)
    assert any("pytest" in s for s in backend_steps)
    assert any("mypy src" in s for s in backend_steps)

    frontend_steps = [s.get("run", "") for s in jobs["frontend"]["steps"]]
    assert any("pnpm lint" in s for s in frontend_steps)
    assert any("pnpm build" in s for s in frontend_steps)
    assert any("pnpm typecheck" in s for s in frontend_steps)


def test_cd_workflow_exists() -> None:
    path = MONOREPO / ".github/workflows/cd.yml"
    assert path.exists(), "Missing CD workflow"


def test_cd_workflow_parses() -> None:
    path = MONOREPO / ".github/workflows/cd.yml"
    config = _load_yaml(path)

    assert config["name"] == "CD"
    assert config["on"] == {"workflow_dispatch": ""}

    deploy = config["jobs"]["deploy"]
    assert deploy["environment"] == "production"


def test_ci_triggers_on_pr_and_main_push() -> None:
    config = _load_yaml(MONOREPO / ".github/workflows/ci.yml")

    triggers = config["on"]
    assert "push" in triggers
    assert "pull_request" in triggers
    assert triggers["push"]["branches"] == ["main"]
