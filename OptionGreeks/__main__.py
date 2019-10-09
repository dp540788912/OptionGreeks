import click
from OptionGreeks.mongo_insert import *


@click.group()
def cli():
    pass


@cli.command(name='update')
@click.option('--name', default='youxiu')
def update(name):
    get_work(name)


if __name__ == '__main__':
    cli()