from mycoai_retrieval_backend.core.security import require_role
from mycoai_retrieval_backend.models.user import User


def test_require_role_passes_for_admin() -> None:
    user = User(id="1", email="a@b.c", roles=("admin",), service="test")
    require_role(user, "admin")


def test_require_role_raises_for_viewer() -> None:
    user = User(id="2", email="v@b.c", roles=("viewer",), service="test")
    try:
        require_role(user, "admin")
    except PermissionError:
        pass
    else:
        raise AssertionError("Expected PermissionError")
