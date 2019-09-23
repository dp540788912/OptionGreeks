import numpy as np
import pandas as pd
from datetime import datetime
from datetime import timedelta
from scipy.stats import norm
import warnings


def bound_adjustment(target_function, lower_bound, upper_bound):

    initial_search_range = upper_bound - lower_bound

    while target_function(lower_bound) * target_function(upper_bound) > 0:
        upper_value = target_function(upper_bound)
        lower_value = target_function(lower_bound)

        if 0 < upper_value <= lower_value or lower_value <= upper_value < 0:
            upper_bound = upper_bound + abs(initial_search_range)

        elif 0 < lower_value < upper_value or upper_value < lower_value < 0:
            lower_bound = lower_bound - abs(initial_search_range)

    return lower_bound, upper_bound


# 二分法
def bisection_iteration(target_function, lower_bound, upper_bound, max_iteration=100, tol=1e-7):

    # 首先判断求解区间是否为异号，若上下界函数取值不合理，调整上下界：
    if target_function(lower_bound) * target_function(upper_bound) > 0:
        lower_bound, upper_bound = bound_adjustment(target_function, lower_bound, upper_bound)

    iteration = 0
    mean = (upper_bound + lower_bound) / 2

    while abs(target_function((upper_bound + lower_bound) / 2)) >= tol and iteration <= max_iteration:

        if abs(target_function(mean)) <= tol:
            print('迭代成功收敛至指定精度范围内,迭代次数为：' + str(iteration))
            status = 0
            return mean, status

        if abs(target_function(upper_bound)) <= tol:
            print('迭代成功收敛至指定精度范围内,迭代次数为：' + str(iteration))
            status = 0
            return upper_bound, status

        if abs(target_function(lower_bound)) <= tol:
            print('迭代成功收敛至指定精度范围内,迭代次数为：' + str(iteration))
            status = 0
            return lower_bound, status

        elif target_function(mean) * target_function(upper_bound) < 0:
            lower_bound = mean
        else:
            upper_bound = mean

        mean = (upper_bound + lower_bound) / 2
        iteration += 1

    if iteration > max_iteration:
        status = 1
        print('迭代次数超出最大迭代次数，未收敛至指定精度，迭代结束')
        return mean, status
    else:
        status = 0
        print('迭代成功收敛至指定精度范围内,迭代次数为：' + str(iteration))
        return mean, status


def newton_iteration(target_function, derivative_function, initial_value, max_iteration=100, tol=1e-7):

    iteration = 0
    root = initial_value
    if abs(target_function(root)) <= tol:
        print('迭代成功收敛至指定精度范围内,迭代次数为：' + str(iteration))
        status = 0
        return root, status

    # 若初始解的导数为0,会导致牛顿法出现除数为0的情况，因此需要调整初始解
    if abs(derivative_function(root)) <= 1e-6:
        root = root+1

    while iteration <= max_iteration and abs(target_function(root)) > tol:
        next_guess = root - target_function(root) / derivative_function(root)

        # 若下一步迭代的解vega值小于上一步迭代解的1/100，则可判断牛顿法出现震荡，跳转至二分法求解
        if derivative_function(root) / derivative_function(next_guess) >= 100:
            print('vega值过小，牛顿法迭代出现震荡，跳转至二分法求解')
            root, status = bisection_iteration(target_function,root,next_guess)
            status = 2
            return root, status
        else:
            root = next_guess
            iteration += 1

    if iteration > max_iteration:
        status = 1
        print('迭代次数超出最大迭代次数，未收敛至指定精度，迭代结束')
        return root, status
    else:
        status = 0
        print('迭代成功收敛至指定精度范围内,迭代次数为：' + str(iteration))
        return root, status


# brent's method https://en.wikipedia.org/wiki/Brent%27s_method#Algorithm
def brent_iteration(target_function, x1, x0, max_iteration=100, tol=1e-7):

    # 首先判断求解区间是否为异号，若上下界函数取值不合理，调整上下界：
    if target_function(x0) * target_function(x1) > 0:
        x0, x1 = bound_adjustment(target_function, x0, x1)

    f_x0 = target_function(x0)
    f_x1 = target_function(x1)

    # 确保x1的函数值距离原点比x0近
    if abs(f_x0) < abs(f_x1):
        x0, x1 = x1, x0
        f_x0, f_x1 = f_x1, f_x0

    x2, f_x2 = x0, f_x0

    mflag = True
    iteration = 0

    while iteration < max_iteration and abs(target_function(x1)) > tol:
        f_x0 = target_function(x0)
        f_x1 = target_function(x1)
        f_x2 = target_function(x2)

        if f_x0 != f_x2 and f_x1 != f_x2:
            # inverse quadratic interpolation
            part1 = (x0 * f_x1 * f_x2) / ((f_x0 - f_x1) * (f_x0 - f_x2))
            part2 = (x1 * f_x0 * f_x2) / ((f_x1 - f_x0) * (f_x1 - f_x2))
            part3 = (x2 * f_x1 * f_x0) / ((f_x2 - f_x0) * (f_x2 - f_x1))
            next_guess = part1 + part2 + part3
        else:
            # linear interpolation
            next_guess = x1 - (f_x1 * (x1 - x0)) / (f_x1 - f_x0)

        # 若满足下述五个条件任一，使用二分法给出下一步迭代解
        condition1 = next_guess < ((3 * x0 + x1)/4) or next_guess > x1
        condition2 = mflag is True and (abs(next_guess - x1) >= abs(x1 - x2)/2)
        condition3 = mflag is False and (abs(next_guess-x1) >= abs(x2-d)/2)
        condition4 = mflag is True and abs(x1-x2) < tol
        condition5 = mflag is False and abs(x2-d) < tol

        if condition1 or condition2 or condition3 or condition4 or condition5:
            next_guess = (x1 + x0) / 2
            mflag = True

        else:
            mflag = False

        f_next = target_function(next_guess)
        d, x2 = x2, x1

        if f_x0 * f_next < 0:
            x1 = next_guess
        else:
            x0 = next_guess

        # 确保x1的函数值距离原点比x0近
        if abs(target_function(x0)) < abs(target_function(x1)):
            x0, x1 = x1, x0

        iteration += 1

    if iteration >= max_iteration:
        status = 1
        print('迭代次数超出最大迭代次数，未收敛至指定精度，迭代结束')
        return x1, status
    else:
        status = 0
        print('迭代成功收敛至指定精度范围内,迭代次数为：' + str(iteration))
        return x1, status

