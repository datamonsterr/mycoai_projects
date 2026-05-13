from pathlib import Path

MONOREPO = Path(__file__).resolve().parents[2]


def test_backend_dockerfile_has_from() -> None:
    path = MONOREPO / "repos/mycoai_retrieval_backend/Dockerfile"
    assert path.exists(), "Missing backend Dockerfile"
    content = path.read_text()
    assert content.startswith("FROM"), "Dockerfile must start with FROM"


def test_backend_dockerfile_uses_python() -> None:
    path = MONOREPO / "repos/mycoai_retrieval_backend/Dockerfile"
    content = path.read_text()
    assert "python:3.13" in content, "Backend must use python:3.13 base"


def test_frontend_dockerfile_has_from() -> None:
    path = MONOREPO / "repos/mycoai_retrieval_frontend/Dockerfile"
    assert path.exists(), "Missing frontend Dockerfile"
    content = path.read_text()
    assert content.startswith("FROM"), "Dockerfile must start with FROM"


def test_frontend_dockerfile_serves_with_nginx() -> None:
    path = MONOREPO / "repos/mycoai_retrieval_frontend/Dockerfile"
    content = path.read_text()
    assert "nginx" in content, "Frontend must serve with nginx"
    assert "EXPOSE 80" in content, "Frontend must expose port 80"


def test_frontend_nginx_config_exists() -> None:
    path = MONOREPO / "repos/mycoai_retrieval_frontend/deploy/nginx/default.conf"
    assert path.exists(), "Missing nginx default.conf"

    content = path.read_text()
    assert "proxy_pass http://backend:8000" in content
    assert "try_files" in content
