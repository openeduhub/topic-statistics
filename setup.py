#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="topic-statistics",
    version="0.1.0",
    description="Calculate various statistics for WLO topic pages.",
    author="",
    author_email="",
    packages=find_packages(),
    install_requires=[
        d for d in open("requirements.txt").readlines() if not d.startswith("--")
    ],
    entry_points={"console_scripts": ["topic-statistics = topic_statistics.webservice:main"]},
)
