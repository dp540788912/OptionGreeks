import rqdatac.validators as valid
from mongo_insert import *
import pandas as pd


def get_greeks(order_book_ids, start_date, end_date, implied_price=True):
    start_date = valid.ensure_date_str(start_date)
    end_date = valid.ensure_date_str(end_date)
    order_book_ids = valid.ensure_order_book_ids(order_book_ids)

    url = 'mongodb://root:root@192.168.10.30:27017/options.py?authSource=admin'
    db = 'option'
    col = 'greeks'

    my_mongo = CustomizedMongo(url, db, col)
    query = {
        '$and':
            [
                {'order_book_id':
                    {
                        '$in': order_book_ids
                    }
                },
                {'trading_date':
                    {
                        '$gte': start_date,
                        '$lte': end_date
                    }
                }
            ]
    }
    result = my_mongo.find(query)
    df = pd.DataFrame(result)
    df = df.set_index(['order_book_id', 'trading_date'], inplace=True)
    print(df)


get_greeks(['10001697', '10001698'], '2019-06-21', '2019-09-20')
