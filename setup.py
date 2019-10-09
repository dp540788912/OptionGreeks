import sys
from setuptools import setup


def read_file(file):
    with open(file, "rt") as f:
        return f.readlines()


requires = read_file('requirements.txt')
print(requires)

setup(
    name="updateGreeks",
    version='1.0',
    description="daily schedule for update",
    python_requires='>=3.6',
    install_requires=requires,
    entry_points={"console_scripts": ["updateGreeks=OptionGreeks.__main__:cli"]},
)

