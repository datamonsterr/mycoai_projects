from __future__ import annotations

from typing import Any, cast

from qdrant_client.models import FieldCondition, Filter, MatchValue

from .models import FilterSpec

_FIELD_STRAIN = "strain"
_FIELD_MEDIA = "media"
_FIELD_ENVIRONMENT = "environment"  # legacy/research schema uses this key
_FIELD_ANGLE = "angle"
_FIELD_SPECY = "specy"
_FIELD_PARENT_ID = "parent_item_id"


def _media_condition(value: str) -> list[FieldCondition]:
    """Match against either the new 'media' key or the legacy 'environment' key."""
    return [
        FieldCondition(key=_FIELD_MEDIA, match=MatchValue(value=value)),
        FieldCondition(key=_FIELD_ENVIRONMENT, match=MatchValue(value=value)),
    ]


def build_filter(filter_spec: FilterSpec | None) -> Filter | None:
    if filter_spec is None:
        return None

    must: list[FieldCondition | Filter] = []
    must_not: list[FieldCondition] = []

    if filter_spec.media is not None:
        # OR across media/environment so legacy research-seeded points still match.
        must.append(Filter(should=cast(Any, _media_condition(filter_spec.media))))

    if filter_spec.exclude_media is not None:
        for cond in _media_condition(filter_spec.exclude_media):
            must_not.append(cond)

    if filter_spec.exclude_strain is not None:
        must_not.append(
            FieldCondition(
                key=_FIELD_STRAIN,
                match=MatchValue(value=filter_spec.exclude_strain),
            )
        )

    if filter_spec.angle is not None:
        must.append(
            FieldCondition(
                key=_FIELD_ANGLE,
                match=MatchValue(value=filter_spec.angle),
            )
        )

    if filter_spec.strain is not None:
        must.append(
            FieldCondition(
                key=_FIELD_STRAIN,
                match=MatchValue(value=filter_spec.strain),
            )
        )

    if filter_spec.specy is not None:
        must.append(
            FieldCondition(
                key=_FIELD_SPECY,
                match=MatchValue(value=filter_spec.specy),
            )
        )

    if filter_spec.parent_id is not None:
        must.append(
            FieldCondition(
                key=_FIELD_PARENT_ID,
                match=MatchValue(value=filter_spec.parent_id),
            )
        )

    if filter_spec.exclude_ids is not None:
        for eid in filter_spec.exclude_ids:
            must_not.append(
                FieldCondition(
                    key="_id",
                    match=MatchValue(value=eid),
                )
            )

    if not must and not must_not:
        return None

    # must list may contain nested Filters (for OR media); flatten at top level.
    flat_must: list[Any] = []
    for must_cond in must:
        flat_must.append(must_cond)

    return Filter(
        must=cast(Any, flat_must) if flat_must else None,
        must_not=cast(Any, must_not) if must_not else None,
    )
