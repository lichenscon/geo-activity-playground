import dataclasses
import datetime
import re
import urllib.parse
from typing import Optional

import numpy as np
import pandas as pd


@dataclasses.dataclass
class SearchQuery:
    equipment: list[str] = dataclasses.field(default_factory=list)
    kind: list[str] = dataclasses.field(default_factory=list)
    name: Optional[str] = None
    name_case_sensitive: bool = False
    start_begin: Optional[datetime.date] = None
    start_end: Optional[datetime.date] = None

    @property
    def active(self) -> bool:
        return (
            self.equipment
            or self.kind
            or self.name
            or self.start_begin
            or self.start_end
        )

    def to_jinja(self) -> dict:
        return {
            "equipment": self.equipment,
            "kind": self.kind,
            "name": self.name or "",
            "name_case_sensitive": self.name_case_sensitive,
            "start_begin": _format_optional_date(self.start_begin),
            "start_end": _format_optional_date(self.start_end),
            "active": self.active,
        }

    def to_url_str(self) -> str:
        variables = []
        for equipment in self.equipment:
            variables.append(("equipment", equipment))
        for kind in self.kind:
            variables.append(("kind", kind))
        if self.name:
            variables.append(("name", self.name))
        if self.name_case_sensitive:
            variables.append(("name_case_sensitive", "true"))
        if self.start_begin:
            variables.append(("start_begin", self.start_begin.isoformat()))
        if self.start_end:
            variables.append(("start_end", self.start_end.isoformat()))

        return "&".join(
            f"{key}={urllib.parse.quote_plus(value)}" for key, value in variables
        )


def _format_optional_date(date: Optional[datetime.date]) -> str:
    if date is None:
        return ""
    else:
        return date.isoformat()


def apply_search_query(
    activity_meta: pd.DataFrame, search_query: SearchQuery
) -> pd.DataFrame:
    mask = _make_mask(activity_meta.index, True)

    if search_query.equipment:
        mask &= _filter_column(activity_meta["equipment"], search_query.equipment)
    if search_query.kind:
        mask &= _filter_column(activity_meta["kind"], search_query.kind)
    if search_query.name:
        mask &= pd.Series(
            [
                bool(
                    re.search(
                        search_query.name,
                        activity_name,
                        0 if search_query.name_case_sensitive else re.IGNORECASE,
                    )
                )
                for activity_name in activity_meta["name"]
            ],
            index=activity_meta.index,
        )
    if search_query.start_begin is not None:
        start_begin = datetime.datetime.combine(
            search_query.start_begin, datetime.time.min
        )
        mask &= start_begin <= activity_meta["start"]
    if search_query.start_end is not None:
        start_end = datetime.datetime.combine(search_query.start_end, datetime.time.max)
        mask &= activity_meta["start"] <= start_end

    return activity_meta.loc[mask]


def _make_mask(
    index: pd.Index,
    default: bool,
) -> pd.Series:
    if default:
        return pd.Series(np.ones((len(index),), dtype=np.bool), index=index)
    else:
        return pd.Series(np.zeros((len(index),), dtype=np.bool), index=index)


def _filter_column(column: pd.Series, values: list):
    sub_mask = _make_mask(column.index, False)
    for equipment in values:
        sub_mask |= column == equipment
    return sub_mask
