import argparse

from src.prepare.init import run_prepare_init


def reformat_incoming_dataset(collection: str = "qdrant-research", limit: int | None = None):
    return run_prepare_init(
        collection_name=collection,
        source_collections=["incoming"],
        limit=limit,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare incoming dataset and upload research features")
    parser.add_argument("--collection", default="qdrant-research")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    reformat_incoming_dataset(collection=args.collection, limit=args.limit)
