# -*- coding: utf-8 -*-
import sys
from setuptools import setup, find_packages


setup(
    name="updateGreeks",
    version='1.0',
    description="daily schedule for update",
    packages=find_packages(),
    python_requires='>=3.6',
    install_requires=[
        'pandas',
        'numpy',
        'pymongo',
        'setuptools',
        'click',
        'rqdatac',
        'rqanalysis',
    ],
    entry_points={"console_scripts": ["updateGreeks=OptionGreeks.__main__:cli"]},
)

