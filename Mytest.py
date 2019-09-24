
from BSmodel_modified.BS_model import *
import rqdatac
import pandas as pd
import datetime as dt
from rqanalysis.risk import get_risk_free_rate
import timeit

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
# def filter_options(_date, param_list):
#     """
#     get all options price that is on the market
#     :param _date: date
#     :param param_list: all option information
#     :return: pandas.dataframe
#     """
#
#     shrink_ = param_list[param_list['de_listed_date'] >= _date]
#     shrink_ = shrink_[shrink_['listed_date'] <= _date]
#     return shrink_


# init
def get_basic_information(_date) -> pd.DataFrame:
    """
    :return: pandas dataframe, index[ nan ]: [[], [], .... ]
    """
    _partial_param_list = object()
    necessary = ['order_book_id', 'strike_price', 'underlying_order_book_id', 'de_listed_date', 'listed_date',
                 'option_type', 'underlying_symbol']
    try:
        _partial_param_list = rqdatac.all_instruments(type='Option', date=_date)[necessary]
    except ConnectionAbortedError:
        print('connection error')
        exit()
    _partial_param_list['de_listed_date'] = _partial_param_list['de_listed_date'].apply(
        lambda x: dt.datetime.strptime(x, '%Y-%m-%d').date())
    _partial_param_list['listed_date'] = _partial_param_list['listed_date'].apply(
        lambda x: dt.datetime.strptime(x, '%Y-%m-%d').date())
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
        return price_['close'].reset_index(level=1, drop=True).rename('option_price')
    else:
        return None


def get_risk_free_series(_date, order_id):
    """
    :param _date: date
    :param order_id: list of ids
    :return: pandas series, index: option_id, value: risk_free_rate
    """
    rate = get_risk_free_rate(_date, _date)
    return pd.Series(rate, index=order_id, name='rf_series')


def get_date2maturity(_partial, _date):
    value_list = map(lambda x: (x - _date).days / 365, _partial['de_listed_date'].tolist())
    return pd.Series(value_list, index=_partial['order_book_id'].tolist(), name='ttm_series')


def get_dividend(_partial):
    return pd.Series(0, index=_partial['order_book_id'].tolist(), name='dd_series')


def get_type(_partial):
    return pd.Series(_partial['option_type'].tolist(), _partial['order_book_id'].tolist(), name='type_series')


def get_underlying_price(_partial, _date):
    under_id_list = _partial['underlying_order_book_id']
    distinct_id = under_id_list.drop_duplicates()
    distinct_price = rqdatac.get_price(distinct_id.tolist(), _date, _date, expect_df=True)
    if distinct_price is None:
        return None
    else:
        distinct_price = distinct_price['close'].reset_index(level=1, drop=True)
    # [index = underlying id]: [price] series
    # to [ option id ]: [ value ]
    tmp_series = pd.Series(0.0, index=_partial['order_book_id'].tolist(), name='udp_series')
    _map = pd.Series(_partial['underlying_order_book_id'].tolist(), index=_partial['order_book_id'].tolist())

    for n in tmp_series.index:
        tmp_series[n] = distinct_price[_map[n]]
    return tmp_series


def get_trading_dates_all_option(partial_param_list_1, end_date):
    """
    :param partial_param_list_1: pandas dataframe
    :param end_date: datetime, the end date
    :return:
    """
    all_listed_date = list(
        map(lambda x: dt.datetime.strptime(x, '%Y-%m-%d').date(), partial_param_list_1['listed_date']))
    earliest_list_date = min(all_listed_date)
    # get trading date
    trading_dates = rqdatac.get_trading_dates(earliest_list_date, end_date)
    return trading_dates


def get_all_para_ready(options_on_market_info, _date):
    # get option price
    option_price = get_option_price_each_day(_date, options_on_market_info['order_book_id'].tolist())
    # get risk free rate
    rf_series = get_risk_free_series(_date, options_on_market_info['order_book_id'].tolist())
    # get strike_price
    sp_series = pd.Series(options_on_market_info['strike_price'].tolist(),
                          index=options_on_market_info['order_book_id'].tolist(), name='sp_series')
    # get time to maturity
    ttm_series = get_date2maturity(options_on_market_info, _date)
    # get dividend
    dd_series = get_dividend(options_on_market_info)
    # get underlying_price
    udp_series = get_underlying_price(options_on_market_info, _date)
    # get type series
    type_series = get_type(options_on_market_info)
    # merge
    merge_data = pd.concat([option_price, udp_series, sp_series, rf_series, dd_series, ttm_series, type_series], axis=1)
    names = merge_data.columns.values.tolist()
    para = [merge_data[x] for x in names]
    # get volatility
    vol_series = get_implied_volatility(*para)
    """
    Get Greeks 
    """
    delta = get_delta(udp_series, sp_series, rf_series, dd_series, vol_series, ttm_series, type_series).rename('delta')
    gamma = get_gamma(udp_series, sp_series, rf_series, dd_series, vol_series, ttm_series).rename('gamma')
    theta = get_theta(udp_series, sp_series, rf_series, dd_series, vol_series, ttm_series, type_series).rename('theta')
    vega = get_vega(udp_series, sp_series, rf_series, dd_series, vol_series, ttm_series).rename('vega')
    rho = get_rho(udp_series, sp_series, rf_series, dd_series, vol_series, ttm_series, type_series).rename('rho')

    pd_data = pd.concat([delta, gamma, theta, vega, rho], axis=1)
    # multi-index
    date_array = [_date for x in range(len(option_price.index))]
    mul_index = pd.MultiIndex.from_arrays([pd_data.index.tolist(), date_array], names=('order_book_id', 'date'))

    pd_data.index = mul_index
    return pd_data


def get_greeks(_date, sc_only=True):
    """
    get the greeks value of all the options on the market
    :param sc_only: True only check common stock option
    :param _date: a specific date
    :return: a data frame: index[ id, date ] : columns[delta, gamma, theta, vega, rho]
    """
    all_data = get_basic_information(_date)
    if sc_only:
        all_data = all_data[all_data['underlying_symbol'] == '510050.XSHG']
    return get_all_para_ready(all_data, _date)


def check_runtime(_func):
    def decorator(*args, **kwargs):
        start = timeit.default_timer()
        _func()
        stop = timeit.default_timer()
        print('Time: ', stop - start)
    return decorator


@ check_runtime
def test_func():
    q_date = dt.datetime(2019, 9, 23).date()
    print(get_greeks(q_date))








