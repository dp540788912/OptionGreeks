from datetime import datetime

from BSmodel import *
import rqdatac
import numpy
import pandas as pd
import math
import datetime as dt
from rqanalysis.risk import get_risk_free_rate

pd.set_option('display.max_columns', None)
rqdatac.init('rice', 'rice', ('dev', 16010))

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


# get parameters
def filter_options(_date, param_list):
    """
    get all options price that is on the market
    :param _date: date
    :param param_list: all option information
    :return: pandas.dataframe
    """

    shrink_ = param_list[param_list['maturity_date'] >= _date]
    shrink_ = shrink_[shrink_['listed_date'] <= _date]
    return shrink_


# init
def get_basic_information() -> pd.DataFrame:
    """
    :return: pandas dataframe, index[ nan ]: [[], [], .... ]
    """
    _partial_param_list = object()
    necessary = ['order_book_id', 'strike_price', 'underlying_order_book_id', 'maturity_date', 'listed_date']
    try:
        _partial_param_list = rqdatac.all_instruments(type='Option')[necessary]
    except ConnectionAbortedError:
        print('connection error')
        exit()
    _partial_param_list['maturity_date'] = _partial_param_list['maturity_date'].apply(
        lambda x: dt.datetime.strptime(x, '%Y-%m-%d').date())
    _partial_param_list['listed_date'] = _partial_param_list['listed_date'].apply(lambda x: dt.datetime.strptime(x, '%Y-%m-%d').date())
    return _partial_param_list


def get_option_price_each_day(_date, all_ids_):
    """
    :param _date: date: str, datetime.datetime, int
    :param all_ids_: list
        list of order book id

    :return: pandas.series
        index = order_book_ids, column = closed price of option
    """
    price_ = rqdatac.get_price(all_ids_, _date, _date, expect_df=True)
    if price_ is not None:
        return price_['close'].reset_index(level=1, drop=True)
    else:
        return None


def get_risk_free_series(_date, order_id):
    """
    :param _date: date
    :param order_id: list of ids
    :return: pandas series, index: option_id, value: risk_free_rate
    """
    rate = get_risk_free_rate(_date, _date)
    return pd.Series(rate, index=order_id)


def get_date2maturity(_partial, _date):
    value_list = map(lambda x: (x - _date).days/365, _partial['maturity_date'].tolist())
    return pd.Series(value_list, index=_partial['order_book_id'].tolist())


def get_dividend(_partial):
    return pd.Series(0, index=_partial['order_book_id'])


def get_underlying_price(_partial, _date):
    under_id_list = _partial['underlying_order_book_id']
    distinct_id = under_id_list.drop_duplicates()
    distinct_price = rqdatac.get_price(distinct_id.tolist(), _date, _date, expect_df=True)
    if distinct_price is None:
        return None
    else:
        distinct_price = distinct_price['close'].reset_index(level=1, drop=True)

    print(distinct_price)
    # [index = underlying id]: [price] series
    # to [ option id ]: [ value ]
    tmp_series = pd.Series(0, index=_partial['order_book_id'].tolist())
    _map = pd.Series(_partial['underlying_order_book_id'], index=_partial['order_book_id'].tolist())
    for n in tmp_series.index:
        tmp_series[n] = distinct_price[map[n]]
    return tmp_series


def get_trading_dates_all_option(partial_param_list_1, end_date):
    """
    :param partial_param_list_1: pandas dataframe
    :param end_date: datetime, the end date
    :return:
    """
    all_listed_date = list(map(lambda x: dt.datetime.strptime(x, '%Y-%m-%d').date(), partial_param_list_1['listed_date']))
    earliest_list_date = min(all_listed_date)
    # get trading date
    trading_dates = rqdatac.get_trading_dates(earliest_list_date, end_date)
    return trading_dates


def get_all_para_ready(_date):

    partial_ = get_basic_information()
    # data frame
    options_on_market_info = filter_options(_date, partial_)

    # get option price
    option_price = get_option_price_each_day(_date, options_on_market_info['order_book_id'].tolist())
    # get risk free rate
    rf_series = get_risk_free_series(_date, partial_['order_book_id'].tolist())
    # get strike_price
    sp_series = pd.Series(partial_['strike_price'], index=partial_['order_book_id'].tolist())
    # get time to maturity
    ttm_series = get_date2maturity(partial_, _date)
    # get dividend

    # get underlying_price


if __name__ == '__main__':
    data = get_basic_information()
    date = dt.datetime(2016, 2, 3).date()
    data = filter_options(date, data)

    print(get_date2maturity(data,date))


