
from BSmodel_modified.interpolation import *
import pandas as pd


def cal_risk_free_for_underlying_id(underlying_id, _data, distinct_price, strike_price, option_type, time_to_maturity, option_price, underlying_price):
    """
    Given a underlying id, return a series, with index = option_id whose underlying id is the given id
    and value is the forward risk free rate
    :param underlying_id:
    :param _data:
    :param distinct_price:
    :param strike_price:
    :param option_type:
    :param time_to_maturity:
    :param option_price:
    :param underlying_price:
    :return:
    """
    status = get_status(underlying_id, _data, distinct_price, strike_price, option_type)
    option_data = construct_option_data(time_to_maturity, strike_price, status, option_type)

    this_time2mature = option_data['time_to_maturity']
    unique_time = this_time2mature.unique().tolist()
    forward_risk_free = pd.Series(index=status.index.tolist())

    for cur_time2mature in unique_time:
        selected_option = select_option(option_data, cur_time2mature)
        tmp_rf = calc_implied_forward_and_risk_free(selected_option, option_price, strike_price, underlying_price, cur_time2mature)
        cur_contract = this_time2mature[this_time2mature == cur_time2mature].index.tolist()
        forward_risk_free.loc[cur_contract] = tmp_rf

    return forward_risk_free


def get_status(underlying_id, _data, distinct_price, strike_price, option_type):
    """
    :param underlying_id:
    :param _data:
    :param distinct_price:
    :param strike_price:
    :param option_type:
    :return: options.py status, for options.py on the market with exact underlying id
    """
    op_id_list = _data[_data['underlying_order_book_id'] == underlying_id]['order_book_id'].tolist()
    args = [distinct_price.loc[underlying_id], op_id_list, strike_price, option_type]
    if underlying_id == '510050.XSHG':
        option_status = stock_options_status(*args)
    elif 'SR' in underlying_id:
        option_status = sr_options_status(*args)
    elif 'M' in underlying_id:
        option_status = m_options_status(*args)
    elif 'CU' in underlying_id:
        option_status = cu_options_status(*args)
    elif 'RU' in underlying_id:
        option_status = ru_options_status(*args)
    elif 'CF' in underlying_id:
        option_status = cf_options_status(*args)
    elif 'C' in underlying_id:
        option_status = c_options_status(*args)

    else:
        raise AttributeError('underlying id is invalid or not currently supported')
    return option_status


def construct_option_data(time_to_maturity, strike_price, option_status, option_types):
    """

    :param time_to_maturity:
    :param strike_price:
    :param option_status:
    :param option_types:
    :return:
    """
    option_data = pd.concat([time_to_maturity, strike_price, option_status, option_types], axis=1).dropna()
    option_data.columns = ['time_to_maturity', 'strike_price', 'option_status', 'option_type']
    return option_data


def calc_implied_forward_and_risk_free(selected_options, option_price, strike_price, underlying_price, time_to_maturity):
    """
    计算对应期限期权的隐含远期价格和隐含无风险利率
    PARAMETERS
    ----------
    selected_options:
    dict,计算隐含远期价格选择的put call option代码，key为call options.py，values为相同strike price的put options.py

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
    key = 0
    for key in list(selected_options.keys()):
        try:
            implied_forward += strike_price.loc[key] / (1 - (option_price.loc[key] - option_price.loc[selected_options[key]]) / underlying_price.loc[key])
        except KeyError:
            print('Data Missing: ', key)
            continue

    implied_forward = implied_forward / len(selected_options)

    implied_risk_free = np.log(implied_forward/underlying_price.loc[key]) / time_to_maturity

    return implied_risk_free


def select_option(option_data, time_to_maturity, calc_number=3):
    """
    挑选对应期限的ATM期权，包括 call options.py 和 put options.py
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
    dict, key为call options.py id，values为put options.py id

    selected_call_option:
    list, 所选择的call options.py id

    selected_put_option:
    list, 所选择的put options.py id
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

    return selected_options


def stock_options_status(underlying_price, option_id, strike_price, option_type):
    """
    PARAMETERS
    ----------
    date:

    underlying_id:

    RETURN
    ---------
    当前存续的50ETF期权的状态，ATM、ITM 或 OTM, for options.py id
    :param option_type: series index = order_book_id, value = options.py type
    :param strike_price: strike prices for all options.py in the market
    :param option_id: options.py ids for underlying id, eg: '500050.XSHE'
    :param underlying_price: price for a exact underlying book ids. eg '500050.XSHE'
    """

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

    for _id in option_id:
        if strike_price.loc[_id] == current_atm_option:
            status.loc[_id] = 'ATM'

        elif strike_price.loc[_id] > current_atm_option:
            # 当行权价格比期货价格高时，若期权为call options.py，此时期权状态为'OTM'（out of the money），若期权为put options.py,此时期权状态为为'ITM'（in the money）
            if option_type.loc[_id] == 'C':
                status.loc[_id] = 'OTM'
            else:
                status.loc[_id] = 'ITM'

        else:
            # 当行权价格比期货价格低时，若期权为call options.py，此时期权状态为'ITM'（in the money），若期权为put options.py,此时期权状态为为'OTM'（out of the money）
            if option_type.loc[_id] == 'C':
                status.loc[_id] = 'ITM'
            else:
                status.loc[_id] = 'OTM'

    return status


# FIXME:商品期权ATM如何确定，目前逻辑为四舍五入，若四舍五入之后没有对应的期权数据，则选择距离现价最近的期权定义为ATM
def sr_options_status(underlying_price, option_id, strike_price, option_type):
    """
    PARAMETERS
    ----------

    RETURN pandas series index = options.py id , value = status
    ---------
    当前存续的白糖期权的状态，ATM、ITM 或 OTM
    :param option_type: series index = order_book_id, value = options.py type
    :param strike_price: strike prices for all options.py in the market
    :param option_id: options.py ids for underlying id, eg: 'SR', list
    :param underlying_price: price for a exact underlying book ids. eg SR
    """

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

    for _id in option_id:
        if strike_price.loc[_id] == current_atm_option:
            status.loc[_id] = 'ATM'

        elif strike_price.loc[_id] > current_atm_option:
            # 当行权价格比期货价格高时，若期权为call options.py，此时期权状态为'OTM'（out of the money），若期权为put options.py,此时期权状态为为'ITM'（in the money）
            if option_type.loc[_id] == 'C':
                status.loc[_id] = 'OTM'
            else:
                status.loc[_id] = 'ITM'

        else:
            # 当行权价格比期货价格低时，若期权为call options.py，此时期权状态为'ITM'（in the money），若期权为put options.py,此时期权状态为为'OTM'（out of the money）
            if option_type.loc[_id] == 'C':
                status.loc[_id] = 'ITM'
            else:
                status.loc[_id] = 'OTM'

    return status


def m_options_status(underlying_price, option_id, strike_price, option_type):
    """
    PARAMETERS
    ----------
    date: str，当前分析日期

    underlying_id: str，豆粕期权的标的期货

    RETURN
    ---------
    当前存续的豆粕期权的状态，ATM、ITM 或 OTM
    :param option_type: series index = order_book_id, value = options.py type
    :param strike_price: strike prices for all options.py in the market
    :param option_id: options.py ids for underlying id, eg: 'SR'
    :param underlying_price: price for a exact underlying book ids. eg SR
    """

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

    for _id in option_id:
        if strike_price.loc[_id] == current_atm_option:
            status.loc[_id] = 'ATM'

        elif strike_price.loc[_id] > current_atm_option:
            # 当行权价格比期货价格高时，若期权为call options.py，此时期权状态为'OTM'（out of the money），若期权为put options.py,此时期权状态为为'ITM'（in the money）
            if option_type.loc[_id] == 'C':
                status.loc[_id] = 'OTM'
            else:
                status.loc[_id] = 'ITM'

        else:
            # 当行权价格比期货价格低时，若期权为call options.py，此时期权状态为'ITM'（in the money），若期权为put options.py,此时期权状态为为'OTM'（out of the money）
            if option_type.loc[_id] == 'C':
                status.loc[_id] = 'ITM'
            else:
                status.loc[_id] = 'OTM'

    return status


def cu_options_status(underlying_price, option_id, strike_price, option_type):
    """
    PARAMETERS
    ----------
    date: str，当前分析日期

    underlying_id: str，豆粕期权的标的期货

    RETURN
    ---------
    当前存续的豆粕期权的状态，ATM、ITM 或 OTM
    :param option_type: series index = order_book_id, value = options.py type
    :param strike_price: strike prices for all options.py in the market
    :param option_id: options.py ids for underlying id, eg: 'SR'
    :param underlying_price: price for a exact underlying book ids. eg SR
    """

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
            # 当行权价格比期货价格高时，若期权为call options.py，此时期权状态为'OTM'（out of the money），若期权为put options.py,此时期权状态为为'ITM'（in the money）
            if option_type.loc[id] == 'C':
                status.loc[id] = 'OTM'
            else:
                status.loc[id] = 'ITM'

        else:
            # 当行权价格比期货价格低时，若期权为call options.py，此时期权状态为'ITM'（in the money），若期权为put options.py,此时期权状态为为'OTM'（out of the money）
            if option_type.loc[id] == 'C':
                status.loc[id] = 'ITM'
            else:
                status.loc[id] = 'OTM'

    return status


def ru_options_status(underlying_price, option_id, strike_price, option_type):
    """
    PARAMETERS
    ----------
    date: str，当前分析日期

    underlying_id: str，豆粕期权的标的期货

    RETURN
    ---------
    当前存续的豆粕期权的状态，ATM、ITM 或 OTM
    :param option_type: series index = order_book_id, value = options.py type
    :param strike_price: strike prices for all options.py in the market
    :param option_id: options.py ids for underlying id, eg: 'SR'
    :param underlying_price: price for a exact underlying book ids. eg SR
    """

    status = pd.Series(index=option_id)

    if underlying_price <= 10000:
        price_interval = 100
    elif underlying_price <= 25000:
        price_interval = 250
    else:
        price_interval = 500

    times = np.around(underlying_price / price_interval, 0)
    current_atm_option = np.around(times * price_interval, 0)
    # 若当前期权中没有符合ATM要求的期权，则选择此时距离理论上ATM期权最近的期权定位ATM
    if strike_price[strike_price == current_atm_option].shape[0] == 0:
        current_atm_option = abs((strike_price - current_atm_option)).min() + current_atm_option

    for id in option_id:
        if strike_price.loc[id] == current_atm_option:
            status.loc[id] = 'ATM'

        elif strike_price.loc[id] > current_atm_option:
            # 当行权价格比期货价格高时，若期权为call options.py，此时期权状态为'OTM'（out of the money），若期权为put options.py,此时期权状态为为'ITM'（in the money）
            if option_type.loc[id] == 'C':
                status.loc[id] = 'OTM'
            else:
                status.loc[id] = 'ITM'

        else:
            # 当行权价格比期货价格低时，若期权为call options.py，此时期权状态为'ITM'（in the money），若期权为put options.py,此时期权状态为为'OTM'（out of the money）
            if option_type.loc[id] == 'C':
                status.loc[id] = 'ITM'
            else:
                status.loc[id] = 'OTM'
    return status


def cf_options_status(underlying_price, option_id, strike_price, option_type):
    """
    PARAMETERS
    ----------
    date: str，当前分析日期

    underlying_id: str，豆粕期权的标的期货

    RETURN
    ---------
    当前存续的豆粕期权的状态，ATM、ITM 或 OTM
    :param option_type: series index = order_book_id, value = options.py type
    :param strike_price: strike prices for all options.py in the market
    :param option_id: options.py ids for underlying id, eg: 'SR'
    :param underlying_price: price for a exact underlying book ids. eg SR
    """

    status = pd.Series(index=option_id)

    if underlying_price <= 10000:
        price_interval = 100
    elif underlying_price <= 20000:
        price_interval = 200
    else:
        price_interval = 400

    times = np.around(underlying_price / price_interval, 0)
    current_atm_option = np.around(times * price_interval, 0)
    # 若当前期权中没有符合ATM要求的期权，则选择此时距离理论上ATM期权最近的期权定位ATM
    if strike_price[strike_price == current_atm_option].shape[0] == 0:
        current_atm_option = abs((strike_price - current_atm_option)).min() + current_atm_option

    for id in option_id:
        if strike_price.loc[id] == current_atm_option:
            status.loc[id] = 'ATM'

        elif strike_price.loc[id] > current_atm_option:
            # 当行权价格比期货价格高时，若期权为call options.py，此时期权状态为'OTM'（out of the money），若期权为put options.py,此时期权状态为为'ITM'（in the money）
            if option_type.loc[id] == 'C':
                status.loc[id] = 'OTM'
            else:
                status.loc[id] = 'ITM'

        else:
            # 当行权价格比期货价格低时，若期权为call options.py，此时期权状态为'ITM'（in the money），若期权为put options.py,此时期权状态为为'OTM'（out of the money）
            if option_type.loc[id] == 'C':
                status.loc[id] = 'ITM'
            else:
                status.loc[id] = 'OTM'
    return status


def c_options_status(underlying_price, option_id, strike_price, option_type):
    """
    PARAMETERS
    ----------
    date: str，当前分析日期
    underlying_id: str，豆粕期权的标的期货
    RETURN
    ---------
    当前存续的豆粕期权的状态，ATM、ITM 或 OTM
    :param option_type: series index = order_book_id, value = options.py type
    :param strike_price: strike prices for all options.py in the market
    :param option_id: options.py ids for underlying id, eg: 'SR'
    :param underlying_price: price for a exact underlying book ids. eg SR
    """

    status = pd.Series(index=option_id)

    if underlying_price <= 1000:
        price_interval = 10
    elif underlying_price <= 3000:
        price_interval = 20
    else:
        price_interval = 40

    times = np.around(underlying_price / price_interval, 0)
    current_atm_option = np.around(times * price_interval, 0)
    # 若当前期权中没有符合ATM要求的期权，则选择此时距离理论上ATM期权最近的期权定位ATM
    if strike_price[strike_price == current_atm_option].shape[0] == 0:
        current_atm_option = abs((strike_price - current_atm_option)).min() + current_atm_option

    for id in option_id:
        if strike_price.loc[id] == current_atm_option:
            status.loc[id] = 'ATM'

        elif strike_price.loc[id] > current_atm_option:
            # 当行权价格比期货价格高时，若期权为call options.py，此时期权状态为'OTM'（out of the money），若期权为put options.py,此时期权状态为为'ITM'（in the money）
            if option_type.loc[id] == 'C':
                status.loc[id] = 'OTM'
            else:
                status.loc[id] = 'ITM'

        else:
            # 当行权价格比期货价格低时，若期权为call options.py，此时期权状态为'ITM'（in the money），若期权为put options.py,此时期权状态为为'OTM'（out of the money）
            if option_type.loc[id] == 'C':
                status.loc[id] = 'ITM'
            else:
                status.loc[id] = 'OTM'
    return status