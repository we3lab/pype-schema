import numpy as np
import pandas as pd
import scipy as sp  # noqa: F401


def get_change(variable, delta_t=1, split=False):
    """Converts cumulative value to rate-of-change value using finite differences
    Note: assumes rate of change at time t is equal to the difference between
    the value at time t+1 and t

    Parameters
    ----------
    variable : pandas.Series, numpy.ndarray
        variable to convert
    delta_t : int
        Time difference between two consecutive values of the variable (default is 1)
    split: bool
        Whether to split the variable into a negative change and a positive change

    Returns
    -------
    tuple, pandas.Series or numpy.ndarray
        Rate of change variable or tuple of netative, positive rate of change variable
    """
    variable = variable.values if isinstance(variable, pd.Series) else variable
    change = (variable[1:] - variable[:-1]) / delta_t
    change = np.concatenate([change, np.array([np.nan])])
    change_neg, change_pos = change.copy(), change.copy()
    change_neg[change_neg > 0] = 0
    change_neg = -change_neg
    change_pos[change_pos < 0] = 0
    if split:
        return change_neg, change_pos
    else:
        return change
