import numpy as np
import pandas as pd
from datetime import datetime
from datetime import timedelta
from scipy.stats import norm
import time
from root_finding_algorithms import *
import rqdatac

rqdatac.init('quant', 'quant123', ('172.18.0.17', 16010))


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

    d1 = (np.log(underlying_price / strike_price) + (risk_free_rate - dividend_yield + pow(volatility,2) / 2) * time_to_maturity) / (volatility * np.sqrt(time_to_maturity))

    return d1


def get_delta(underlying_price, strike_price, risk_free_rate, dividend_yield, volatility, time_to_maturity):
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

    d1 = get_d1(underlying_price,strike_price,risk_free_rate,dividend_yield,volatility,time_to_maturity)

    delta = pd.Series(index=strike_price.index)

    for id in strike_price.index.tolist():
        if rqdatac.instruments(id).option_type == 'C':
            delta.loc[id] = norm.cdf(d1.loc[id]) * np.exp(-dividend_yield.loc[id] * time_to_maturity.loc[id])
        else:
            delta.loc[id]  = np.exp(-dividend_yield.loc[id] * time_to_maturity.loc[id]) * (norm.cdf(d1.loc[id]) - 1)
    return delta


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

    d1 = get_d1(underlying_price,strike_price,risk_free_rate,dividend_yield,volatility,time_to_maturity)

    gamma = np.exp(-dividend_yield * time_to_maturity - pow(d1, 2) / 2) / (underlying_price * volatility * np.sqrt(2 * np.pi * time_to_maturity))

    return gamma


def get_theta(underlying_price, strike_price, risk_free_rate, dividend_yield, volatility, time_to_maturity):
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

    d1 = get_d1(underlying_price,strike_price,risk_free_rate,dividend_yield,volatility,time_to_maturity)
    d2 = d1 - volatility * np.sqrt(time_to_maturity)

    # 根据theta计算公式将其分为三个部分
    part_1 = underlying_price * volatility * np.exp(-dividend_yield * time_to_maturity) * np.exp(-pow(d1,2) / 2) / (2 * np.sqrt(2 * time_to_maturity * np.pi))
    part_2 = risk_free_rate * strike_price * np.exp(-risk_free_rate * time_to_maturity)
    part_3 = dividend_yield * underlying_price * np.exp(-dividend_yield * time_to_maturity)

    theta = pd.Series(index=strike_price.index)

    for id in strike_price.index.tolist():
        if rqdatac.instruments(id).option_type == 'C':
            theta.loc[id] = -part_1.loc[id] - part_2.loc[id] * norm.cdf(d2.loc[id]) + part_3.loc[id] * norm.cdf(d1.loc[id])
        else:
            theta.loc[id] = -part_1.loc[id] + part_2.loc[id] * norm.cdf(-d2.loc[id]) - part_3.loc[id] * norm.cdf(-d1.loc[id])

    return theta


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

    d1 = get_d1(underlying_price,strike_price,risk_free_rate,dividend_yield,volatility,time_to_maturity)

    vega = underlying_price * np.exp(-dividend_yield * time_to_maturity) * np.sqrt(time_to_maturity) * np.exp(-pow(d1, 2) / 2) / np.sqrt(2 * np.pi)

    return vega


def get_rho(underlying_price, strike_price, risk_free_rate, dividend_yield, volatility, time_to_maturity):
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

    d1 = get_d1(underlying_price,strike_price,risk_free_rate,dividend_yield,volatility,time_to_maturity)
    d2 = d1 - volatility * np.sqrt(time_to_maturity)

    rho = pd.Series(index=strike_price.index)

    for id in strike_price.index.tolist():
        if rqdatac.instruments(id).option_type == 'C':
            rho.loc[id] = strike_price.loc[id] * time_to_maturity.loc[id] * np.exp(-risk_free_rate.loc[id] * time_to_maturity.loc[id]) * norm.cdf(d2.loc[id])
        else:
            rho.loc[id] = -strike_price.loc[id] * time_to_maturity.loc[id] * np.exp(-risk_free_rate.loc[id] * time_to_maturity.loc[id]) * norm.cdf(-d2.loc[id])

    return rho


def get_implied_volatility(option_price, underlying_price, strike_price, risk_free_rate, dividend_yield, time_to_maturity, max_iteration=100, tol=1e-7):

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
    implied_volatility = pd.Series(index=option_price.index)
    brent_status = pd.Series(index=option_price.index)

    for id in option_price.index.tolist():
        current_underlying_price = underlying_price.loc[id]
        current_strike_price = strike_price.loc[id]
        current_dividend = dividend_yield.loc[id]
        current_time_to_maturity = time_to_maturity.loc[id]
        target_price = option_price.loc[id]
        current_risk_free = risk_free_rate.loc[id]
        option_type = rqdatac.instruments(id).option_type

        lower_bound = 0
        upper_bound = 2

        def _target_function(volatility):
            d1 = get_d1(current_underlying_price, current_strike_price, current_risk_free, current_dividend, volatility, current_time_to_maturity)
            d2 = d1 - volatility * np.sqrt(current_time_to_maturity)

            if option_type == 'C':
                return current_underlying_price * np.exp(-current_dividend * current_time_to_maturity) * norm.cdf(d1) - current_strike_price * np.exp(-current_risk_free * current_time_to_maturity) * norm.cdf(d2) - target_price
            else:
                return current_strike_price * np.exp(-current_risk_free * current_time_to_maturity) * norm.cdf(-d2) - current_underlying_price * np.exp(-current_dividend * current_time_to_maturity) * norm.cdf(-d1) - target_price

        # def _derivative_function(volatility):
        #     d1 = get_d1(current_underlying_price, current_strike_price, current_risk_free, current_dividend, volatility, current_time_to_maturity)
        #     return current_underlying_price * np.exp(-current_dividend * current_time_to_maturity) * np.sqrt(current_time_to_maturity) * np.exp(-pow(d1, 2) / 2) / np.sqrt(2 * np.pi)

        implied_volatility.loc[id], brent_status.loc[id] = brent_iteration(_target_function, lower_bound, upper_bound, max_iteration, tol)

    return implied_volatility, brent_status
