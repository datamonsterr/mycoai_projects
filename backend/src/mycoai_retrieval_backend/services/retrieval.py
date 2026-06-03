from mycoai_retrieval_backend.schemas.retrieval import RetrievalHit


async def retrieve(query: str, limit: int) -> list[RetrievalHit]:
    return []
