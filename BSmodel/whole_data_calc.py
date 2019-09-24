import pickle
from BSmodel.BS_model import *
from BSmodel.toolkit import *
import rqdatac

rqdatac.init('rice', 'rice', ('192.168.0.241', 16010))


# 计算某一天的50ETF期权区全量数据
def calc_daily_vol_greeks(date, underlying_id, option_id):
    """
    PARAMETERS
    ----------
    date: str，当前分析日期

    underlying_id: str，期权的标的代码

    option_id: list，当前存续期权的id

    RETURN
    ---------
    data_with_greek：pd.DataFrame, index为期权id，columns是期权信息包括标的价格，行权价，期权状态、类型、隐含波动率和期权对应的希腊值等
    root_finding_status：pd.DataFrame，index为期权id，columns是三种计算方式的耗时以及状态
    """

    underlying_price = rqdatac.get_price(underlying_id, date, date, '1d', 'close', adjust_type='none').loc[date]

    underlying_price = pd.Series(index=option_id, data=underlying_price)

    # 取出可交易期权的期权价格和strike price
    option_panel = rqdatac.get_price(option_id, date, date, fields=['close', 'strike_price'])

    option_price = option_panel['close'].loc[date]

    if underlying_id == '510050.XSHG':
        strike_price = option_panel['strike_price'].loc[date]
    else:
        strike_price = pd.Series(data=[rqdatac.instruments(id).strike_price for id in option_id], index=option_id)

    time_to_maturity = calc_time_to_maturity(option_id, date)
    risk_free_rate = apply_risk_free_rate(option_id, date)

    dividend_yield = pd.Series(data=0, index=option_id)

    # 判断当前可交易option的状态以及期权的类型
    # 期权状态包括当日到期的期权，因此期权状态需要取子集
    if underlying_id == '510050.XSHG':
        option_status = stock_options_status(date, underlying_id).loc[option_id]
    elif 'SR' in underlying_id:
        option_status = sr_options_status(date, underlying_id).loc[option_id]
    elif 'M' in underlying_id:
        option_status = m_options_status(date, underlying_id).loc[option_id]
    elif 'CU' in underlying_id:
        option_status = cu_options_status(date, underlying_id).loc[option_id]
    else:
        raise AttributeError('underlying id is invalid')

    option_types = pd.Series(data=[rqdatac.instruments(id).option_type for id in option_status.index.tolist()],index=option_status.index.tolist())

    # 三种求根方式计算implied volatility

    implied_volatility, brent_status = get_implied_volatility(
        option_price, underlying_price, strike_price, risk_free_rate, dividend_yield, time_to_maturity)

    processed_implied_volatility = processing_implied_volatility(implied_volatility, strike_price, time_to_maturity, option_types)
    # 计算Greeks
    delta = get_delta(underlying_price, strike_price, risk_free_rate, dividend_yield, processed_implied_volatility, time_to_maturity)

    gamma = get_gamma(underlying_price, strike_price, risk_free_rate, dividend_yield, processed_implied_volatility, time_to_maturity)

    theta = get_theta(underlying_price, strike_price, risk_free_rate, dividend_yield, processed_implied_volatility, time_to_maturity)

    vega = get_vega(underlying_price, strike_price, risk_free_rate, dividend_yield, processed_implied_volatility, time_to_maturity)

    rho = get_rho(underlying_price, strike_price, risk_free_rate, dividend_yield, processed_implied_volatility, time_to_maturity)

    data_with_greek = pd.concat([underlying_price, option_price, strike_price, risk_free_rate, dividend_yield, time_to_maturity, option_status, option_types, implied_volatility, delta, gamma, theta, vega, rho], axis=1)
    data_with_greek.columns = ['underlying_price', 'option_price', 'strike_price', 'risk_free_rate',
                               'dividend_yield', 'time_to_maturity', 'option_status', 'option_type',
                               'implied_vol', 'delta', 'gamma','theta', 'vega', 'rho']

    return data_with_greek


def calc_daily_forward_vol_greeks(date, underlying_id, option_id, calc_number):
    """
    PARAMETERS
    ----------
    date: str，当前分析日期

    underlying_id: str，期权的标的代码

    option_id: list，当前存续期权的id

    calc_number: int,计算隐含远期价格时需要的期权数目，例如 calc_number=3，意味着选择距离ATM期权最近的三只OTM和三只ITM期权计算其隐含远期价格

    RETURN
    ---------
    data_with_greek：pd.DataFrame, index为期权id，columns是期权信息包括标的价格，行权价，期权状态、类型、隐含波动率和期权对应的希腊值等
    root_finding_status：pd.DataFrame，index为期权id，columns是三种计算方式的耗时以及状态
    """


    underlying_price = rqdatac.get_price(underlying_id, date, date, '1d', 'close', adjust_type='none').loc[date]

    underlying_price = pd.Series(index=option_id, data=underlying_price)

    # 取出可交易期权的期权价格和strike price
    option_panel = rqdatac.get_price(option_id, date, date, fields=['close', 'strike_price'])

    option_price = option_panel['close'].loc[date]

    if underlying_id == '510050.XSHG':
        strike_price = option_panel['strike_price'].loc[date]
    else:
        strike_price = pd.Series(data=[rqdatac.instruments(id).strike_price for id in option_id], index=option_id)

    time_to_maturity = calc_time_to_maturity(option_id, date)

    dividend_yield = pd.Series(data=0,index=option_id)

    # 判断当前可交易option的状态以及期权的类型
    if underlying_id == '510050.XSHG':
        option_status = stock_options_status(date, underlying_id).loc[option_id]
    elif 'SR' in underlying_id:
        option_status = sr_options_status(date, underlying_id).loc[option_id]
    elif 'M' in underlying_id:
        option_status = m_options_status(date, underlying_id).loc[option_id]
    elif 'CU' in underlying_id:
        option_status = cu_options_status(date, underlying_id).loc[option_id]
    else:
        raise AttributeError('underlying id is invalid')

    option_types = pd.Series(data=[rqdatac.instruments(id).option_type for id in option_status.index.tolist()],index=option_status.index.tolist())

    # 根据不同的time_to_maturity计算对应的implied forward price
    option_data = pd.concat([time_to_maturity, strike_price, option_status, option_types], axis=1)
    option_data.columns = ['time_to_maturity', 'strike_price', 'option_status', 'option_type']

    total_time_to_maturity = time_to_maturity.unique()
    implied_forward = pd.Series(index=option_id)
    implied_risk_free = pd.Series(index=option_id)

    for period in total_time_to_maturity:
        selected_options, selected_call_option, selected_put_option = select_option(option_data, period, calc_number)

        current_time_to_maturity_contracts = time_to_maturity[time_to_maturity == period].index.tolist()
        #计算当前期限期权远期价格
        implied_forward.loc[current_time_to_maturity_contracts],implied_risk_free.loc[current_time_to_maturity_contracts] = calc_implied_forward_and_risk_free(selected_options, option_price, strike_price,underlying_price,period)

    # 三种求根方式计算implied volatility

    implied_volatility, brent_status = get_implied_volatility(option_price,underlying_price,strike_price,implied_risk_free,dividend_yield,time_to_maturity)

    processed_implied_volatility = processing_implied_volatility(implied_volatility, strike_price, time_to_maturity, option_types)
    # 计算Greeks

    delta = get_delta(underlying_price, strike_price, implied_risk_free, dividend_yield, processed_implied_volatility, time_to_maturity)

    gamma = get_gamma(underlying_price, strike_price, implied_risk_free, dividend_yield, processed_implied_volatility, time_to_maturity)

    theta = get_theta(underlying_price, strike_price, implied_risk_free, dividend_yield, processed_implied_volatility, time_to_maturity)

    vega = get_vega(underlying_price, strike_price, implied_risk_free, dividend_yield, processed_implied_volatility, time_to_maturity)

    rho = get_rho(underlying_price, strike_price, implied_risk_free, dividend_yield, processed_implied_volatility, time_to_maturity)

    data_with_greek = pd.concat([underlying_price,implied_forward, option_price, strike_price, implied_risk_free, dividend_yield, time_to_maturity, option_status, option_types, implied_volatility, delta, gamma, theta, vega, rho], axis=1)
    data_with_greek.columns = ['underlying_price', 'implied_forward_price', 'option_price', 'strike_price', 'implied_risk_free_rate', 'dividend_yield', 'time_to_maturity', 'option_status', 'option_type', 'implied_vol', 'delta', 'gamma', 'theta', 'vega', 'rho']

    return data_with_greek


# 计算50ETF期权 vol和 Greeks
def calc_stock_options_daily_implied_forward(date, calc_number):
    """
    PARAMETERS
    ----------
    date: str，当前分析日期

    calc_number: int,计算隐含远期价格时需要的期权数目，例如 calc_number=3，意味着选择距离ATM期权最近的三只OTM和三只ITM期权计算其隐含远期价格

    RETURN
    ---------
    使用隐含远期价格和当前收盘价计算得到的50ETF期权在某日的全量数据
    """

    underlying_id = '510050.XSHG'
    option_id = rqdatac.options.get_contracts(underlying_id, trading_date=date)
    option_id = [id for id in option_id if rqdatac.instruments(id).de_listed_date > str(date)]
    data_with_greek = calc_daily_vol_greeks(date, underlying_id, option_id)
    data_with_greek_forward = calc_daily_forward_vol_greeks(date, underlying_id, option_id, calc_number)

    return data_with_greek, data_with_greek_forward


# 计算白糖期权implied volatility和Greeks，白糖期权最初交易时间为2017-04-19
def calc_sr_options_daily_implied_forward(date, calc_number):
    """
    PARAMETERS
    ----------
    date: str，当前分析日期

    calc_number: int,计算隐含远期价格时需要的期权数目，例如 calc_number=3，意味着选择距离ATM期权最近的三只OTM和三只ITM期权计算其隐含远期价格

    RETURN
    ---------
    使用隐含远期价格和当前收盘价计算得到的白糖期权在某日的全量数据
    """

    # 获取当前白糖期权可交易的期权及其对应的标的期货
    option_id_sr = rqdatac.options.get_contracts('SR')
    option_id_sr = [id for id in option_id_sr if rqdatac.instruments(id).de_listed_date > str(date)]
    option_id_sr = [id for id in option_id_sr if rqdatac.instruments(id).listed_date <= str(date)]
    sr_future = list(set([id[:6] for id in option_id_sr]))

    # dict keys为标的期货，values为该标的期货对应的期权代码
    sr_dict = {}
    for i in sr_future:
        sr_dict[i] = [id for id in option_id_sr if id[:6] == i]

    data_with_greek = pd.DataFrame()
    data_with_greek_forward = pd.DataFrame()

    for underlying_id in list(sr_dict.keys()):
        current_data_with_greek = calc_daily_vol_greeks(date, underlying_id, sr_dict[underlying_id])
        current_data_with_greek_forward = calc_daily_forward_vol_greeks(date, underlying_id, sr_dict[underlying_id], calc_number)

        data_with_greek = pd.concat([data_with_greek, current_data_with_greek])
        data_with_greek_forward = pd.concat([data_with_greek_forward, current_data_with_greek_forward])

    return data_with_greek, data_with_greek_forward


# fixme：测试20181207日豆粕期权数据遇到拿到的期权代码在当前日期之后的期权
# 计算豆粕期权implied volatility和Greeks，豆粕期权最初交易时间为2017-03-31
def calc_m_options_daily_implied_forward(date, calc_number):
    """
    PARAMETERS
    ----------
    date: str，当前分析日期

    calc_number: int,计算隐含远期价格时需要的期权数目，例如 calc_number=3，意味着选择距离ATM期权最近的三只OTM和三只ITM期权计算其隐含远期价格

    RETURN
    ---------
    使用隐含远期价格和当前收盘价计算得到的豆粕期权在某日的全量数据
    """

    # 获取当前豆粕期权可交易的期权及其对应的标的期货
    option_id_m = rqdatac.options.get_contracts('M')
    option_id_m = [id for id in option_id_m if rqdatac.instruments(id).de_listed_date > str(date)]
    option_id_m = [id for id in option_id_m if rqdatac.instruments(id).listed_date <= str(date)]
    m_future = list(set([id[:5] for id in option_id_m]))

    # dict keys为标的期货，values为该标的期货对应的期权代码
    m_dict = {}
    for i in m_future:
        m_dict[i] = [id for id in option_id_m if id[:5] == i]

    data_with_greek = pd.DataFrame()
    data_with_greek_forward = pd.DataFrame()

    for underlying_id in list(m_dict.keys()):
        current_data_with_greek = calc_daily_vol_greeks(date, underlying_id, m_dict[underlying_id])
        current_data_with_greek_forward = calc_daily_forward_vol_greeks(date,underlying_id,m_dict[underlying_id],calc_number)

        data_with_greek = pd.concat([data_with_greek, current_data_with_greek])
        data_with_greek_forward = pd.concat([data_with_greek_forward, current_data_with_greek_forward])

    return data_with_greek, data_with_greek_forward


# 计算阴极铜期权implied volatility和Greeks，豆粕期权最初交易时间为2018-09-21
def calc_cu_options_daily_implied_forward(date, calc_number):
    """
    PARAMETERS
    ----------
    date: str，当前分析日期

    calc_number: int,计算隐含远期价格时需要的期权数目，例如 calc_number=3，意味着选择距离ATM期权最近的三只OTM和三只ITM期权计算其隐含远期价格

    RETURN
    ---------
    使用隐含远期价格和当前收盘价计算得到的铜期权在某日的全量数据
    """

    # 获取当前阴极铜期权可交易的期权及其对应的标的期货
    option_id_cu = rqdatac.options.get_contracts('CU')
    option_id_cu = [id for id in option_id_cu if rqdatac.instruments(id).de_listed_date > str(date)]
    option_id_cu = [id for id in option_id_cu if rqdatac.instruments(id).listed_date <= str(date)]
    cu_future = list(set([id[:6] for id in option_id_cu]))

    # dict keys为标的期货，values为该标的期货对应的期权代码
    cu_dict = {}
    for i in cu_future:
        cu_dict[i] = [id for id in option_id_cu if id[:5] == i]

    data_with_greek = pd.DataFrame()
    data_with_greek_forward = pd.DataFrame()

    for underlying_id in list(cu_dict.keys()):
        current_data_with_greek = calc_daily_vol_greeks(date, underlying_id,cu_dict[underlying_id])
        current_data_with_greek_forward = calc_daily_forward_vol_greeks(date,underlying_id,cu_dict[underlying_id],calc_number)

        data_with_greek = pd.concat([data_with_greek, current_data_with_greek])
        data_with_greek_forward = pd.concat([data_with_greek_forward, current_data_with_greek_forward])

    return data_with_greek, data_with_greek_forward


def get_50ETF_whole_data(start_date, end_date, calc_number):
    trading_dates = rqdatac.get_trading_dates(start_date, end_date)
    trading_dates = [pd.Timestamp(date) for date in trading_dates]
    underlying_id = '510050.XSHG'

    data_with_greek = {}
    data_with_greek_forward = {}

    for date in trading_dates:
        print(date)
        option_id = rqdatac.options.get_contracts('510050.XSHG', trading_date=date)
        option_id = [id for id in option_id if rqdatac.instruments(id).de_listed_date > str(date)]

        data_with_greek[date] = calc_daily_vol_greeks(date, underlying_id, option_id)
        data_with_greek_forward[date] = calc_daily_forward_vol_greeks(date, underlying_id, option_id, calc_number)

    pickle.dump(data_with_greek, open('/users/rice/desktop/options/whole_period_data/data_with_greek.pkl', 'wb'))
    pickle.dump(data_with_greek_forward, open('/users/rice/desktop/options/whole_period_data/data_with_greek_forward.pkl', 'wb'))

