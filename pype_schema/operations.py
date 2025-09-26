import warnings
import numpy as np
import pandas as pd
import scipy as sp  # noqa: F401
from pint import DimensionalityError

from .units import u


class Constant:
    """Representation for a constant value that is not in the SCADA system.

    Only need for `Algebraic` mode since lambda expressions support constant
    values directly.

    Parameters
    ----------
    value : float
        The value of this constant at all timesteps

    Attributes
    ----------
    id : str

    value : float
        The value of this constant at all timesteps
    """

    def __init__(self, value, parent_id=None):
        self.id = "Constant(" + str(value) + ")"
        self.value = value
        self.parent_id = parent_id

    def __repr__(self):
        return (
            f"<pype_schema.operations.Constant id:{self.id} "
            f"value:{self.value} parent_id:{self.parent_id}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.value == other.value
            and self.parent_id == other.parent_id
        )

    def __lt__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        if self.value != other.value:
            return self.value < other.value
        elif self.id != other.id:
            return self.id < other.id
        elif self.parent_id != other.parent_id:
            if self.parent_id is None:
                return True
            elif other.parent_id is None:
                return False
            else:
                return self.parent_id < other.parent_id
        else:  # if all equal, less than is False
            return False


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


def binary_helper(operation, unit, prev_unit, totalized_mix=False):
    """Helper for parsing operations and checking units of binary operations

    Parameters
    ----------
    operation : ["+", "-", "*", "/"]
        Function to apply when combining tags.
        Supported functions are "+", "-", "*", and "/".

    unit : Unit
        Units for the right side of the operation, represented as a Pint unit.

    prev_unit : Unit
        Units for the left side of the operation, represented as a Pint unit.

    totalized_mix : bool
        Skip unit checking when there is a mix of totalized and detotalized variables.
        Default is False

    Raises
    ------
    ValueError
        When units are incompatible for addition or subtraction.
        When `operation` is unsupported.

    UserWarning
        When a mix of totalized and detotalized variables makes it impossible
        to verify unit compatibility

    Returns
    -------
    Unit
        Resulting Pint Unit from combining the `unit` and `prev_unit`
        according to `operation`
    """
    # convert unit and prev_unit to dimensionless if None
    unit = u.dimensionless if unit is None else unit
    prev_unit = u.dimensionless if prev_unit is None else prev_unit
    if operation == "+" or operation == "-":
        if unit != prev_unit:
            try:
                u.convert(1, unit, prev_unit)
            except DimensionalityError:
                if totalized_mix:
                    warnings.warn(
                        "Unable to verify units since there is a mix of "
                        "totalized and detotalized variables"
                    )
                else:
                    raise ValueError(
                        "Units for addition and subtraction must be compatible"
                    )
    elif operation == "*" or operation == "/":
        if operation == "/":
            prev_unit = prev_unit / unit
        else:
            prev_unit = prev_unit * unit
    else:
        raise ValueError("Unsupported operation " + operation)

    return prev_unit


def unary_helper(data, un_op):
    """Transform the given data according to the VirtualTag's unary operator

    Parameters
    ----------
    data : list, array, or Series
        a list, numpy array, or pandas Series of data to apply a unary operation to

    un_op : ["noop", "delta", "<<", ">>", "~", "-"]
        Supported operations are:
            "noop" : null operator, useful when
            skipping tags in a list of unary operations.

            "delta" : calculate the difference between
            the current timestep and previous timestep

            "<<" : shift all data left one timestep,
            so that the last time step will be NaN

            ">>" : shift all data right one timestep,
            so that the first time step will be NaN

            "~" : Boolean not

            "-" : unary negation

        Note that "delta", "<<", and ">>" return a timeseries padded
        with NaN so that it is the same length as input data

    Returns
    -------
    list, array, or Series
        numpy array of dataset trannsformed by unary operation
    """
    # allow for multiple unary operations to be performed sequentially
    result = None
    if isinstance(un_op, list):
        result = data.copy()
        for op in un_op:
            result = unary_helper(result, op)
    elif un_op == "noop":
        result = data.copy()
    elif un_op == "delta":
        r_shift = unary_helper(data, ">>")
        result = data - r_shift
    elif un_op == "-":
        if isinstance(data, list):
            result = [-x for x in data]
        elif isinstance(data, (np.ndarray, pd.Series)):
            result = -data
    elif un_op == "~":
        if isinstance(data, list):
            result = [not bool(x) for x in data]
        elif isinstance(data, (np.ndarray, pd.Series)):
            result = data == 0
    else:
        if isinstance(data, list):
            result = data.copy()
            if un_op == "<<":
                for i in range(len(data) - 1):
                    result[i] = data[i + 1]
                result[len(data) - 1] = float("nan")
            elif un_op == ">>":
                for i in range(1, len(data)):
                    result[i] = data[i - 1]
                result[0] = float("nan")
        elif isinstance(data, np.ndarray):
            result = data.copy().astype("float")
            if un_op == "<<":
                for i in range(len(data) - 1):
                    result[i] = data[i + 1]
                result[len(data) - 1] = np.nan
            elif un_op == ">>":
                for i in range(1, len(data)):
                    result[i] = data[i - 1]
                result[0] = np.nan
        elif isinstance(data, pd.Series):
            if un_op == "<<":
                result = data.shift(-1)
            elif un_op == ">>":
                result = data.shift(1)

    if result is None:
        raise TypeError("Data must be either a list, array, or Series")

    return result
