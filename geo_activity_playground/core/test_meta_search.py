import datetime

import pandas as pd

from geo_activity_playground.core.meta_search import _make_mask
from geo_activity_playground.core.meta_search import apply_search_query
from geo_activity_playground.core.meta_search import SearchQuery


def test_empty_query() -> None:
    activity_meta = pd.DataFrame(
        {
            "equipment": pd.Series(["A", "B", "B"]),
            "id": pd.Series([1, 2, 3]),
            "kind": pd.Series(["X", "X", "Y"]),
            "name": ["Test1", "Test2", "Test3"],
            "start": [
                datetime.datetime(2024, 12, 24, 10),
                datetime.datetime(2025, 1, 1, 10),
                None,
            ],
        }
    )

    search_query = SearchQuery()

    actual = apply_search_query(activity_meta, search_query)
    assert (actual["id"] == activity_meta["id"]).all()


def test_equipment_query() -> None:
    activity_meta = pd.DataFrame(
        {
            "equipment": pd.Series(["A", "B", "B"]),
            "id": pd.Series([1, 2, 3]),
            "kind": pd.Series(["X", "X", "Y"]),
            "name": ["Test1", "Test2", "Test3"],
            "start": [
                datetime.datetime(2024, 12, 24, 10),
                datetime.datetime(2025, 1, 1, 10),
                None,
            ],
        }
    )
    search_query = SearchQuery(equipment=["B"])
    actual = apply_search_query(activity_meta, search_query)
    assert set(actual["id"]) == {2, 3}


def test_make_mask() -> None:
    index = [1, 2]
    assert (_make_mask(index, True) == pd.Series([True, True], index=index)).all()
    assert (_make_mask(index, False) == pd.Series([False, False], index=index)).all()
