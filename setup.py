# -*- coding: utf-8 -*-
import sys
from setuptools import setup, find_packages


setup(
    name="update_greeks",
    version='3.1',
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
        'rqanalysis', 'scipy', 'h5py'
    ],
    entry_points={"console_scripts": ["update-greeks=option_greeks.__main__:cli"]},
)

