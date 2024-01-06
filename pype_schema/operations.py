import numpy as np
import pandas as pd
import scipy as sp
import warnings

def get_change(variable, delta_t=1, split=False, pos_change=True, neg_change=True):
    """Converts cumulative value to rate-of-change value using finite differences
    Note: assumes rate of change at time t is equal to the difference between the value at time 
    t+1 and t

    Parameters
    ----------
    variable : pandas.Series, numpy.ndarray
        variable to convert
    delta_t : int 
        Time difference between two consecutive values of the variable (default is 1)
    split: bool
        Whether to split the variable into a negative change and a positive change
    neg_change: bool
        Whether to return the negative change variable
    pos_change: bool
        Whether to return the positive change variable

    Returns
    -------
    tuple, pandas.Series or numpy.ndarray
        Rate of change variable or tuple of netative, positive rate of change variable
    """
    variable = variable.values if isinstance(variable, pd.Series) else variable
    change = (variable[1:] - variable[:-1]) / delta_t
    change = np.concatenate([change, np.array([np.nan])])
    if split:
        change_neg, change_pos = change.copy(), change.copy()
        change_neg[change_neg > 0] = 0
        change_neg = - change_neg
        change_pos[change_pos < 0] = 0
        if pos_change and neg_change:
            return change_neg, change_pos
        elif neg_change:
            return change_neg 
        elif pos_change:
            return change_pos
        else:
            warnings.warn(
                """
                    Split is `True` but both pos_change and neg_change are `False` 
                    so no variable is returned
                """
            )
    else:
        return change 
    

