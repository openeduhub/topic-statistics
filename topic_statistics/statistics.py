from typing import Optional

import numpy as np
from data_utils.default_pipelines.data import Data, subset_data_points
from data_utils.defaults import Fields, Grouped_Fields
from pydantic import BaseModel


class Count(BaseModel):
    total: int
    editorially_confirmed: int


def count(data: Data, topic_uri: str, topic_url: str) -> Count:
    """
    Get the count statistics for data that belongs to the topic or collection.
    """
    data = _get_relevant(data, topic_uri, topic_url)
    return _get_count(data, topic_url)


def count_by_field(
    data: Data, topic_uri: str, topic_url: str, field: Grouped_Fields
) -> dict[str, Count]:
    """Like :func:`count`, but also groups by a metadata field."""
    topic_data = _get_relevant(data, topic_uri, topic_url)

    results: dict[str, Count] = dict()
    for index, uri in enumerate(data.target_data[field.value].uris):
        relevant = topic_data.target_data[field.value].arr[:, index]
        relevant_data = subset_data_points(topic_data, np.where(relevant)[0])
        results[uri] = _get_count(relevant_data, topic_url)

    return results


def _get_relevant(
    data: Data, topic_uri: Optional[str], topic_url: Optional[str]
) -> Data:
    """Get a subset of the data that belongs to the topic or collection."""
    uri_index = (
        np.where(data.target_data[Fields.TOPIC.value].uris == topic_uri)[0]
        if topic_uri is not None
        else np.arange(len(data.target_data[Fields.TOPIC.value].uris))
    )
    url_index = (
        np.where(data.target_data[Fields.COLLECTIONS_LOCATION.value].uris == topic_url)[
            0
        ]
        if topic_url is not None
        else np.arange(len(data.target_data[Fields.COLLECTIONS_LOCATION.value].uris))
    )

    relevant = np.logical_or(
        data.target_data[Fields.TOPIC.value].arr[:, uri_index],
        data.target_data[Fields.COLLECTIONS_LOCATION.value].arr[:, url_index],
    )
    return subset_data_points(data, np.where(relevant)[0])


def _get_count(data: Data, topic_url: str) -> Count:
    """Calculate the count statistics for the given data."""
    url_index = np.where(
        data.target_data[Fields.COLLECTIONS_LOCATION.value].uris == topic_url
    )[0]

    # an assignment is editorially confirmed
    # if the material is assigned to the collection
    editorially_confirmed = (
        data.target_data[Fields.COLLECTIONS_LOCATION.value].arr[:, url_index].sum()
    )

    return Count(
        total=len(data.editor_arr),
        editorially_confirmed=editorially_confirmed,
    )
