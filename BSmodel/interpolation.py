import pandas as pd
import numpy as np


# 参考：https://en.wikiversity.org/wiki/Cubic_Spline_Interpolation#quiz0
def cubic_spline_interpolation(Y, X, X_new):
    """
    ----------
    Parameter
    Y: pd.Series values为待拟合因变量数据点

    X: pd.Series values为待拟合自变量数据点

    X_new: 1-d array values为需要计算的X值

    ----------
    Return
    Y_new: pd.Series values为插值拟合X_new对应的Y值, index 为自然数

    """

    # 首先计算出自变量X和因变量Y的一阶差分
    diff_x = X.diff()
    diff_y = Y.diff()
    number = len(X)

    lambda_value = pd.Series(index=range(number-1))
    mu_value = pd.Series(index=range(number)[1:])
    d_value = pd.Series(index=range(number))

    for i in range(number)[1:-1]:
        lambda_value.loc[i] = diff_x.iloc[i+1] / (diff_x.iloc[i] + diff_x.iloc[i+1])
        mu_value.loc[i] = 1 - lambda_value.loc[i]
        d_value.loc[i] = 6 * (diff_y.iloc[i+1] / (diff_x.iloc[i+1] * (diff_x.iloc[i+1]+diff_x.iloc[i])) - diff_y.iloc[i] / (diff_x.iloc[i] * (diff_x.iloc[i+1]+diff_x.iloc[i])))

    d_value.loc[0] = 0
    d_value.iloc[-1] = 0
    lambda_value.loc[0] = 0
    mu_value.iloc[-1] = 0

    # 将上述数据构建为矩阵求解 M
    intermediate_df = pd.DataFrame(index=range(number), columns=range(number), data=0)
    for i in range(number):
        intermediate_df.loc[i, i] = 2
        if i+1 < number:
            intermediate_df.loc[i + 1, i] = mu_value.loc[i + 1]
            intermediate_df.loc[i, i + 1] = lambda_value.loc[i]

    matrix = np.matrix(intermediate_df)

    target_parameter = pd.Series(data=d_value.dot(np.linalg.inv(matrix)))

    def _function_value(location, x):

        calc_value = target_parameter.iloc[location - 1] * pow((X.iloc[location] - x), 3) / (6 * diff_x.iloc[location]) + \
                     target_parameter.iloc[location] * pow((x - X.iloc[location - 1]), 3) / (6 * diff_x.iloc[location]) + \
                     (Y.iloc[location - 1] - target_parameter.iloc[location - 1] * pow(diff_x.iloc[location], 2) / 6) * (X.iloc[location] - x) / diff_x.iloc[location] + \
                     (Y.iloc[location] - target_parameter.iloc[location] * pow(diff_x.iloc[location], 2) / 6) * (x - X.iloc[location - 1]) / diff_x.iloc[location]

        return calc_value

    def _derivative_value(location, x):

        calc_derivative_value = -target_parameter.iloc[location-1] * (X.iloc[location] - x) ** 2 / (2 * diff_x.iloc[location]) + \
                     target_parameter.iloc[location] * (x - X.iloc[location - 1]) ** 2 / (2 * diff_x.iloc[location]) + \
                     (Y.iloc[location] - Y.iloc[location - 1]) / diff_x.iloc[location] - \
                     (target_parameter.iloc[location] - target_parameter.iloc[location - 1]) * diff_x.iloc[location] / 6

        return calc_derivative_value

    Y_new = pd.Series()

    for i in range(len(X_new)):
        # 分段插值
        if X_new[i] < X.iloc[0]:
            Y_new.loc[i] = Y.iloc[0] + _derivative_value(1, X.iloc[0]) * (X_new[i] - X.iloc[0])
        elif X_new[i] >= X.iloc[-1]:
            Y_new.loc[i] = _function_value(number - 1, X.iloc[-1]) + _derivative_value(number - 1,X.iloc[-1]) * (X_new[i] - X.iloc[-1])
        else:
            # 找到当前输入价格对应的区间
            current_location = len(X[X <= X_new[i]])
            Y_new.loc[i] = _function_value(current_location, X_new[i])

    return Y_new

