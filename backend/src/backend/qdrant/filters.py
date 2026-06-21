from __future__ import annotations

from typing import Any, cast

from qdrant_client.models import FieldCondition, Filter, MatchValue

from .models import FilterSpec

_FIELD_STRAIN = "strain"
_FIELD_ENVIRONMENT = "environment"
_FIELD_ANGLE = "angle"
_FIELD_SPECY = "specy"
_FIELD_PARENT_ID = "parent_item_id"


def build_filter(filter_spec: FilterSpec | None) -> Filter | None:
    if filter_spec is None:
        return None

    must: list[FieldCondition] = []
    must_not: list[FieldCondition] = []

    if filter_spec.environment is not None:
        must.append(
            FieldCondition(
                key=_FIELD_ENVIRONMENT,
                match=MatchValue(value=filter_spec.environment),
            )
        )

    if filter_spec.exclude_environment is not None:
        must_not.append(
            FieldCondition(
                key=_FIELD_ENVIRONMENT,
                match=MatchValue(value=filter_spec.exclude_environment),
            )
        )

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

    return Filter(
        must=cast(Any, must) if must else None,
        must_not=cast(Any, must_not) if must_not else None,
    )
