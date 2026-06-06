"""Import coverage for all schema submodules."""


def test_import_schemas_admin() -> None:
    from mycoai_retrieval_backend.schemas import admin  # noqa: F401


def test_import_schemas_auth() -> None:
    from mycoai_retrieval_backend.schemas import auth  # noqa: F401


def test_import_schemas_dashboard() -> None:
    from mycoai_retrieval_backend.schemas import dashboard  # noqa: F401


def test_import_schemas_feedback() -> None:
    from mycoai_retrieval_backend.schemas import feedback  # noqa: F401


def test_import_schemas_images() -> None:
    from mycoai_retrieval_backend.schemas import images  # noqa: F401


def test_import_schemas_index() -> None:
    from mycoai_retrieval_backend.schemas import index  # noqa: F401


def test_import_schemas_media() -> None:
    from mycoai_retrieval_backend.schemas import media  # noqa: F401


def test_import_schemas_retrieval() -> None:
    from mycoai_retrieval_backend.schemas import retrieval  # noqa: F401


def test_import_schemas_species() -> None:
    from mycoai_retrieval_backend.schemas import species  # noqa: F401


def test_import_schemas_training() -> None:
    from mycoai_retrieval_backend.schemas import training  # noqa: F401
