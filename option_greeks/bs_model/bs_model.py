import logging
import numpy as np
import pandas as pd
from .utils import check_cdf
from .algorithm import brent_iteration


ReverseSqrtOf2Pi = 1 / np.sqrt(2 * np.pi)


def get_d1(underlying_price, strike_price, risk_free_rate, dividend_yield, volatility, time_to_maturity):
    """
    PARAMETERS
    ----------
    underlying_price:
    pandas.Series 原生标的价格。index为order_book_id，value为原生标的价格(单位：元）
    strike_price:
    pandas.Series 行权价格。 index为order_book_id, value为行权价格(单位：元）
    risk_free_rate:
    pd.Series 年化无风险利率, index为order_book_id,value为对应年化无风险收益率，比如某只期权剩余1个月到期，则选择一个月无风险收益率计算其implied volatility
    dividend_yield:
    pandas.Series 年化股息收益率。index为order_book_id value为年化股息收益率
    volatility:
    pandas.Series 年化波动率。index为order_book_id value为年化波动率
    time_to_maturity:
    pandas.Series 到期时间。index为order_book_id，value为到期时间。比如某只期权还有90天到期，则time_to_maturity为 90/365
    RETURN
    ----------
    pd.Series index为order_book_id，value为black-scholes定价公式中的d1
    """

    d1 = (np.log(underlying_price / strike_price) +
          (risk_free_rate - dividend_yield + np.power(volatility, 2) * 0.5) * time_to_maturity) / \
         (volatility * np.sqrt(time_to_maturity))

    return d1


def get_delta(underlying_price, strike_price, risk_free_rate, dividend_yield, volatility, time_to_maturity, _type):
    """
    PARAMETERS
    ----------
    underlying_price:
    pandas.Series 原生标的价格。index为order_book_id，value为原生标的价格(单位：元）
    strike_price:
    pandas.Series 行权价格。 index为order_book_id, value为行权价格(单位：元）
    risk_free_rate:
    pd.Series 年化无风险利率, index为order_book_id,value为对应年化无风险收益率，比如某只期权剩余1个月到期，则选择一个月无风险收益率计算其implied volatility
    dividend_yield:
    pandas.Series 年化股息收益率。index为order_book_id value为年化股息收益率
    volatility:
    pandas.Series 年化波动率。index为order_book_id value为年化波动率
    time_to_maturity:
    pandas.Series 到期时间。index为order_book_id，value为到期时间。比如某只期权还有90天到期，则time_to_maturity为 90/365
    RETURN
    ----------
    pd.Series index为order_book_id，value为delta值
    """

    d1 = get_d1(underlying_price, strike_price, risk_free_rate, dividend_yield, volatility, time_to_maturity)

    delta = {}

    for _id in strike_price.index:
        if _type[_id] == 'C':
            delta[_id] = check_cdf(d1[_id]) * np.exp(-dividend_yield[_id] * time_to_maturity[_id])
        else:
            delta[_id] = np.exp(-dividend_yield[_id] * time_to_maturity[_id]) * (check_cdf(d1[_id]) - 1)
    return pd.Series(delta)


def get_gamma(underlying_price, strike_price, risk_free_rate, dividend_yield, volatility, time_to_maturity):
    """
    PARAMETERS
    ----------
    underlying_price:
    pandas.Series 原生标的价格。index为order_book_id，value为原生标的价格(单位：元）
    strike_price:
    pandas.Series 行权价格。 index为order_book_id, value为行权价格(单位：元）
    risk_free_rate:
    pd.Series 年化无风险利率, index为order_book_id,value为对应年化无风险收益率，比如某只期权剩余1个月到期，则选择一个月无风险收益率计算其implied volatility
    dividend_yield:
    pandas.Series 年化股息收益率。index为order_book_id value为年化股息收益率
    volatility:
    pandas.Series 年化波动率。index为order_book_id value为年化波动率
    time_to_maturity:
    pandas.Series 到期时间。index为order_book_id，value为到期时间。比如某只期权还有90天到期，则time_to_maturity为 90/365
    RETURN
    ----------
    pd.Series index为order_book_id，value为gamma值
    """

    d1 = get_d1(underlying_price, strike_price, risk_free_rate, dividend_yield, volatility, time_to_maturity)

    gamma = ReverseSqrtOf2Pi * \
        np.exp(-dividend_yield * time_to_maturity - np.power(d1, 2) * 0.5) / \
        (underlying_price * volatility * np.sqrt(time_to_maturity))

    return gamma


def get_theta(underlying_price, strike_price, risk_free_rate, dividend_yield, volatility, time_to_maturity, _type):
    """
    PARAMETERS
    ----------
    _type: 类型
    underlying_price:
    pandas.Series 原生标的价格。index为order_book_id，value为原生标的价格(单位：元）
    strike_price:
    pandas.Series 行权价格。 index为order_book_id, value为行权价格(单位：元）
    risk_free_rate:
    pd.Series 年化无风险利率, index为order_book_id,value为对应年化无风险收益率，比如某只期权剩余1个月到期，则选择一个月无风险收益率计算其implied volatility
    dividend_yield:
    pandas.Series 年化股息收益率。index为order_book_id value为年化股息收益率
    volatility:
    pandas.Series 年化波动率。index为order_book_id value为年化波动率
    time_to_maturity:
    pandas.Series 到期时间。index为order_book_id，value为到期时间。比如某只期权还有90天到期，则time_to_maturity为 90/365
    RETURN
    ----------
    pd.Series index为order_book_id，value为theta值
    """
    sqrt_time_to_maturity = np.sqrt(time_to_maturity)

    d1 = get_d1(underlying_price, strike_price, risk_free_rate, dividend_yield, volatility, time_to_maturity)
    d2 = d1 - volatility * sqrt_time_to_maturity

    # 根据theta计算公式将其分为三个部分
    part_1 = 0.5 * ReverseSqrtOf2Pi * underlying_price * volatility * \
        np.exp(-dividend_yield * time_to_maturity - np.power(d1, 2) * 0.5) / sqrt_time_to_maturity

    part_2 = risk_free_rate * strike_price * np.exp(-risk_free_rate * time_to_maturity)
    part_3 = dividend_yield * underlying_price * np.exp(-dividend_yield * time_to_maturity)

    theta = {}

    for _id in strike_price.index:
        if _type[_id] == 'C':
            theta[_id] = -part_1[_id] - part_2[_id] * check_cdf(d2[_id]) + part_3[_id] * check_cdf(d1[_id])
        else:
            theta[_id] = -part_1[_id] + part_2[_id] * check_cdf(-d2[_id]) - part_3[_id] * check_cdf(-d1[_id])

    return pd.Series(theta)


def get_vega(underlying_price, strike_price, risk_free_rate, dividend_yield, volatility, time_to_maturity):
    """
    PARAMETERS
    ----------
    underlying_price:
    pandas.Series 原生标的价格。index为order_book_id，value为原生标的价格(单位：元）
    strike_price:
    pandas.Series 行权价格。 index为order_book_id, value为行权价格(单位：元）
    risk_free_rate:
    pd.Series 年化无风险利率, index为order_book_id,value为对应年化无风险收益率，比如某只期权剩余1个月到期，则选择一个月无风险收益率计算其implied volatility
    dividend_yield:
    pandas.Series 年化股息收益率。index为order_book_id value为年化股息收益率
    volatility:
    pandas.Series 年化波动率。index为order_book_id value为年化波动率
    time_to_maturity:
    pandas.Series 到期时间。index为order_book_id，value为到期时间。比如某只期权还有90天到期，则time_to_maturity为 90/365
    RETURN
    ----------
    pd.Series index为order_book_id，value为vega值
    """

    d1 = get_d1(underlying_price, strike_price, risk_free_rate, dividend_yield, volatility, time_to_maturity)

    vega = ReverseSqrtOf2Pi * underlying_price * \
        np.exp(-dividend_yield * time_to_maturity - np.power(d1, 2) * 0.5) * np.sqrt(time_to_maturity)

    return vega


def get_rho(underlying_price, strike_price, risk_free_rate, dividend_yield, volatility, time_to_maturity, _type):
    """
    PARAMETERS
    ----------
    underlying_price:
    pandas.Series 原生标的价格。index为order_book_id，value为原生标的价格(单位：元）
    strike_price:
    pandas.Series 行权价格。 index为order_book_id, value为行权价格(单位：元）
    risk_free_rate:
    pd.Series 年化无风险利率, index为order_book_id,value为对应年化无风险收益率，比如某只期权剩余1个月到期，则选择一个月无风险收益率计算其implied volatility
    dividend_yield:
    pandas.Series 年化股息收益率。index为order_book_id value为年化股息收益率
    volatility:
    pandas.Series 年化波动率。index为order_book_id value为年化波动率
    time_to_maturity:
    pandas.Series 到期时间。index为order_book_id，value为到期时间。比如某只期权还有90天到期，则time_to_maturity为 90/365
    RETURN
    ----------
    pd.Series index为order_book_id，value为theta值
    """

    d1 = get_d1(underlying_price, strike_price, risk_free_rate, dividend_yield, volatility, time_to_maturity)
    d2 = d1 - volatility * np.sqrt(time_to_maturity)

    rho = {}

    for _id in strike_price.index.tolist():
        if _type[_id] == 'C':
            rho[_id] = strike_price[_id] * time_to_maturity[_id] * \
                       np.exp(-risk_free_rate[_id] * time_to_maturity[_id]) * check_cdf(d2[_id])
        else:
            rho[_id] = -strike_price[_id] * time_to_maturity[_id] * \
                       np.exp(-risk_free_rate[_id] * time_to_maturity[_id]) * check_cdf(-d2[_id])
    return pd.Series(rho)


def get_implied_volatility(option_price, underlying_price, strike_price, risk_free_rate, dividend_yield,
                           time_to_maturity, _type, max_iteration=100, tol=1e-7):
    """
    PARAMETERS
    ----------
    option_price:
    pandas.Series 期权价格。index为order_book_id，value为对应期权的实时行情价格（单位：元）
    underlying_price:
    pandas.Series 原生标的价格。index为order_book_id，value为原生标的价格(单位：元）（spot price)
    strike_price:
    pandas.Series 行权价格。 index为order_book_id, value为行权价格(单位：元）
    risk_free_rate:
    pd.Series 年化无风险利率, index为order_book_id,value为对应年化无风险收益率，比如某只期权剩余1个月到期，则选择一个月无风险收益率计算其implied volatility
    dividend_yield:
    pandas.Series 年化股息收益率。index为order_book_id value为年化股息收益率
    time_to_maturity:
    pandas.Series 到期时间。index为order_book_id，value为到期时间。比如某只期权还有90天到期，则time_to_maturity为 90/365
    max_iteration:
    np.int 最大迭代次数
    tol:
    np.float 需要数据精度
    RETURN
    ----------
    pd.Series index为order_book_id，value为隐含波动率
    """
    implied_volatility = {}

    for my_id in option_price.index:
        current_underlying_price = underlying_price[my_id]
        current_strike_price = strike_price[my_id]
        current_dividend = dividend_yield[my_id]
        current_time_to_maturity = time_to_maturity[my_id]
        target_price = option_price[my_id]
        current_risk_free = risk_free_rate[my_id]
        option_type = _type[my_id]

        lower_bound = 1e-4
        upper_bound = 2

        def _target_function(volatility):
            d1 = get_d1(current_underlying_price, current_strike_price, current_risk_free,
                        current_dividend, volatility, current_time_to_maturity)
            d2 = d1 - volatility * np.sqrt(current_time_to_maturity)

            if option_type == 'C':
                return current_underlying_price * np.exp(-current_dividend * current_time_to_maturity) \
                       * check_cdf(d1) - current_strike_price * \
                       np.exp(-current_risk_free * current_time_to_maturity) \
                       * check_cdf(d2) - target_price
            else:
                return current_strike_price * np.exp(-current_risk_free * current_time_to_maturity) \
                       * check_cdf(-d2) - current_underlying_price * \
                       np.exp(-current_dividend * current_time_to_maturity) \
                       * check_cdf(-d1) - target_price

        try:
            implied_volatility[my_id] = brent_iteration(_target_function, lower_bound,
                                                        upper_bound, max_iteration, tol)
        except Exception as e:
            logging.warning(e)
            print(e)

    return pd.Series(implied_volatility)
