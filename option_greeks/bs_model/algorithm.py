
from scipy import optimize


class BoundException(Exception):
    """ target function has no bound """


def bound_adjustment(target_function, lower_bound, upper_bound):
    initial_search_range = abs(upper_bound - lower_bound)
    max_iter = 100
    _iter = 0

    upper_value = target_function(upper_bound)
    lower_value = target_function(lower_bound)

    while upper_value * lower_value > 0 and _iter < max_iter:

        if 0 < upper_value <= lower_value or lower_value <= upper_value < 0:
            upper_bound = upper_bound + (initial_search_range * (2 << _iter))
            upper_value = target_function(upper_bound)

        elif 0 < lower_value < upper_value or upper_value < lower_value < 0:
            lower_bound = lower_bound - (initial_search_range * (2 << _iter))
            lower_value = target_function(lower_bound)
        _iter += 1

    if _iter >= max_iter:
        raise BoundException("Max iteration reached!")
    return lower_bound, upper_bound


# brent's method https://en.wikipedia.org/wiki/Brent%27s_method#Algorithm
def brent_iteration(target_function, x0, x1, max_iteration=100, tol=1e-7):
    # 首先判断求解区间是否为异号，若上下界函数取值不合理，调整上下界：
    if target_function(x0) * target_function(x1) > 0:
        x0, x1 = bound_adjustment(target_function, x0, x1)

    x1 = optimize.brenth(target_function, x0, x1, xtol=tol, rtol=tol, maxiter=max_iteration)
    return x1


