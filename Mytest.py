from datetime import datetime

from BSmodel import *
import rqdatac
import numpy
import pandas
import math
import datetime as dt
pandas.set_option('display.max_columns', None)


"""
    According to closed price, calculate implied volatility, and greeks(delta, gamma, vega, theta, rho) of all the
    options from listed date to current date in the specified market

    Parameters needed for calculation:
    underlying price, strike price, option price, risk free rate, dividend yield, time to maturity

    api needed:
    instruments(order_book_id, market)
    :return (order_book_id, symbol, round_lot, listed_date, type, contract_multiplier, underlying_order_book_id,
            uderlying_symbol, mature_date, )


    :return: True if all the jobs done
"""

# init
rqdatac.init('rice', 'rice', ('192.168.10.34', 16012))
# test

ins = object()
try:
    ins = rqdatac.all_instruments(type='Option')
except ConnectionAbortedError:
    print('connection error')
    exit()


# get parameters
# get dates
all_ids = ins['order_book_id']
all_listed_date = list(map(lambda x: dt.datetime.strptime(x, '%Y-%m-%d').date(), ins['listed_date']))
earliest_list_date = min(all_listed_date)
print(earliest_list_date)

# get trading date
trading_dates = rqdatac.get_trading_dates(earliest_list_date, dt.datetime.now().date())

# test for option
print(rqdatac.get_price(all_ids[0], earliest_list_date, datetime.now().date()))
