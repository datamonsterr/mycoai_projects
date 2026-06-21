from dataclasses import dataclass

from backend.core.security import require_role


@dataclass
class _FakeUser:
    role: str


def test_require_role_passes_for_owner() -> None:
    require_role(_FakeUser(role="owner"), "owner")


def test_require_role_raises_for_user() -> None:
    try:
        require_role(_FakeUser(role="user"), "owner")
    except PermissionError:
        pass
    else:
        raise AssertionError("Expected PermissionError")
