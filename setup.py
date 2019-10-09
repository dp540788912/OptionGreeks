import sys
from setuptools import setup


assert sys.version_info >= (3, 6, 0)


def read_file(file):
    with open(file, "rt") as f:
        return f.read()


setup(
    name="update_greeks",
    version='1.0',
    description="daily schedule for update",
    author='GuangXingLi',
    python_requires='>=3.6',
    install_requires=read_file('requirements.txt').strip(),
    entry_points={"console_scripts": ["update-greeks = __main__:cli"]},
)

