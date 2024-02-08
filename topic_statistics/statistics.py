from typing import Optional

import numpy as np
from data_utils.default_pipelines.data import Data, subset_data_points
from data_utils.defaults import Fields
from pydantic import BaseModel


class Count(BaseModel):
    total: int
    editorially_confirmed: int


def _get_relevant(data: Data, topic_uri: str) -> Data:
    topic_index = np.where(data.target_data[Fields.TOPIC.value].uris == topic_uri)[0]
    if len(topic_index) == 0:
        raise ValueError(f"No collection with URI {topic_uri} found!")

    relevant = data.target_data[Fields.TOPIC.value].arr[:, topic_index[0]]
    return subset_data_points(data, np.where(relevant)[0])


def count(data: Data, topic_uri: Optional[str]) -> Count:
    if topic_uri is not None:
        data = _get_relevant(data, topic_uri=topic_uri)

    return Count(
        total=len(data.editor_arr), editorially_confirmed=data.editor_arr.sum()
    )


def count_by_field(data: Data, topic_uri: str, field: Fields) -> dict[str, Count]:
    topic_data = _get_relevant(data, topic_uri)

    results: dict[str, Count] = dict()
    for index, uri in enumerate(data.target_data[field.value].uris):
        relevant = topic_data.target_data[field.value].arr[:, index]
        results[uri] = count(
            subset_data_points(topic_data, np.where(relevant)[0]), None
        )

    return results
