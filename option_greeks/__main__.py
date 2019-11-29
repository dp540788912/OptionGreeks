# -*- coding: utf-8 -*-
import click
from option_greeks.mongo_insert import get_work


@click.group()
def cli():
    pass


@cli.command(name='update')
@click.option('-m', '--mongo-url', required=True)
@click.option('-r', '--rqdata-uri', required=True)
@click.option('-d', '--days', required=True)
def update(mongo_url, rqdata_uri, days):
    print('work start')
    get_work(mongo_url, rqdata_uri, days)


if __name__ == '__main__':
    cli()

