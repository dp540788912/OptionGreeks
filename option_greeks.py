
from BSmodel_modified.BS_model import *
from BSmodel_modified.toolkit import *
import rqdatac
import pandas as pd
import datetime as dt
from rqanalysis.risk import get_risk_free_rate
import timeit

rqdatac.init('rice', 'rice', ('dev', 16010))
filter_tmp = 'C|SR|RU|M|CU|510050.XSHG|CF'
pd.set_option('display.max_columns', 500)

"""
    According to closed price, calculate implied volatility, and greeks(delta, gamma, vega, theta, rho) of all the
    options.py from listed date to current date in the specified market
    Parameters needed for calculation:
    underlying price, strike price, options.py price, risk free rate, dividend yield, time to maturity
"""


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
    _partial_param_list = _partial_param_list[_partial_param_list['de_listed_date'] > _date]
    _partial_param_list['listed_date'] = _partial_param_list['listed_date'].apply(
        lambda x: dt.datetime.strptime(x, '%Y-%m-%d').date())
    global filter_tmp
    _partial_param_list = _partial_param_list[_partial_param_list['underlying_order_book_id'].str.contains(filter_tmp)]
    return _partial_param_list


def get_option_price_each_day(_date, all_ids_) -> pd.Series:
    """
    :param _date: date: str, datetime.datetime, int
    :param all_ids_: list
        list of order book id

    :return: pandas.series
        index = order_book_ids, column = closed price of options.py
    """

    price_ = rqdatac.get_price(all_ids_, _date, _date, expect_df=True)
    if price_ is not None:
        return price_['close'].reset_index(level=1, drop=True).rename('option_price')
    else:
        return pd.Series(None)


def get_risk_free_series(_date, order_id) -> pd.Series:
    """
    :param _date: date
    :param order_id: list of ids
    :return: pandas series, index: option_id, value: risk_free_rate
    """
    rate = get_risk_free_rate(_date, _date)
    return pd.Series(rate, index=order_id, name='rf_series')


def get_date2maturity(_partial, _date) -> pd.Series:
    """
    :param _partial: DataFrame
    :param _date: exact date
    :return: pands Series
    """
    value_list = map(lambda x: (x - _date).days / 365, _partial['de_listed_date'].tolist())
    return pd.Series(value_list, index=_partial['order_book_id'].tolist(), name='ttm_series')


def get_dividend(_partial) -> pd.Series:
    return pd.Series(0, index=_partial['order_book_id'].tolist(), name='dd_series')


def get_type(_partial) -> pd.Series:
    return pd.Series(_partial['option_type'].tolist(), _partial['order_book_id'].tolist(), name='type_series')


def get_underlying_price(_partial, _date) -> (pd.Series, pd.Series):
    """
    :param _partial: DataFrame
    :param _date: exact date
    :return: pands Series
    """
    under_id_list = _partial['underlying_order_book_id']
    distinct_id = under_id_list.drop_duplicates()
    distinct_price = rqdatac.get_price(distinct_id.tolist(), _date, _date, expect_df=True)
    if distinct_price is None:
        raise Exception("the date is not a trading date")
    else:
        distinct_price = distinct_price['close'].reset_index(level=1, drop=True)
    # [index = underlying id]: [price] series
    # to [ options.py id ]: [ value ]
    tmp_series = pd.Series(0.0, index=_partial['order_book_id'].tolist(), name='udp_series')
    _map = pd.Series(_partial['underlying_order_book_id'].tolist(), index=_partial['order_book_id'].tolist())

    for n in tmp_series.index:
        tmp_series[n] = distinct_price[_map[n]]
    return tmp_series, distinct_price


def get_trading_dates_all_option(end_date, start_date=None) -> list:
    """
    :param start_date: define start date yourself
    :param end_date: datetime, the end date
    :return:
    """
    if start_date is None:
        partial_param_list_1 = rqdatac.all_instruments(type='Option')
        all_listed_date = partial_param_list_1['listed_date'].apply(
            lambda x: dt.datetime.strptime(x, '%Y-%m-%d').date()).tolist()
        earliest_list_date = min(all_listed_date)
    else:
        earliest_list_date = start_date
    # get trading date
    trading_dates = rqdatac.get_trading_dates(earliest_list_date, end_date)
    return trading_dates


def get_forward_risk_rate(_data, distinct_price, strike_price, option_type, time_to_maturity, option_price, underlying_price):
    distinct_underlying_id = _data['underlying_order_book_id'].unique().tolist()
    forward_risk_free_series = pd.Series(index=_data['order_book_id'])

    for _id in distinct_underlying_id:
        tmp_rf = cal_risk_free_for_underlying_id(_id, _data, distinct_price, strike_price, option_type, time_to_maturity, option_price, underlying_price)
        forward_risk_free_series.loc[tmp_rf.index.tolist()] = tmp_rf.tolist()

    return forward_risk_free_series


def get_all_para_ready(options_on_market_info, _date, implied_price=False):
    """
    :param implied_price: indicator
    :param options_on_market_info: DataFrame, options.py on market
    :param _date: exact_date
    :return: dataFrame , all the greeks
    """
    if options_on_market_info.empty:
        return None
    # Get components needed for calculation
    # get options.py price
    option_price = get_option_price_each_day(_date, options_on_market_info['order_book_id'].tolist())
    # get risk free rate
    # get strike_price
    sp_series = pd.Series(options_on_market_info['strike_price'].tolist(),
                          index=options_on_market_info['order_book_id'].tolist(), name='sp_series')
    # get time to maturity
    ttm_series = get_date2maturity(options_on_market_info, _date)
    # get dividend
    dd_series = get_dividend(options_on_market_info)
    # get underlying_price
    try:
        udp_series, distinct_price = get_underlying_price(options_on_market_info, _date)
    except AttributeError:
        raise AttributeError('can\'t get information on that day, please retry')
    # get type series
    type_series = get_type(options_on_market_info)

    if implied_price:
        rf_series = get_forward_risk_rate(options_on_market_info, distinct_price, sp_series, type_series, ttm_series, option_price, udp_series)
    else:
        rf_series = get_risk_free_series(_date, options_on_market_info['order_book_id'].tolist())

    # merge
    merge_data = pd.concat([option_price, udp_series, sp_series, rf_series, dd_series, ttm_series, type_series], axis=1)
    names = merge_data.columns.values.tolist()
    para = [merge_data[x] for x in names]
    # get volatility
    vol_series = get_implied_volatility(*para)
    # Calculate Geeks
    delta = get_delta(udp_series, sp_series, rf_series, dd_series, vol_series, ttm_series, type_series).rename('delta')
    gamma = get_gamma(udp_series, sp_series, rf_series, dd_series, vol_series, ttm_series).rename('gamma')
    theta = get_theta(udp_series, sp_series, rf_series, dd_series, vol_series, ttm_series, type_series).rename('theta')
    vega = get_vega(udp_series, sp_series, rf_series, dd_series, vol_series, ttm_series).rename('vega')
    rho = get_rho(udp_series, sp_series, rf_series, dd_series, vol_series, ttm_series, type_series).rename('rho')
    # Merge
    pd_data = pd.concat([delta, gamma, theta, vega, rho], axis=1)
    # multi-index
    date_array = [_date for x in range(len(pd_data.index))]
    mul_index = pd.MultiIndex.from_arrays([pd_data.index.tolist(), date_array], names=('order_book_id', 'trading_date'))
    # set index
    pd_data.index = mul_index
    return pd_data


def get_greeks(_date, sc_only=True, implied_price=False):
    """
    get the greeks value of all the options.py on the market
    :param implied_price: indicator
    :param sc_only: True: only check common stock options.py, false: all the options.py
    :param _date: a specific date
    :return: a data frame: index[ id, date ] : columns[delta, gamma, theta, vega, rho]
    """
    all_data = get_basic_information(_date)
    if sc_only:
        all_data = all_data[all_data['underlying_symbol'] == '510050.XSHG']
    else:
        all_data = all_data[all_data['underlying_symbol'] != '510050.XSHG']
    return get_all_para_ready(all_data, _date, implied_price)


def check_runtime(_func):
    """
    Decorator to calculate the time needed
    :param _func:
    :return:
    """
    def decorator(*args, **kwargs):
        start = timeit.default_timer()
        _func()
        stop = timeit.default_timer()
        print('Time: ', stop - start)
    return decorator


@ check_runtime
def test_func():
    q_date = dt.datetime(2019, 9, 26).date()
    print(get_greeks(q_date, sc_only=True, implied_price=True))


# test_func()





