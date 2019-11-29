# -*- coding:utf-8 -*-
import bisect
import pandas as pd
import numpy as np


def cal_risk_free_for_underlying_id(underlying_id, _data, distinct_price, strike_price,
                                    option_type, time_to_maturity, option_price, underlying_price):
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
        tmp_rf = calc_implied_forward_and_risk_free(selected_option, option_price,
                                                    strike_price, underlying_price, cur_time2mature)
        cur_contract = this_time2mature[this_time2mature == cur_time2mature].index.tolist()
        forward_risk_free[cur_contract] = tmp_rf

    return forward_risk_free


class StatusArgument:
    def __init__(self, points, values, precision=0):
        assert len(values) == len(points) + 1, "values length must be 1 more than points"
        self.points = points
        self.values = values
        self.precision = precision

    def get_interval(self, underlying_price):
        return self.values[bisect.bisect_left(self.points, underlying_price)]


STATUS_MAP = {
    '510050.XSHG': StatusArgument([3, 5, 10, 20, 50, 100], [0.05, 0.1, 0.25, 0.5, 1, 2.5, 5], 3),
    'SR': StatusArgument([3000, 10000], [50, 100, 200]),
    'M': StatusArgument([2000, 5000], [20, 50, 100]),
    'CU': StatusArgument([40000, 80000], [500, 1000, 2000]),
    'RU': StatusArgument([10000, 25000], [100, 250, 500]),
    'CF': StatusArgument([10000, 20000], [100, 200, 400]),
    'C': StatusArgument([1000, 3000], [10, 20, 40])
}


def get_option_status(underlying_price, option_id, strike_price, option_type, status_type):
    """
    当前存续的50ETF期权的状态，ATM、ITM 或 OTM, for option id
    :param option_type: series index = order_book_id, value = option type
    :param strike_price: strike prices for all option in the market
    :param option_id: option ids for underlying id, eg: '500050.XSHE'
    :param underlying_price: price for a exact underlying book ids. eg '500050.XSHE'
    :param status_type: one of ['510050.XSHG', 'SR', 'M', 'CU', 'RU', 'CF', 'C']
    """

    arg = STATUS_MAP[status_type]
    price_interval = arg.get_interval(underlying_price)

    times = np.around(underlying_price / price_interval, 0)
    current_atm_option = np.around(times * price_interval, arg.precision)

    # 若当前期权中没有符合ATM要求的期权，则选择此时距离理论上ATM期权最近的期权定位ATM
    if strike_price[strike_price == current_atm_option].shape[0] == 0:
        current_atm_option = abs((strike_price - current_atm_option)).min() + current_atm_option

    # convert to dict speed up following function
    strike_price = strike_price.to_dict()
    option_type = option_type.to_dict()

    def stats(_id):
        if strike_price[_id] == current_atm_option:
            return 'ATM'

        if strike_price[_id] > current_atm_option:
            # 当行权价格比期货价格高时，若期权为call option，此时期权状态为'OTM'（out of the money），
            # 若期权为put option,此时期权状态为为'ITM'（in the money）
            if option_type[_id] == 'C':
                return 'OTM'
            return 'ITM'

        # 当行权价格比期货价格低时，若期权为call option，此时期权状态为'ITM'（in the money）
        # 若期权为put option,此时期权状态为为'OTM'（out of the money）
        if option_type[_id] == 'C':
            return 'ITM'

        return 'OTM'

    status = pd.Series(index=option_id, data=map(stats, option_id))
    return status


def get_status_type(underlying_id):
    if underlying_id == '510050.XSHG':
        return underlying_id
    if 'SR' in underlying_id:
        return 'SR'
    if 'M' in underlying_id:
        return 'M'
    if 'CU' in underlying_id:
        return 'CU'
    if 'RU' in underlying_id:
        return 'RU'
    if 'CF' in underlying_id:
        return 'CF'
    if 'C' in underlying_id:
        return 'C'


def get_status(underlying_id, _data, distinct_price, strike_price, option_type):
    """
    :param underlying_id:
    :param _data:
    :param distinct_price:
    :param strike_price:
    :param option_type:
    :return: option_status, for option on the market with exact underlying id
    """
    op_id_list = _data[_data['underlying_order_book_id'] == underlying_id]['order_book_id'].tolist()
    status_type = get_status_type(underlying_id)
    if status_type is None:
        raise AttributeError('underlying id is invalid or not currently supported')
    return get_option_status(distinct_price[underlying_id], op_id_list, strike_price, option_type, status_type)


def construct_option_data(time_to_maturity, strike_price, option_status, option_types):
    """

    :param time_to_maturity:
    :param strike_price:
    :param option_status:
    :param option_types:
    :return:
    """
    option_data = pd.concat([time_to_maturity, strike_price, option_status, option_types], axis=1, sort=True).dropna()
    option_data.columns = ['time_to_maturity', 'strike_price', 'option_status', 'option_type']
    return option_data


def calc_implied_forward_and_risk_free(selected_options, option_price, strike_price,
                                       underlying_price, time_to_maturity):
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
    key_price = 1
    for key, put in selected_options.items():
        try:
            key_price = underlying_price[key]
            implied_forward += strike_price[key] * key_price / (
                    key_price - option_price[key] + option_price[put])
        except KeyError:
            print('Data Missing: ', key)
            continue

    implied_forward = implied_forward / len(selected_options)

    implied_risk_free = np.log(implied_forward/key_price) / time_to_maturity

    return implied_risk_free


def select_option(option_data, time_to_maturity, calc_number=3):
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

    call_atm = call_options[call_options['option_status'] == 'ATM']
    put_atm = put_options[put_options['option_status'] == 'ATM']

    # 若当前call期权不存在ATM期权
    if call_atm.empty:
        status = call_options['option_status'].unique()
        if len(status) == 1 and status == 'OTM':
            call_ATM = 0
        elif len(status) == 1 and status == 'ITM':
            call_ATM = len(call_options)
        else:
            call_ATM = call_options.index.tolist().index(
                call_options[call_options['option_status'] == 'ITM'].index[-1])
    else:
        call_ATM = call_options.index.tolist().index(call_atm.index[0])

    if put_atm.empty:
        status = put_options['option_status'].unique()
        if len(status) == 1 and status == 'ITM':
            put_ATM = 0
        elif len(status) == 1 and status == 'OTM':
            put_ATM = len(put_options)
        else:
            put_ATM = put_options.index.tolist().index(
                put_options[put_options['option_status'] == 'OTM'].index[-1])
    else:
        put_ATM = put_options.index.tolist().index(put_atm.index[0])

    call_bound = (max(0, call_ATM - calc_number), min(call_ATM + calc_number, len(call_options)))
    put_bound = (max(0, put_ATM - calc_number), min(put_ATM + calc_number, len(put_options)))

    selected_call_option = call_options.index.tolist()[call_bound[0]:call_bound[1] + 1]
    selected_put_option = put_options.index.tolist()[put_bound[0]:put_bound[1] + 1]

    # 将选择的put和call按照strike price组合：
    selected_options = dict(zip(selected_call_option, selected_put_option))

    return selected_options
