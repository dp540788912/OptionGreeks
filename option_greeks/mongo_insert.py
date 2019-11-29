# -*- coding: utf-8 -*-
import pymongo
from pymongo import UpdateOne
import datetime as dt
import option_greeks.bs_model.computation as og
import rqdatac

# url = 'mongodb://root:root@192.168.10.30:27017/options.py?authSource=admin'
database = 'option'
# col = 'greeks'


class CustomizedMongo:
    """A customized class for use mongo."""
    def __init__(self, url, db, col):
        self._client = pymongo.MongoClient(url)
        self._db = self._client[db]
        self._col = self._db[col]

    def close(self):
        self._client.close()

    def db_list(self):
        """check database names in the client"""
        name_list = self._client.list_database_names()
        return name_list

    def col_list(self):
        """check collection list in this database"""
        col_list = self._db.list_collection_names()
        return col_list

    def insert(self, _data, upsert=False):
        """Data is a pandas DataFrame, """
        if _data is None:
            return False
        _data = _data.reset_index()
        if not upsert:
            try:
                self._col.insert_many(_data.T.to_dict().values())
            except ConnectionError:
                raise ConnectionError('Connection failed')
            print('Insertion Completed')
        else:
            data_dic = _data.to_dict('records')
            operations = []
            for d in data_dic:
                operations.append(UpdateOne({'trading_date': d['trading_date'], 'order_book_id': d['order_book_id']},
                                            {'$set': d}, upsert=True))
            print('before bulk write')
            self._col.bulk_write(operations)
            print('bulk write sucess')
        return True

    def drop(self):
        self._col.drop()

    def find(self, query):
        return self._col.find(query)

    def find_max(self, key, limit=1):
        return self._col.find().sort([(key, pymongo.DESCENDING)]).limit(limit)


@ og.check_runtime
def initial_data(_url, _db, _col, implied_price):

    my_mongo = CustomizedMongo(_url, _db, _col)
    trading_date = og.get_trading_dates_all_option(dt.datetime(2017, 11, 23).date())
    trading_date.reverse()

    data_processing(my_mongo, trading_date, implied_price)
    my_mongo.close()


@ og.check_runtime
def data_processing(_my_mongo, _trading_dates, implied_price, drop=0, sc_only='all', upsert=False):
    if type(_trading_dates) is not list:
        _trading_dates = [_trading_dates]
    length = len(_trading_dates)

    if drop == 1:
        _my_mongo.drop()
    else:
        for date in _trading_dates:
            length -= 1
            try:
                data = og.get_greeks(date, sc_only=sc_only, implied_price=implied_price)
                print(data)
            except ValueError:
                print('{} data is not reachable yet'.format(date))
                continue
            _my_mongo.insert(data, upsert=upsert)
            print(date, ": finished", 'job left: ', length)


def update_mongo_depre(url, db, implied):
    if implied:
        col = 'greeks_implied_forward'
    else:
        col = 'greeks'
    key = 'trading_date'
    my_mongo = CustomizedMongo(url, db, col)
    _max = my_mongo.find_max(key)
    newest_date = next(_max)['trading_date']
    newest_date = dt.datetime.strptime(newest_date, '%Y-%m-%d').date()

    trading_date = og.get_trading_dates_all_option(dt.datetime.now().date(), newest_date - dt.timedelta(days=1))
    try:
        data_processing(my_mongo, trading_date, implied)
    except ValueError:
        print('today\'s data is not reachable yet')


def get_previous_trading_days_customized(n):
    today = dt.datetime.now().date()
    if len(rqdatac.get_trading_dates(today, today)) == 1:
        n -= 1
        yield today
    while n > 0:
        today = rqdatac.get_previous_trading_date(today)
        yield today
        n -= 1


def for_test(mongo_url, db, _days, implied):
    rqdatac.init(uri='tcp://rice:rice@dev:16010')
    test = 'test'
    '''find n trading days before today'''
    my_mongo = CustomizedMongo(mongo_url, db, test)
    trading_days = list(get_previous_trading_days_customized(int(_days)))
    try:
        print('data_processing')
        data_processing(my_mongo, trading_days, implied, upsert=True)
    except ValueError:
        print('today\'s data is not reachable yet')


def update_mongo(url, db, _days, implied):
    if implied:
        col = 'greeks_implied_forward'
    else:
        col = 'greeks'
    '''find n trading days before today'''
    my_mongo = CustomizedMongo(url, db, col)
    trading_days = list(get_previous_trading_days_customized(int(_days)))
    try:
        data_processing(my_mongo, trading_days, implied, upsert=True)
    except ValueError:
        print('data not ready yet')


def update_one_day(implied, _date):
    pass


def get_work(_url, rqdata_uri, days):
    rqdatac.init(uri=rqdata_uri)
    update_mongo(_url, database, days, True)
    update_mongo(_url, database, days, False)


if __name__ == '__main__':
    mongo_url = 'mongodb://root:root@:27017/options.py?authSource=admin'
    days = 3
    rqdata_uri = 'tcp://rice:rice@dev:16016'
    # for_test(mongo_url, database, days, implied=True)
    get_work(mongo_url, rqdata_uri, days)

