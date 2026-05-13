import yaml
from pathlib import Path

MONOREPO = Path(__file__).resolve().parents[2]


def test_docker_compose_dev_parses() -> None:
    path = MONOREPO / "docker-compose.dev.yml"
    assert path.exists(), f"Missing {path.name}"

    with open(path) as f:
        config = yaml.safe_load(f)

    services = config["services"]
    assert "postgres" in services
    assert "qdrant" in services
    assert "redis" in services

    # Dev: no backend/frontend — they run natively
    assert "backend" not in services
    assert "frontend" not in services
    assert "celery-worker" not in services


def test_docker_compose_prod_parses() -> None:
    path = MONOREPO / "docker-compose.yml"
    assert path.exists(), f"Missing {path.name}"

    with open(path) as f:
        config = yaml.safe_load(f)

    services = config["services"]
    assert "postgres" in services
    assert "qdrant" in services
    assert "redis" in services
    assert "backend" in services
    assert "frontend" in services
    assert "celery-worker" in services

    backend = services["backend"]
    assert "build" in backend, "backend must define build context"
    frontend = services["frontend"]
    assert "build" in frontend, "frontend must define build context"


def test_prod_backend_depends_on_healthy_deps() -> None:
    with open(MONOREPO / "docker-compose.yml") as f:
        config = yaml.safe_load(f)

    deps = config["services"]["backend"].get("depends_on", {})
    for dep in ["postgres", "qdrant", "redis"]:
        assert dep in deps
        assert deps[dep]["condition"] == "service_healthy"


def test_prod_no_exposed_db_ports() -> None:
    """Security: PostgreSQL, Qdrant, Redis must not expose ports to host."""
    with open(MONOREPO / "docker-compose.yml") as f:
        config = yaml.safe_load(f)

    for name in ["postgres", "qdrant", "redis"]:
        svc = config["services"][name]
        assert "ports" not in svc, f"{name} must not expose ports in production"


def test_env_example_has_required_vars() -> None:
    path = MONOREPO / ".env.example"
    assert path.exists(), "Missing .env.example"

    content = path.read_text()
    required = [
        "DATABASE_URL",
        "REDIS_URL",
        "JWT_SECRET",
        "CORS_ORIGINS",
        "POSTGRES_PASSWORD",
        "MYCOAI_QDRANT_HOST",
        "MYCOAI_QDRANT_PORT",
    ]
    for var in required:
        assert var in content, f".env.example missing {var}"
