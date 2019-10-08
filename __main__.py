import click
from mongo_insert import *


@click.group()
def cli():
    pass


@cli.command(name='update')
def update():
    get_work()
