# -*- coding: utf-8 -*-
import rqdatac
import datetime as dt
from rqanalysis.risk import get_risk_free_rate
import warnings
from .toolkit import cal_risk_free_for_underlying_id
from .bs_model import *
import timeit
_FILTER_MAP = 'C|SR|RU|M|CU|510050.XSHG|CF'
_REQUEST_ATTR = ['order_book_id', 'strike_price', 'underlying_order_book_id', 'de_listed_date', 'listed_date',
                 'option_type', 'underlying_symbol']
"""
    According to closed price, calculate implied volatility, and greeks(delta, gamma, vega, theta, rho) of all the
    options from listed date to current date in the specified market
    Parameters needed for calculation:
    underlying price, strike price, option price, risk free rate, dividend yield, time to maturity
"""


def get_basic_information(_date) -> pd.DataFrame:
    """
    :return: pandas dataframe, index[ nan ]: [[], [], .... ]
    """
    try:
        _origin_data = rqdatac.all_instruments(type='Option', date=_date)[_REQUEST_ATTR]
    except ConnectionAbortedError:
        raise ConnectionAbortedError('Connection error happens')
    _origin_data['de_listed_date'] = _origin_data['de_listed_date'].apply(lambda x: dt.datetime.strptime(x, '%Y-%m-%d'))
    _origin_data = _origin_data[_origin_data['de_listed_date'] > _date]
    _origin_data['listed_date'] = _origin_data['listed_date'].apply(lambda x: dt.datetime.strptime(x, '%Y-%m-%d'))
    _origin_data = _origin_data[_origin_data['underlying_order_book_id'].str.contains(_FILTER_MAP)]
    return _origin_data


def get_option_price_each_day(_date, all_ids_) -> pd.Series:
    price_ = rqdatac.get_price(all_ids_, _date, _date, expect_df=True)
    if price_ is not None:
        price_ = price_['close'].reset_index(level=1, drop=True).rename('option_price')
        msg = 'Option price data missing'
        check_if_missing_items(price_.index.tolist(), all_ids_, msg)
        return price_
    else:
        return pd.Series()


def check_if_missing_items(new_array, ori_array, msg):
    remained = list(set(ori_array) - set(new_array))
    if not remained:
        return remained
    else:
        warnings.warn("{} {}".format(remained, msg))


def get_risk_free_series(_date, order_id) -> pd.Series:
    rate = []
    try:
        rate = get_risk_free_rate(_date, _date)
    except TypeError:
        warnings.warn('{} risk free rate data is not available'.format(_date))
    return pd.Series(rate, index=order_id, name='rf_series')


def get_date2maturity(_partial, _date) -> pd.Series:
    value_list = map(lambda x: (x - _date).days / 365, _partial['de_listed_date'].tolist())
    return pd.Series(value_list, index=_partial['order_book_id'].tolist(), name='ttm_series')


def get_dividend(_ids) -> pd.Series:
    return pd.Series(0, index=_ids, name='dd_series')


def get_type(_partial) -> pd.Series:
    return pd.Series(_partial['option_type'].tolist(), index=_partial['order_book_id'].tolist(), name='type_series')


def get_underlying_price(_partial, _date) -> (pd.Series, pd.Series):
    under_id_list = _partial['underlying_order_book_id']
    distinct_id = under_id_list.drop_duplicates()
    distinct_price = rqdatac.get_price(distinct_id.tolist(), _date, _date, expect_df=True)
    if distinct_price is None:
        raise ValueError("{} is not a trading date".format(_date))
    else:
        distinct_price = distinct_price['close'].reset_index(level=1, drop=True)
        msg = 'Underlying price missing in date {}'.format(_date)
        check_if_missing_items(distinct_price.index.tolist(), distinct_id, msg)

    tmp_series = pd.Series(under_id_list.tolist(), index=_partial['order_book_id'].tolist(), name='udp_series')
    return pd.merge(tmp_series, distinct_price, left_on='udp_series', right_index=True)['close'].rename('udp_series'), distinct_price


def get_trading_dates_all_option(end_date, start_date=None) -> list:
    """
    :param start_date: define start date yourself
    :param end_date: datetime, the end date
    :return: list if trading dates
    """
    if start_date is None:
        _ori_date = rqdatac.all_instruments(type='Option')
        all_listed_date = _ori_date['listed_date'].apply(lambda x: dt.datetime.strptime(x, '%Y-%m-%d')).tolist()
        earliest_list_date = min(all_listed_date)
    else:
        earliest_list_date = start_date
    if end_date < earliest_list_date:
        return []

    # get trading date
    trading_dates = rqdatac.get_trading_dates(earliest_list_date, end_date)
    return trading_dates


def get_forward_risk_rate(_data, distinct_price, strike_price, option_type, time_to_maturity, option_price,
                          underlying_price):
    distinct_underlying_id = _data['underlying_order_book_id'].unique().tolist()
    forward_risk_free_series = pd.Series(index=_data['order_book_id'])

    for _id in distinct_underlying_id:
        tmp_rf = cal_risk_free_for_underlying_id(_id, _data, distinct_price, strike_price, option_type,
                                                 time_to_maturity, option_price, underlying_price)
        forward_risk_free_series[tmp_rf.index.tolist()] = tmp_rf.tolist()

    return forward_risk_free_series


def get_all_para_ready(options_on_market_info, _date, implied_price=False):
    if options_on_market_info is None or options_on_market_info.empty:
        return None
    id_list = options_on_market_info['order_book_id'].tolist()
    option_price = get_option_price_each_day(_date, id_list)
    sp_series = pd.Series(options_on_market_info['strike_price'].tolist(), index=id_list, name='sp_series')
    ttm_series = get_date2maturity(options_on_market_info, _date)
    dd_series = get_dividend(id_list)
    try:
        udp_series, distinct_price = get_underlying_price(options_on_market_info, _date)
    except AttributeError:
        raise AttributeError('{} data is missing, perhaps it\'s not a trading date')

    type_series = get_type(options_on_market_info)
    if implied_price:
        rf_series = get_forward_risk_rate(options_on_market_info, distinct_price, sp_series, type_series, ttm_series,
                                          option_price, udp_series)
    else:
        rf_series = get_risk_free_series(_date, id_list)
    para = [option_price, udp_series, sp_series, rf_series, dd_series, ttm_series, type_series]

    # Calculate Geeks
    vol_series = get_implied_volatility(*para).rename('iv')
    args = [udp_series, sp_series, rf_series, dd_series, vol_series, ttm_series]
    delta = get_delta(*args, type_series).rename('delta')
    gamma = get_gamma(*args).rename('gamma')
    theta = get_theta(*args, type_series).rename('theta')
    vega = get_vega(*args).rename('vega')
    rho = get_rho(*args, type_series).rename('rho')
    _col = ['iv', 'delta', 'gamma', 'theta', ]
    pd_data = pd.concat([vol_series, delta, gamma, theta, vega, rho], axis=1, sort=True)

    # multi-index
    date_array = [_date for _ in range(len(pd_data.index))]
    mul_index = pd.MultiIndex.from_arrays([pd_data.index.tolist(), date_array], names=('order_book_id', 'trading_date'))
    pd_data.index = mul_index
    return pd_data


def get_greeks(_date, ids=None, sc_only='true', implied_price=False):
    """
    get the greeks value of all the options.py on the market
    :param ids: id list or str, default None(return all available data)
    :param implied_price: indicator
    :param sc_only: True: only check common stock options.py, false: all the options.py
    :param _date: a specific date
    :return: a data frame: index[ id, date ] : columns[delta, gamma, theta, vega, rho]
    """
    all_data = get_basic_information(_date)
    if sc_only == 'true':
        all_data = all_data[all_data['underlying_symbol'] == '510050.XSHG']
    elif sc_only == 'false':
        all_data = all_data[all_data['underlying_symbol'] != '510050.XSHG']

    if ids is None:
        return get_all_para_ready(all_data, _date, implied_price)
    else:
        return get_all_para_ready(all_data, _date, implied_price).loc[ids]


def check_runtime(_func):
    def decorator(*args, **kwargs):
        start = timeit.default_timer()
        _func(*args, **kwargs)
        stop = timeit.default_timer()
        print('Time: ', stop - start)
    return decorator

