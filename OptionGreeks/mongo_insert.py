# -*- coding: utf-8 -*-
import pymongo
import datetime as dt
from OptionGreeks import option_greeks as og


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

    def insert(self, _data):
        """Data is a pandas DataFrame, """
        if _data is None:
            return False
        _data = _data.reset_index()
        _data['trading_date'] = _data['trading_date'].apply(lambda x: x.strftime("%Y-%m-%d"))
        try:
            self._col.insert_many(_data.T.to_dict().values())
        except ConnectionError:
            raise ConnectionError('Connection failed')
        print('work done')
        return True

    def drop(self):
        self._col.drop()

    def find(self, query):
        return self._col.find(query)

    def find_max(self, key, limit=1):
        return self._col.find().sort([(key, pymongo.DESCENDING)]).limit(limit)

# FIXME: 2019-06-11, all price data is missing
@ og.check_runtime
def initial_data(drop=0):
    url = 'mongodb://root:root@192.168.10.30:27017/options.py?authSource=admin'
    db = 'option'
    col = 'greeks'
    my_mongo = CustomizedMongo(url, db, col)
    trading_date = og.get_trading_dates_all_option('2019-06-10')
    trading_date += og.get_trading_dates_all_option('2019-09-28', '2019-06-12')
    trading_date.reverse()
    length = len(trading_date)

    Data_processing(my_mongo, trading_date)
    my_mongo.close()


@ og.check_runtime
def Data_processing(_my_mongo, _trading_dates, implied_price, drop=0):
    length = len(_trading_dates)
    if drop == 1:
        _my_mongo.drop()
    else:
        for date in _trading_dates:
            length -= 1
            data = og.get_greeks(date, sc_only='init', implied_price=implied_price)
            _my_mongo.insert(data)
            print(data)
            print(date, ": finished", 'job left: ', length)


def update_mongo_1(implied):
    url = 'mongodb://root:root@192.168.10.30:27017/options.py?authSource=admin'
    db = 'option'
    if implied:
        col = 'greeks_implied_forward'
    else:
        col = 'greeks'
    key = 'trading_date'
    my_mongo = CustomizedMongo(url, db, col)
    _max = my_mongo.find_max(key)
    newest_date = next(_max)['trading_date']
    newest_date = dt.datetime.strptime(newest_date, '%Y-%m-%d').date()

    trading_date = og.get_trading_dates_all_option(dt.datetime.now().date(), newest_date + dt.timedelta(days=1))
    try:
        Data_processing(my_mongo, trading_date, implied)
    except ValueError:
        print('today\'s data is not reachable yet')


def get_work(*arg):
    update_mongo_1(True)
    update_mongo_1(False)


if __name__ == '__main__':
    get_work()
