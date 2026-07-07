"""Import coverage for service and repo stub modules."""


class TestServiceImports:
    def test_import_services_batch(self) -> None:
        from backend.services.batch import enqueue_batch  # noqa: F401

    def test_import_services_feature_extraction(self) -> None:
        from backend.services.feature_extraction import (  # noqa: F401
            extract_features,
        )

    def test_import_services_retrieval(self) -> None:
        from backend.services.retrieval import retrieve_by_point_id  # noqa: F401

    def test_import_services_segmentation(self) -> None:
        from backend.services.segmentation import (  # noqa: F401
            segment_image,
        )

    def test_import_services_storage(self) -> None:
        from backend.services.storage import (
            create_storage,  # noqa: F401
        )

    def test_import_services_stores(self) -> None:
        from backend.services.stores import (  # noqa: F401
            MemoryStore,
            new_id,
            seed_data,
            utcnow,
        )

    def test_import_services_training(self) -> None:
        from backend.services import training  # noqa: F401

    def test_import_services_qdrant_client(self) -> None:
        from backend.services import qdrant_client  # noqa: F401


class TestRepoImports:
    def test_import_repos_image(self) -> None:
        from backend.repos.image import ImageRepository  # noqa: F401

    def test_import_repos_strain(self) -> None:
        from backend.repos.strain import StrainRepository  # noqa: F401

    def test_import_repos_user(self) -> None:
        from backend.repos import user  # noqa: F401

    def test_import_repos_species(self) -> None:
        from backend.repos import species  # noqa: F401

    def test_import_repos_feedback(self) -> None:
        from backend.repos import feedback  # noqa: F401

    def test_import_repos_media(self) -> None:
        from backend.repos import media  # noqa: F401
