
import pymongo
import pandas as pd
import datetime as dt
import option_greeks as og
import rqdatac


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
        return True

    def drop(self):
        self._col.drop()

    def find(self, query):
        return self._col.find(query)

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

    if drop == 1:
        my_mongo.drop()
    else:
        for date in trading_date:
            length -= 1
            data = og.get_greeks(date, sc_only=False, implied_price=False)
            my_mongo.insert(data)
            print(date, ": finished", 'job left: ', length)
    my_mongo.close()


if __name__ == '__main__':
    initial_data()


