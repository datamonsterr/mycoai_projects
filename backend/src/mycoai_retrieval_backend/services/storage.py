from pathlib import Path


class StorageService:
    def __init__(self, root: Path) -> None:
        self.root = root

    def resolve(self, name: str) -> Path:
        return self.root / name
