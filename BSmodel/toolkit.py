import numpy as np
import pandas as pd
from root_finding_algorithms import *
from interpolation import *
import rqdatac

rqdatac.init('quant', 'quant123', ('172.18.0.17', 16010))


def calc_time_to_maturity(order_book_id, date):
    """
    PARAMETERS
    ----------
    order_book_id: list，期权的order_book_id

    date: str，当前分析日期

    RETURN
    ---------
    pd.Series,返回每只期权当前日期对应的time_to_maturity
    """
    time_to_maturity = pd.Series(index=order_book_id)

    for id in order_book_id:
        option_delisted_date = rqdatac.instruments(id).de_listed_date
        days_to_maturity = (pd.Timestamp(option_delisted_date) - pd.Timestamp(date)).days
        time_to_maturity.loc[id] = days_to_maturity / 365

    return time_to_maturity


def apply_risk_free_rate(order_book_id, date):
    """
    根据期权不同的期限选择对应的无风险利率
    PARAMETERS
    ----------
    order_book_id: list，期权的order_book_id

    date: str，当前分析日期

    RETURN
    ---------
    pd.Series,返回每只期权当前日期对应的无风险利率
    """

    risk_free_rate = pd.Series(index=order_book_id)
    current_risk_free = rqdatac.get_yield_curve(date, date, tenor=['0S', '1M', '2M', '3M', '6M', '9M', '1Y'])
    x = pd.Series(data=[1, 30, 60, 90, 180, 270, 360])
    y = pd.Series(data=current_risk_free.values[0])

    for id in order_book_id:
        option_delisted_date = rqdatac.instruments(id).de_listed_date

        days_to_maturity = (pd.Timestamp(option_delisted_date) - pd.Timestamp(date)).days

        risk_free_rate.loc[id] = cubic_spline_interpolation(y, x, np.array([days_to_maturity])).values[0]

    return risk_free_rate


def calc_implied_forward_and_risk_free(selected_options, option_price, strike_price, underlying_price,time_to_maturity):
    """
    计算对应期限期权的隐含远期价格和隐含无风险利率
    PARAMETERS
    ----------
    selected_options:
    dict,计算隐含远期价格选择的put call option代码，key为call option，values为相同strike price的put option

    option_price:
    pd.Series 期权价，index为期权代码，values为对应期权价

    strike_price:
    pd.Series 期权行权价，index为期权代码，values为对应期权行权价

    underlying_price:
    pd.Series 标的价格，index为期权代码，values为对应标的价格

    time_to_maturity:
    float 所选期权的期限，以年为单位

    RETURN
    ---------
    float 当前期限期权远期价格,隐含无风险利率（r-q）

    """
    implied_forward = 0

    for key in list(selected_options.keys()):
        implied_forward += strike_price.loc[key] / (1 - (option_price.loc[key] - option_price.loc[selected_options[key]]) / underlying_price.loc[key])

    implied_forward = implied_forward / len(selected_options)

    implied_risk_free = np.log(implied_forward/underlying_price.loc[key]) / time_to_maturity

    return implied_forward, implied_risk_free


def stock_options_status(date, underlying_id):
    """
    PARAMETERS
    ----------
    date: str，当前分析日期

    underlying_id: str，50ETF期权的标的，即 '510050.XSHG'

    RETURN
    ---------
    当前存续的50ETF期权的状态，ATM、ITM 或 OTM
    """

    underlying_price = rqdatac.get_price(underlying_id, date, date, '1d', 'close').loc[date]

    # 取出当天可交易的所有50ETF期权
    option_id = rqdatac.options.get_contracts(underlying_id,trading_date=date)

    # 取出可交易期权的strike price
    strike_price = rqdatac.get_price(option_id, date, date, fields='strike_price').loc[date]

    status = pd.Series(index=option_id)

    if underlying_price <= 3:
        price_interval = 0.05
    elif underlying_price <= 5:
        price_interval = 0.1
    elif underlying_price <= 10:
        price_interval = 0.25
    elif underlying_price <= 20:
        price_interval = 0.5
    elif underlying_price <= 50:
        price_interval = 1
    elif underlying_price <= 100:
        price_interval = 2.5
    else:
        price_interval = 5

    times = np.around(underlying_price / price_interval, 0)
    current_atm_option = np.around(times * price_interval, 3)

    # 若当前期权中没有符合ATM要求的期权，则选择此时距离理论上ATM期权最近的期权定位ATM
    if strike_price[strike_price == current_atm_option].shape[0] == 0:
        current_atm_option = abs((strike_price - current_atm_option)).min() + current_atm_option

    for id in option_id:
        if strike_price.loc[id] == current_atm_option:
            status.loc[id] = 'ATM'

        elif strike_price.loc[id] > current_atm_option:
            # 当行权价格比期货价格高时，若期权为call option，此时期权状态为'OTM'（out of the money），若期权为put option,此时期权状态为为'ITM'（in the money）
            if rqdatac.instruments(id).option_type == 'C':
                status.loc[id] = 'OTM'
            else:
                status.loc[id] = 'ITM'

        else:
            # 当行权价格比期货价格低时，若期权为call option，此时期权状态为'ITM'（in the money），若期权为put option,此时期权状态为为'OTM'（out of the money）
            if rqdatac.instruments(id).option_type == 'C':
                status.loc[id] = 'ITM'
            else:
                status.loc[id] = 'OTM'

    return status


# FIXME:商品期权ATM如何确定，目前逻辑为四舍五入，若四舍五入之后没有对应的期权数据，则选择距离现价最近的期权定义为ATM
def sr_options_status(date, underlying_id):
    """
    PARAMETERS
    ----------
    date: str，当前分析日期

    underlying_id: str，白糖期权的标的期货

    RETURN
    ---------
    当前存续的白糖期权的状态，ATM、ITM 或 OTM
    """

    underlying_price = rqdatac.get_price(underlying_id, date, date, '1d', 'close').loc[date]

    # 取出当天可交易的所有白糖期权
    option_id = rqdatac.options.get_contracts(underlying_id)
    option_id = [id for id in option_id if rqdatac.instruments(id).de_listed_date >= str(date)]
    option_id = [id for id in option_id if rqdatac.instruments(id).listed_date <= str(date)]
    # 取出可交易期权的strike price
    strike_price = rqdatac.get_price(option_id, date, date, fields='strike_price').loc[date]

    status = pd.Series(index=option_id)

    if underlying_price <= 3000:
        price_interval = 50
    elif underlying_price <= 10000:
        price_interval = 100
    else:
        price_interval = 200

    times = np.around(underlying_price / price_interval, 0)
    current_atm_option = np.around(times * price_interval, 0)

    # 若当前期权中没有符合ATM要求的期权，则选择此时距离理论上ATM期权最近的期权定位ATM
    if strike_price[strike_price == current_atm_option].shape[0] == 0:
        current_atm_option = abs((strike_price - current_atm_option)).min() + current_atm_option

    for id in option_id:
        if strike_price.loc[id] == current_atm_option:
            status.loc[id] = 'ATM'

        elif strike_price.loc[id] > current_atm_option:
            # 当行权价格比期货价格高时，若期权为call option，此时期权状态为'OTM'（out of the money），若期权为put option,此时期权状态为为'ITM'（in the money）
            if rqdatac.instruments(id).option_type == 'C':
                status.loc[id] = 'OTM'
            else:
                status.loc[id] = 'ITM'

        else:
            # 当行权价格比期货价格低时，若期权为call option，此时期权状态为'ITM'（in the money），若期权为put option,此时期权状态为为'OTM'（out of the money）
            if rqdatac.instruments(id).option_type == 'C':
                status.loc[id] = 'ITM'
            else:
                status.loc[id] = 'OTM'

    return status


def m_options_status(date,underlying_id):
    """
    PARAMETERS
    ----------
    date: str，当前分析日期

    underlying_id: str，豆粕期权的标的期货

    RETURN
    ---------
    当前存续的豆粕期权的状态，ATM、ITM 或 OTM
    """

    underlying_price = rqdatac.get_price(underlying_id, date, date, '1d', 'close').loc[date]

    # 取出当天可交易的所有豆粕期权
    option_id = rqdatac.options.get_contracts(underlying_id)
    option_id = [id for id in option_id if rqdatac.instruments(id).de_listed_date >= str(date)]
    option_id = [id for id in option_id if rqdatac.instruments(id).listed_date <= str(date)]
    # 取出可交易期权的strike price
    strike_price = rqdatac.get_price(option_id, date, date, fields='strike_price').loc[date]

    status = pd.Series(index=option_id)

    if underlying_price <= 2000:
        price_interval = 25
    elif underlying_price <= 5000:
        price_interval = 50
    else:
        price_interval = 100

    times = np.around(underlying_price / price_interval, 0)
    current_atm_option = np.around(times * price_interval, 0)
    # 若当前期权中没有符合ATM要求的期权，则选择此时距离理论上ATM期权最近的期权定位ATM
    if strike_price[strike_price == current_atm_option].shape[0] == 0:
        current_atm_option = abs((strike_price - current_atm_option)).min() + current_atm_option

    for id in option_id:
        if strike_price.loc[id] == current_atm_option:
            status.loc[id] = 'ATM'

        elif strike_price.loc[id] > current_atm_option:
            # 当行权价格比期货价格高时，若期权为call option，此时期权状态为'OTM'（out of the money），若期权为put option,此时期权状态为为'ITM'（in the money）
            if rqdatac.instruments(id).option_type == 'C':
                status.loc[id] = 'OTM'
            else:
                status.loc[id] = 'ITM'

        else:
            # 当行权价格比期货价格低时，若期权为call option，此时期权状态为'ITM'（in the money），若期权为put option,此时期权状态为为'OTM'（out of the money）
            if rqdatac.instruments(id).option_type == 'C':
                status.loc[id] = 'ITM'
            else:
                status.loc[id] = 'OTM'

    return status


def cu_options_status(date,underlying_id):
    """
    PARAMETERS
    ----------
    date: str，当前分析日期

    underlying_id: str，铜期权的标的期货

    RETURN
    ---------
    当前存续的铜期权的状态，ATM、ITM 或 OTM
    """

    underlying_price = rqdatac.get_price(underlying_id, date, date, '1d', 'close').loc[date]

    # 取出当天可交易的所有铜期权
    option_id = rqdatac.options.get_contracts(underlying_id)
    option_id = [id for id in option_id if rqdatac.instruments(id).de_listed_date >= str(date)]
    option_id = [id for id in option_id if rqdatac.instruments(id).listed_date <= str(date)]
    # 取出可交易期权的strike price
    strike_price = rqdatac.get_price(option_id, date, date, fields='strike_price').loc[date]

    status = pd.Series(index=option_id)

    if underlying_price <= 40000:
        price_interval = 500
    elif underlying_price <= 80000:
        price_interval = 1000
    else:
        price_interval = 2000

    times = np.around(underlying_price / price_interval, 0)
    current_atm_option = np.around(times * price_interval, 0)
    # 若当前期权中没有符合ATM要求的期权，则选择此时距离理论上ATM期权最近的期权定位ATM
    if strike_price[strike_price == current_atm_option].shape[0] == 0:
        current_atm_option = abs((strike_price - current_atm_option)).min() + current_atm_option

    for id in option_id:
        if strike_price.loc[id] == current_atm_option:
            status.loc[id] = 'ATM'

        elif strike_price.loc[id] > current_atm_option:
            # 当行权价格比期货价格高时，若期权为call option，此时期权状态为'OTM'（out of the money），若期权为put option,此时期权状态为为'ITM'（in the money）
            if rqdatac.instruments(id).option_type == 'C':
                status.loc[id] = 'OTM'
            else:
                status.loc[id] = 'ITM'

        else:
            # 当行权价格比期货价格低时，若期权为call option，此时期权状态为'ITM'（in the money），若期权为put option,此时期权状态为为'OTM'（out of the money）
            if rqdatac.instruments(id).option_type == 'C':
                status.loc[id] = 'ITM'
            else:
                status.loc[id] = 'OTM'

    return status


def select_option(option_data, time_to_maturity, calc_number):
    """
    挑选对应期限的ATM期权，包括 call option 和 put option
    PARAMETERS
    ----------

    option_data:
    DataFrame, 期权数据，index为期权代码，columns包括：time_to_maturity(到期时间），option_type（期权类型），strike_price（行权价格），status（期权状态等）

    time_to_maturity:
    float，期权到期时间

    calc_number:
    int 自定义计算隐含远期价格时，选择的档数，比如calc_number=3，即意为选择平值期权附近3个实值期权和3个虚值期权

    RETURN
    ---------
    selected_options:
    dict, key为call option id，values为put option id

    selected_call_option:
    list, 所选择的call option id

    selected_put_option:
    list, 所选择的put option id
    """

    needed_options = option_data[option_data['time_to_maturity'] == time_to_maturity]

    # 找到当前期权中的平值期权所在位置
    # 取出当前期权的平值期权，call和put各有一个平值期权,根据call和put分别选择所需的期权
    call_options = needed_options[needed_options['option_type'] == 'C']
    put_options = needed_options[needed_options['option_type'] == 'P']

    call_options = call_options.sort_values(by='strike_price')
    put_options = put_options.sort_values(by='strike_price')

    # 若当前call期权不存在ATM期权
    if call_options[call_options['option_status'] == 'ATM'].empty is True:
        status = call_options['option_status'].unique()
        if len(status) == 1 and status == 'OTM':
            call_ATM = 0
        elif len(status) == 1 and status == 'ITM':
            call_ATM = len(call_options)
        else:
            call_ATM = call_options.index.tolist().index(call_options[call_options['option_status'] == 'ITM'].index[-1])
    else:
        call_ATM = call_options.index.tolist().index(call_options[call_options['option_status'] == 'ATM'].index[0])

    if put_options[put_options['option_status'] == 'ATM'].empty is True:
        status = put_options['option_status'].unique()
        if len(status) == 1 and status == 'ITM':
            put_ATM = 0
        elif len(status) == 1 and status == 'OTM':
            put_ATM = len(put_options)
        else:
            put_ATM = put_options.index.tolist().index(put_options[put_options['option_status'] == 'OTM'].index[-1])
    else:
        put_ATM = put_options.index.tolist().index(put_options[put_options['option_status'] == 'ATM'].index[0])

    call_bound = (max(0, call_ATM - calc_number), min(call_ATM + calc_number, len(call_options)))
    put_bound = (max(0, put_ATM - calc_number), min(put_ATM + calc_number, len(put_options)))

    selected_call_option = call_options.iloc[call_bound[0]:call_bound[1] + 1].index.tolist()
    selected_put_option = put_options.iloc[put_bound[0]:put_bound[1] + 1].index.tolist()

    # 将选择的put和call按照strike price组合：
    selected_options = {}
    for i in range(len(selected_call_option)):
        selected_options.update({selected_call_option[i]: selected_put_option[i]})

    return selected_options, selected_call_option, selected_put_option


# 对计算得到的implied volatility进行处理
def processing_implied_volatility(implied_volatility, strike_price, time_to_maturity, option_types):
    """
    针对deep in the money 或者 deep out of the money的期权隐含波动率使用行权价和期限相同的期权进行近似处理
    PARAMETERS
    ----------
    implied_volatility: pd.Series,index为期权id，values为其对应的隐含波动率

    strike_price: pd.Series,index为期权id，values为其对应的行权价

    option_types: pd.Series,index为期权id，values为其对应的期权类型'C'或者'P'

    RETURN
    ----------
    pd.Series,index为期权id，values为其对应的隐含波动率
    """

    processed_implied_volatility = implied_volatility.copy()

    # 挑选出implied volatility数值趋近于0的期权：
    selected_options = implied_volatility[abs(implied_volatility) <= 1e-4]

    # 针对结果无限趋近于0的call / put option，使用跟其到期时间和行权价相同的put / call option的隐含波动率填补

    for id in selected_options.index.tolist():
        current_option_type = option_types.loc[id]
        current_time_to_maturity = time_to_maturity.loc[id]
        current_strike_price = strike_price.loc[id]

        # 根据time_to_maturity先挑选出所有期限相同的期权
        first_selected_options = time_to_maturity[time_to_maturity==current_time_to_maturity].index.tolist()
        second_selected = strike_price.loc[first_selected_options][strike_price.loc[first_selected_options]==current_strike_price].index.tolist()

        if current_option_type == 'P':
            target_type = 'C'
        else:
            target_type = 'P'
        target_id = option_types.loc[second_selected][option_types.loc[second_selected]==target_type].index[0]

        processed_implied_volatility.loc[id] = processed_implied_volatility.loc[target_id]

    return processed_implied_volatility
