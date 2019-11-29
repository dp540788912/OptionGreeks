import numpy as np
from pandas.core.generic import NDFrame
from scipy.stats import norm

_x_length = 2**23 - 1
_x_array = np.geomspace(1e-12, 5, _x_length)
_cdf_table_array = np.concatenate((-_x_array[::-1], np.array([0]),  _x_array,  np.array([np.inf])))
cdf_table_array = norm.cdf(_cdf_table_array)


def check_cdf(x):
    if np.isnan(x):
        return np.nan
    if isinstance(x, float) or isinstance(x, np.ndarray):
        return cdf_table_array[_cdf_table_array.searchsorted(x)]
    if isinstance(x, NDFrame):
        return x.apply(check_cdf)
    raise ValueError('type {} is not support!'.format(type(x)))
