import datetime

import altair as alt
import numpy as np
import pandas as pd
from flask import Blueprint
from flask import render_template
from flask import request

from geo_activity_playground.core.activities import ActivityRepository
from geo_activity_playground.core.meta_search import apply_search_query
from geo_activity_playground.webui.search_util import search_query_from_form
from geo_activity_playground.webui.search_util import SearchQueryHistory


def make_eddington_blueprint(
    repository: ActivityRepository, search_query_history: SearchQueryHistory
) -> Blueprint:
    blueprint = Blueprint("eddington", __name__, template_folder="templates")

    @blueprint.route("/")
    def index():
        query = search_query_from_form(request.args)
        search_query_history.register_query(query)
        activities = apply_search_query(repository.meta, query).copy()

        activities["day"] = [start.date() for start in activities["start"]]

        sum_per_day = activities.groupby("day").apply(
            lambda group: int(sum(group["distance_km"])), include_groups=False
        )
        counts = dict(zip(*np.unique(sorted(sum_per_day), return_counts=True)))
        eddington = pd.DataFrame(
            {"distance_km": d, "count": counts.get(d, 0)}
            for d in range(max(counts.keys()) + 1)
        )
        eddington["total"] = eddington["count"][::-1].cumsum()[::-1]
        x = list(range(1, max(eddington["distance_km"]) + 1))
        en = eddington.loc[eddington["total"] >= eddington["distance_km"]][
            "distance_km"
        ].iloc[-1]
        eddington["missing"] = eddington["distance_km"] - eddington["total"]

        logarithmic_plot = (
            (
                (
                    alt.Chart(
                        eddington,
                        height=500,
                        width=1000,
                        title=f"Eddington Number {en}",
                    )
                    .mark_area(interpolate="step")
                    .encode(
                        alt.X(
                            "distance_km",
                            scale=alt.Scale(domainMin=0),
                            title="Distance / km",
                        ),
                        alt.Y(
                            "total",
                            scale=alt.Scale(domainMax=en + 10),
                            title="Days exceeding distance",
                        ),
                        [
                            alt.Tooltip("distance_km", title="Distance / km"),
                            alt.Tooltip("total", title="Days exceeding distance"),
                            alt.Tooltip("missing", title="Days missing for next"),
                        ],
                    )
                )
                + (
                    alt.Chart(pd.DataFrame({"distance_km": x, "total": x}))
                    .mark_line(color="red")
                    .encode(alt.X("distance_km"), alt.Y("total"))
                )
            )
            .interactive()
            .to_json(format="vega")
        )
        return render_template(
            "eddington/index.html.j2",
            eddington_number=en,
            logarithmic_plot=logarithmic_plot,
            eddington_table=eddington.loc[
                (eddington["distance_km"] > en) & (eddington["distance_km"] <= en + 10)
            ].to_dict(orient="records"),
            query=query.to_jinja(),
            yearly_eddington=get_yearly_eddington(activities),
            eddington_number_history_plot=get_eddington_number_history(activities),
        )

    return blueprint


def get_eddington_number(distances: pd.Series) -> int:
    if len(distances) == 1:
        if distances.iloc[0] >= 1:
            return 1
        else:
            0

    sorted_distances = sorted(distances, reverse=True)
    for en, distance in enumerate(sorted_distances, 1):
        if distance < en:
            return en - 1


def get_yearly_eddington(meta: pd.DataFrame) -> dict[int, int]:
    meta = meta.dropna(subset=["start", "distance_km"]).copy()
    meta["year"] = [start.year for start in meta["start"]]
    meta["date"] = [start.date() for start in meta["start"]]

    yearly_eddington = meta.groupby("year").apply(
        lambda group: get_eddington_number(
            group.groupby("date").apply(
                lambda group2: int(group2["distance_km"].sum()), include_groups=False
            )
        ),
        include_groups=False,
    )
    return yearly_eddington.to_dict()


def get_eddington_number_history(meta: pd.DataFrame) -> dict:
    meta = meta.dropna(subset=["start", "distance_km"]).copy()
    meta["year"] = [start.year for start in meta["start"]]
    meta["date"] = [start.date() for start in meta["start"]]

    daily_distances = meta.groupby("date").apply(
        lambda group2: int(group2["distance_km"].sum()), include_groups=False
    )

    eddington_number_history = {"date": [], "eddington_number": []}
    top_days = []
    for date, distance in daily_distances.items():
        if len(top_days) == 0:
            top_days.append(distance)
        else:
            if distance >= top_days[0]:
                top_days.append(distance)
                top_days.sort()
        while top_days[0] < len(top_days):
            top_days.pop(0)
        eddington_number_history["date"].append(
            datetime.datetime.combine(date, datetime.datetime.min.time())
        )
        eddington_number_history["eddington_number"].append(len(top_days))
    history = pd.DataFrame(eddington_number_history)

    return (
        alt.Chart(history)
        .mark_line(interpolate="step-after")
        .encode(
            alt.X("date", title="Date"),
            alt.Y("eddington_number", title="Eddington number"),
        )
    ).to_json(format="vega")
