import argparse
from enum import Enum
from pathlib import Path
from typing import Literal, Optional, Union
from functools import partial

import data_utils.filters as filt
import pandas as pd
import uvicorn
from data_utils.default_pipelines.data import Data
from data_utils.default_pipelines.flat_classification import generate_data
from data_utils.defaults import Fields
from data_utils.fetch import fetch
from fastapi import FastAPI
from nlprep import Iterable
from pydantic import BaseModel

from topic_statistics._version import __version__
from topic_statistics.statistics import Count, count, count_by_field


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
        "--data-dir",
        action="store",
        default="./data",
        help="The directory in which the data shall be stored.",
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
        filters=[filt.get_len_filter([Fields.TOPIC.value], min_lengths=1)],
    )

    global data
    try:
        data = generate_data_fun(json_file=data_dir / "workspace_data-public-only.json")
    except FileNotFoundError:
        data = None

    # Data types
    class Input_Update(BaseModel):
        username: Optional[str] = None
        password: Optional[str] = None
        url: str = "https://elasticdump.staging.openeduhub.net"
        data_set: str = "workspace_data-public-only.json.gz"
        skip_if_exists: bool = True

    class Input_Stats(BaseModel):
        topic_uri: str
        group_by_fields: Optional[Iterable[Fields]] = None

    class Output_Stats(BaseModel):
        total: Count
        by_fields: Optional[dict[Fields, dict[str, Count]]] = None

    app = FastAPI()

    @app.get("/_ping")
    async def ping():
        pass

    @app.post("/update-data")
    async def update_data(inp: Input_Update):
        new_json = fetch(
            base_url=inp.url,
            target_file=inp.data_set,
            output_dir=data_dir,
            username=inp.username,
            password=inp.password,
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
                field: count_by_field(data, inp.topic_uri, field)
                for field in inp.group_by_fields
            }

        return Output_Stats(total=count(data, inp.topic_uri), by_fields=grouped_counts)

    uvicorn.run(app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()