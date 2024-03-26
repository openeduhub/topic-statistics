import argparse
from collections.abc import Iterable
from functools import partial
from pathlib import Path
from typing import Optional

import its_data.filters as filt
import pandas as pd
import uvicorn
from fastapi import FastAPI
from its_data.default_pipelines.flat_classification import generate_data
from its_data.defaults import Fields
from its_data.fetch import fetch
from pydantic import BaseModel, Field

from topic_statistics._version import __version__
from topic_statistics.statistics import (
    Category_Count,
    Count,
    Field_Counts,
    count,
    count_by_field,
)


def main():
    # define CLI arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port", action="store", default=8080, help="Port to listen on", type=int
    )
    parser.add_argument(
        "--host", action="store", default="0.0.0.0", help="Hosts to listen on", type=str
    )
    parser.add_argument(
        "--username",
        action="store",
        default=None,
        help="The username to use when running a data update and authenticating at the source.",
        type=str,
    )
    parser.add_argument(
        "--password",
        action="store",
        default=None,
        help="The password to use when running a data update and authenticating at the source.",
        type=str,
    )
    parser.add_argument(
        "--data-dir",
        action="store",
        default="./data",
        help="The directory in which the data shall be stored. Creates directories if necessary.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s {version}".format(version=__version__),
    )

    # read passed CLI arguments
    args = parser.parse_args()

    # load the data, if possible
    data_dir = Path(args.data_dir)
    generate_data_fun = partial(
        generate_data,
        target_fields=[x.value for x in Fields],
        use_defaults=True,
        skip_labels=True,
        # we only need data that is part of at least one collection
        # or has at least one topic assigned
        filters=[
            filt.get_len_filter(
                [
                    Fields.TOPIC.value,
                    Fields.COLLECTIONS_LOCATION.value,
                ],
                min_lengths=1,
            )
        ],
    )

    global data
    try:
        data = generate_data_fun(json_file=data_dir / "workspace_data-public-only.json")
    except FileNotFoundError:
        data = None

    # Data types
    class Input_Update(BaseModel):
        skip_if_exists: bool = True

    class Input_Stats(BaseModel):
        topic_uri: str
        topic_url: str
        group_by_fields: Optional[Iterable[Fields]] = Field(
            default=None, examples=[[Fields.TAXONID.value]]
        )

    class Output_Stats(BaseModel):
        total: Count
        by_fields: Optional[list[Field_Counts]] = None

    app = FastAPI()

    @app.get("/_ping")
    async def ping():
        pass

    @app.post("/update-data")
    async def update_data(inp: Input_Update):
        new_json = fetch(
            base_url="https://elasticdump.prod.openeduhub.net",
            target_file="workspace_data-public-only.json.gz",
            output_dir=data_dir,
            username=args.username,
            password=args.password,
            skip_if_exists=inp.skip_if_exists,
        )

        global data
        data = generate_data_fun(json_file=new_json)

    @app.post("/counts")
    async def counts(inp: Input_Stats) -> Output_Stats:
        if data is None:
            raise ValueError("No data found! Please run 'update-data' first.")

        grouped_counts = None
        if inp.group_by_fields is not None:
            grouped_counts = {
                field: count_by_field(
                    data, topic_uri=inp.topic_uri, topic_url=inp.topic_url, field=field
                )
                for field in inp.group_by_fields
            }

        return Output_Stats(
            total=count(data, topic_uri=inp.topic_uri, topic_url=inp.topic_url),
            by_fields=[
                Field_Counts(
                    field=field.value,
                    counts=[
                        Category_Count(
                            total=count.total,
                            editorially_confirmed=count.editorially_confirmed,
                            category=category,
                        )
                        for category, count in value.items()
                    ],
                )
                for field, value in grouped_counts.items()
            ]
            if grouped_counts is not None
            else None,
        )

    uvicorn.run(app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
