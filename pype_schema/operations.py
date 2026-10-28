import ast
import builtins
import importlib
import sys
import math  # noqa: F401
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


# ---------------------------------------------------------------------------
# Custom operations: validating and building user-supplied lambda strings
# ---------------------------------------------------------------------------
#
# A custom operation is a single lambda expression, written as a string in a
# file that is loaded at analysis time, e.g. "lambda x: x.diff().shift(-1)".
#
# Trust model. Operations are expected to come from the developer who created
# the file, or from another trusted party. The checks below stop accidents and
# make a tampered file hard to turn into arbitrary code execution; they are NOT
# a substitute for process-level isolation. In particular:
#
# - only the *syntax* and the *names/attributes* an expression can touch are
#   restricted. CPU time and memory used while the expression runs are not
#   (``9**9**9`` is valid, and so is ``[0] * 10**10``);
# - operations may modify the data passed to them in place (e.g.
#   ``inplace=True`` or ``out=``). This is permitted deliberately: it is a side
#   effect on the caller's data, not a way around the restrictions, so callers
#   should not assume their inputs are unchanged after an operation runs.
#
# Allow-lists. What an expression can reach is defined by the generated block at
# the bottom of this file, which scripts/generate_allowlist.py writes from the
# installed numpy, pandas, scipy, and math. It is a frozen, default-deny list: a
# function added by a newer library version is unreachable until the generator is
# re-run and the diff is reviewed. scripts/allowlist_report.md lists everything
# that was excluded and why. Do not edit the generated block by hand; a test fails
# if it differs from what the generator writes.
#
# ``apply`` / ``agg`` / ``aggregate`` / ``transform`` are special. Called with a
# string (``x.agg("sum")``) they look an attribute up by name, which would bypass
# the attribute allow-list. They are therefore allowed only when called directly
# with something whose method name is visible and checked: a lambda, a library
# function such as ``np.mean``, a builtin such as ``abs``, a string literal that
# names an allowed method, or a list/dict of those. A name built at runtime
# (``"to_" + "csv"``), or the method passed around as a value, is rejected. See
# `_is_function_spec`.

# Seat-belt limits on the size of an expression. Validation is linear in the
# size of the expression, so these are generous; they only exist to fail fast
# on pathological input. Tune as needed.
MAX_EXPRESSION_LENGTH = 100_000  # characters
MAX_EXPRESSION_NODES = 50_000  # AST nodes

# AST node types permitted anywhere inside a custom operation. This is the
# single source of truth: *every* node the validator visits is checked against
# it. Nodes the validator handles structurally rather than by visiting them
# (``arguments``/``arg`` of a lambda, ``comprehension`` clauses, and ``Store``
# contexts of comprehension targets) are deliberately absent, so they fail
# closed if they ever show up anywhere else.
ALLOWED_NODES = (
    ast.Expression,
    ast.Lambda,
    ast.Name,
    ast.Load,
    ast.Call,
    ast.keyword,
    ast.Attribute,
    ast.Subscript,
    ast.Slice,
    ast.Starred,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.Set,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
    ast.IfExp,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.Constant,
    # binary operators
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.MatMult,
    ast.BitAnd,
    ast.BitOr,
    ast.BitXor,
    ast.LShift,
    ast.RShift,
    # unary operators
    ast.USub,
    ast.UAdd,
    ast.Invert,
    ast.Not,
    # boolean operators
    ast.And,
    ast.Or,
    # comparison operators
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Is,
    ast.IsNot,
    ast.In,
    ast.NotIn,
)
if sys.version_info < (3, 9):  # pragma: no cover
    # before 3.9, subscripts wrap their index in Index/ExtSlice nodes
    ALLOWED_NODES += (ast.Index, ast.ExtSlice)

_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)

# Library names an expression may reference freely, and the library each one
# refers to (keys of ALLOWED_MODULE_MEMBERS).
MODULE_ALIASES = {
    "np": "numpy",
    "numpy": "numpy",
    "pd": "pandas",
    "pandas": "pandas",
    "sp": "scipy",
    "scipy": "scipy",
    "math": "math",
}
ALLOWED_NAMES = frozenset(MODULE_ALIASES)

# Builtins exposed to the evaluated expression. Deliberately excludes
# ``__import__``, ``eval``, ``exec``, ``compile``, ``open``, ``getattr``,
# ``setattr``, ``globals``, ``locals``, ``vars``, ``input``, etc.
SAFE_BUILTIN_NAMES = frozenset(
    {
        "abs",
        "all",
        "any",
        "bool",
        "dict",
        "divmod",
        "enumerate",
        "filter",
        "float",
        "int",
        "len",
        "list",
        "map",
        "max",
        "min",
        "pow",
        "range",
        "reversed",
        "round",
        "set",
        "sorted",
        "str",
        "sum",
        "tuple",
        "zip",
    }
)
SAFE_BUILTINS = {name: getattr(builtins, name) for name in SAFE_BUILTIN_NAMES}

# a library path is at most <library>.<submodule>.<submodule>, so attribute
# chains deeper than this can never refer to a library
_MAX_LIBRARY_DEPTH = 3


def count_args(func_str):
    """Count the arguments for a lambda function string
    without executing the function.

    Parameters
    ----------
    func_str : str
        A string representation of a lambda function

    Returns
    -------
    int :
        The lambda function's number of arguments

    Raises
    ------
    ValueError
        If `custom_operations` is not a single lambda string
    """
    tree = ast.parse(func_str.strip(), mode="eval")
    if not isinstance(tree.body, ast.Lambda):
        raise ValueError("`custom_operations` must be a single lambda expression")
    args = tree.body.args
    nargs = len(args.posonlyargs) + len(args.args) + len(args.kwonlyargs)
    nargs -= len(args.defaults)
    nargs -= sum(d is not None for d in args.kw_defaults)
    return nargs


def _is_bound(name, scopes):
    return any(name in scope for scope in scopes)


def _target_names(target):
    """Names bound by a comprehension target, rejecting unsafe targets.

    Only plain names (optionally nested in tuples/lists or prefixed by ``*``)
    may be bound. ``Attribute`` (``np.sum``) and ``Subscript`` (``x[0]``)
    targets are stores into existing objects, and would let an expression
    rebind attributes of shared modules or objects.
    """
    names = set()
    pending = [target]
    while pending:
        item = pending.pop()
        if isinstance(item, ast.Name):
            names.add(item.id)
        elif isinstance(item, (ast.Tuple, ast.List)):
            pending.extend(item.elts)
        elif isinstance(item, ast.Starred):
            pending.append(item.value)
        else:
            raise ValueError(
                "Assignment targets in `custom_operations` must be plain "
                f"names; `{type(item).__name__}` targets are not allowed"
            )
    return frozenset(names)


def _library_reference(expr, scopes):
    """``(path, namespace)`` if `expr` is a bare reference to an allowed library
    or library submodule, else ``(None, None)``.

    ``path`` is e.g. ``("scipy", "stats")`` and ``namespace`` is that entry of
    ALLOWED_MODULE_MEMBERS (``{"names": ..., "modules": ...}``). A library name
    that has been shadowed by a lambda parameter or comprehension variable is
    an ordinary object, not a library, so ``ALLOWED_ATTRIBUTES`` applies to it.
    """
    attrs = []
    while isinstance(expr, ast.Attribute):
        attrs.append(expr.attr)
        if len(attrs) > _MAX_LIBRARY_DEPTH:
            return None, None
        expr = expr.value
    if (
        not isinstance(expr, ast.Name)
        or expr.id not in MODULE_ALIASES
        or _is_bound(expr.id, scopes)
    ):
        return None, None
    path = (MODULE_ALIASES[expr.id],)
    namespace = ALLOWED_MODULE_MEMBERS[path[0]]
    for attr in reversed(attrs):
        namespace = namespace["modules"].get(attr)
        if namespace is None:
            return None, None
        path += (attr,)
    return path, namespace


def _is_function_spec(expr, scopes):
    """Whether `expr` is a function spec that cannot reach a method that is not allowed.

    Used for the argument of ``apply``/``agg``/``aggregate``/``transform``, which
    turn a *string* argument into an attribute lookup by name. Only these shapes
    are accepted, so the name is always visible here and always checked:

    - a lambda,
    - a library function or class, e.g. ``np.mean`` or ``sp.stats.zscore``,
    - a safe builtin, e.g. ``abs``,
    - a string literal that names an allowed method, e.g. ``"sum"`` (anything not
      in ALLOWED_ATTRIBUTES, such as ``"to_csv"``, is rejected),
    - a list/tuple of those, or a dict whose keys are literal labels and whose
      values are those (``{"a": np.mean, "b": ["min", "max"]}``).

    Names bound by a parameter or comprehension, calls, subscripts, string
    expressions such as ``"to_" + "csv"``, and arbitrary attributes are rejected,
    because the method they would name is not known here.
    """
    pending = [expr]
    while pending:
        item = pending.pop()
        if isinstance(item, ast.Lambda):
            continue
        if isinstance(item, ast.Constant):
            if not (isinstance(item.value, str) and item.value in ALLOWED_ATTRIBUTES):
                return False
        elif isinstance(item, ast.Name):
            if _is_bound(item.id, scopes) or item.id not in SAFE_BUILTIN_NAMES:
                return False
        elif isinstance(item, ast.Attribute):
            _, namespace = _library_reference(item.value, scopes)
            if namespace is None or item.attr not in namespace["names"]:
                return False
        elif isinstance(item, (ast.List, ast.Tuple)):
            pending.extend(item.elts)
        elif isinstance(item, ast.Dict):
            if any(not isinstance(key, ast.Constant) for key in item.keys):
                return False  # also rejects ``**`` unpacking, whose key is None
            pending.extend(item.values)
        else:
            return False
    return True


def _check_guarded_call(node, scopes):
    """Validate a direct call of a GUARDED_METHODS method, e.g. ``x.agg(np.mean)``."""
    method = node.func.attr
    hint = (
        f"`{method}` may only be called directly with a function written in the "
        "expression (a lambda, np.mean, abs, ...) or the name of an allowed method "
        "(e.g. 'sum') - not with a name that is built at runtime"
    )
    path, _ = _library_reference(node.func.value, scopes)
    root = node.func.value
    while isinstance(root, ast.Attribute):
        root = root.value
    if path is not None or (
        isinstance(root, ast.Name)
        and root.id in MODULE_ALIASES
        and not _is_bound(root.id, scopes)
    ):
        raise ValueError(
            f"{hint} (and not through a library, e.g. pd.DataFrame.{method})"
        )
    if any(isinstance(arg, ast.Starred) for arg in node.args) or any(
        keyword.arg is None for keyword in node.keywords
    ):
        raise ValueError(f"{hint}; `*` / `**` arguments are not allowed here")
    if node.args:
        func_arg = node.args[0]
    else:
        keywords = [keyword for keyword in node.keywords if keyword.arg == "func"]
        func_arg = keywords[0].value if keywords else None
    if func_arg is None or not _is_function_spec(func_arg, scopes):
        raise ValueError(hint)


def _validate_ast(tree):
    """Validate a parsed custom operation, raising ValueError if it is unsafe.

    Returns the set of library paths the expression refers to (e.g.
    ``{("numpy",), ("scipy",), ("scipy", "stats")}``), so only those libraries
    need to be imported to run it.

    Walks the tree with an explicit stack instead of recursion, so the depth of
    an expression (e.g. a sum of several hundred terms) cannot exhaust the
    Python call stack. Each stack entry carries the lexical scopes (a tuple of
    frozensets of bound names) in force for that node, so names bound by a
    lambda's parameters or a comprehension's targets are bound only inside
    that lambda/comprehension, and nested lambdas get their own scope.
    """
    nodes_seen = 0
    libraries_used = set()
    stack = [(tree, ())]
    while stack:
        node, scopes = stack.pop()

        nodes_seen += 1
        if nodes_seen > MAX_EXPRESSION_NODES:
            raise ValueError(
                "`custom_operations` expression is too large "
                f"(more than {MAX_EXPRESSION_NODES} syntax nodes)"
            )
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(
                f"Disallowed syntax in `custom_operations`: {type(node).__name__}"
            )

        if isinstance(node, ast.Lambda):
            args = node.args
            if args.defaults or any(d is not None for d in args.kw_defaults):
                raise ValueError(
                    "Default argument values are not allowed in `custom_operations`"
                )
            params = {
                arg.arg for arg in (args.posonlyargs + args.args + args.kwonlyargs)
            }
            if args.vararg is not None:
                params.add(args.vararg.arg)
            if args.kwarg is not None:
                params.add(args.kwarg.arg)
            stack.append((node.body, scopes + (frozenset(params),)))

        elif isinstance(node, _COMPREHENSIONS):
            pending = []
            bound = frozenset()
            for generator in node.generators:
                if generator.is_async:
                    raise ValueError(
                        "Asynchronous comprehensions are not allowed in "
                        "`custom_operations`"
                    )
                # an iterable is evaluated before its own target is bound, and
                # sees only the targets of the generators before it
                pending.append((generator.iter, scopes + (bound,)))
                bound = bound | _target_names(generator.target)
                pending.extend((cond, scopes + (bound,)) for cond in generator.ifs)
            if isinstance(node, ast.DictComp):
                elements = [node.key, node.value]
            else:
                elements = [node.elt]
            pending.extend((element, scopes + (bound,)) for element in elements)
            stack.extend(reversed(pending))  # so they pop in source order

        elif isinstance(node, ast.Attribute):
            if not isinstance(node.ctx, ast.Load):
                raise ValueError(
                    "Assigning to attributes is not allowed in `custom_operations`"
                )
            if node.attr.startswith("_"):
                raise ValueError(
                    f"Access to attribute `{node.attr}` is not allowed "
                    "in `custom_operations`"
                )
            if node.attr in GUARDED_METHODS:
                raise ValueError(
                    f"`{node.attr}` may only be called directly on an object, with a "
                    "function written in the expression (a lambda, np.mean, abs, ...) or "
                    "the name of an allowed method, e.g. x.apply(lambda v: v + 1) or "
                    "x.agg('sum'); it cannot be passed around as a value"
                )
            path, namespace = _library_reference(node.value, scopes)
            if namespace is None:
                if node.attr not in ALLOWED_ATTRIBUTES:
                    raise ValueError(
                        f"`{node.attr}` is not an allowed attribute in "
                        "`custom_operations` (see ALLOWED_ATTRIBUTES)"
                    )
            elif node.attr in namespace["modules"]:
                libraries_used.add(path + (node.attr,))
            elif node.attr not in namespace["names"]:
                raise ValueError(
                    f"`{node.attr}` is not an allowed member of this library in "
                    "`custom_operations` (see ALLOWED_MODULE_MEMBERS)"
                )
            stack.append((node.value, scopes))

        elif isinstance(node, ast.Name):
            if not isinstance(node.ctx, ast.Load):
                raise ValueError(
                    "Assigning to names is not allowed in `custom_operations`"
                )
            name = node.id
            if _is_bound(name, scopes):
                continue
            if name.startswith("_"):
                raise ValueError(
                    f"Reference to `{name}` is not allowed in `custom_operations`"
                )
            if name not in ALLOWED_NAMES and name not in SAFE_BUILTIN_NAMES:
                raise ValueError(
                    f"Unknown name `{name}` in `custom_operations`; only "
                    f"{sorted(ALLOWED_NAMES)} and basic builtins are allowed"
                )
            if name in MODULE_ALIASES:
                libraries_used.add((MODULE_ALIASES[name],))

        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in GUARDED_METHODS
        ):
            # x.apply(...) etc.: the method is checked here, in the context of
            # the call, rather than as a free-standing attribute
            _check_guarded_call(node, scopes)
            children = [node.func.value, *node.args, *node.keywords]
            stack.extend((child, scopes) for child in reversed(children))

        else:
            children = list(ast.iter_child_nodes(node))
            stack.extend((child, scopes) for child in reversed(children))

    return libraries_used


def _parse_custom_operation(func_str):
    """Parse and validate a custom operation string.

    Returns ``(tree, libraries_used)``. Both `validate_custom_operation` and
    `build_custom_operation` go through this single parse so that the exact tree
    that was validated is also the one that gets compiled -- there is no
    "validate one string, evaluate another" gap (e.g. differing leading
    whitespace between validation and ``eval``).
    """
    if not isinstance(func_str, str):
        raise TypeError(
            f"`custom_operations` must be a string, not {type(func_str).__name__}"
        )
    if len(func_str) > MAX_EXPRESSION_LENGTH:
        raise ValueError(
            "`custom_operations` expression is too long "
            f"(more than {MAX_EXPRESSION_LENGTH} characters)"
        )
    try:
        tree = ast.parse(func_str.strip(), mode="eval")
    except (RecursionError, MemoryError) as error:
        raise ValueError(
            "`custom_operations` expression is too deeply nested or too large"
        ) from error
    if not isinstance(tree.body, ast.Lambda):
        raise ValueError("`custom_operations` must be a single lambda expression")
    return tree, _validate_ast(tree)


def _resolve_namespace(path):
    """The module object for a library path such as ``("numpy", "emath")``.

    Some public namespaces (numpy.emath) are attributes, not importable module
    paths, so walk attributes first and fall back to importing.
    """
    obj = importlib.import_module(path[0])
    for i, part in enumerate(path[1:], start=1):
        try:
            obj = getattr(obj, part)
        except AttributeError:
            obj = importlib.import_module(".".join(path[: i + 1]))
    return obj


def validate_custom_operation(func_str):
    """Validate that a custom operation string is a safe lambda expression.

    Parses `func_str` and walks its abstract syntax tree with a scope-aware
    validator, enforcing allow-lists so the expression can use
    pandas/numpy/scipy/math (method calls, attribute access, subscripts,
    comprehensions, nested lambdas, and the functions listed in
    ``ALLOWED_MODULE_MEMBERS``) while remaining unable to execute arbitrary
    code. It rejects:

    - input longer than ``MAX_EXPRESSION_LENGTH`` characters or containing more
      than ``MAX_EXPRESSION_NODES`` syntax nodes,
    - any syntax node outside ``ALLOWED_NODES`` (e.g. assignments, f-strings),
    - default argument values (they are evaluated when the lambda is built and
      would bypass the free-name check),
    - assignment targets that are not plain names (an ``Attribute``/``Subscript``
      target such as ``np.sum`` could rebind a shared module),
    - any attribute whose name begins with ``_`` (blocks dunder traversal such
      as ``__class__`` / ``__globals__`` / ``__subclasses__``),
    - any member of ``np``/``pd``/``sp``/``math`` (or of one of their
      submodules) that is not in ``ALLOWED_MODULE_MEMBERS``, and any attribute of
      any other object that is not in ``ALLOWED_ATTRIBUTES`` (default-deny, so
      code/IO entry points such as ``read_pickle``, ``load``, ``eval``,
      ``query`` are never reachable, nor is any future addition to the
      libraries),
    - ``apply``/``agg``/``aggregate``/``transform`` unless called directly with a
      function that is visible in the expression, or the name of an allowed method
      (never a name that is built at runtime or passed in),
    - any free (unbound) name that is not in `ALLOWED_NAMES` or the safe
      builtin set (blocks ``__import__``, ``open``, ``getattr``, ``eval`` ...).

    Names bound by lambda parameters and comprehension targets are scoped, so a
    name bound inside a comprehension is not treated as bound outside it, and a
    library name that has been shadowed by a parameter (``lambda np: ...``) is
    treated as an ordinary object.

    The validator is iterative, so the nesting depth of an expression does not
    depend on the Python recursion limit.

    This is validation only; use `build_custom_operation` to additionally
    compile the expression in a restricted namespace. See the comment above
    ALLOWED_NODES for what validation deliberately does not restrict (CPU/memory use,
    in-place modification of arguments).

    Parameters
    ----------
    func_str : str
        A string representation of a lambda function to validate

    Returns
    -------
    str :
        The original `func_str`, unchanged, when validation succeeds

    Raises
    ------
    TypeError
        When `func_str` is not a string
    ValueError
        When `func_str` is not a single lambda expression, is too large or too
        deeply nested, or contains syntax, names, or attributes that are not
        allowed
    SyntaxError
        When `func_str` is not valid Python syntax
    """
    _parse_custom_operation(func_str)
    return func_str


def build_custom_operation(func_str):
    """Validate a custom operation string and compile it to a callable.

    The expression is validated and compiled from a single parsed AST (so the
    validated tree is exactly the one evaluated), then evaluated in a
    restricted namespace whose builtins are limited to `SAFE_BUILTINS` and
    whose only module globals are the libraries the expression actually uses
    (so e.g. scipy is only imported if the expression refers to it).

    The restricted namespace is defense in depth, not a security boundary: the
    AST allow-lists enforced by `validate_custom_operation` are the primary
    control. Operations are expected to come from trusted authors (see the
    comment above ALLOWED_NODES).

    Parameters
    ----------
    func_str : str
        A string representation of a lambda function

    Returns
    -------
    callable :
        The compiled lambda function

    Raises
    ------
    TypeError
        When `func_str` is not a string
    ValueError
        When `func_str` fails `validate_custom_operation`, or is too deeply
        nested to compile
    SyntaxError
        When `func_str` is not valid Python syntax
    ImportError
        When a library the expression refers to is not installed
    """
    tree, libraries_used = _parse_custom_operation(func_str)
    try:
        code = compile(tree, "<custom_operation>", "eval", dont_inherit=True)
    except (RecursionError, MemoryError) as error:
        raise ValueError(
            "`custom_operations` expression is too deeply nested or too large"
        ) from error

    # import exactly what the expression refers to; lazily-loaded submodules
    # (scipy.stats, ...) are imported here rather than relied on to appear on
    # attribute access
    modules = {path: _resolve_namespace(path) for path in libraries_used}
    safe_globals = {"__builtins__": SAFE_BUILTINS}
    for alias, library in MODULE_ALIASES.items():
        if (library,) in modules:
            safe_globals[alias] = modules[(library,)]

    return eval(code, safe_globals, {})


# BEGIN GENERATED ALLOW-LISTS -- written by generate_allowlist.py; do not edit by hand.
# Generated with Python 3.12.3, numpy 2.4.4, pandas 3.0.2, scipy 1.17.1.
# To change a decision, edit the rules in generate_allowlist.py and re-run it, then
# review the diff. allowlist_report.md lists everything that was excluded and why.
# A test fails if this block differs from what the generator writes.
# fmt: off


def _names(space_separated):
    return frozenset(space_separated.split())


def _ns(names, modules=None):
    """One namespace: the members reachable as ``lib.name`` and its submodules."""
    return {"names": _names(names), "modules": modules or {}}


# What may be reached through a library name (np.sqrt, sp.stats.zscore, ...).
ALLOWED_MODULE_MEMBERS = {
    "math": _ns(
        """
        acos
        acosh
        asin
        asinh
        atan
        atan2
        atanh
        cbrt
        ceil
        comb
        copysign
        cos
        cosh
        degrees
        dist
        e
        erf
        erfc
        exp
        exp2
        expm1
        fabs
        factorial
        floor
        fmod
        frexp
        fsum
        gamma
        gcd
        hypot
        inf
        isclose
        isfinite
        isinf
        isnan
        isqrt
        lcm
        ldexp
        lgamma
        log
        log10
        log1p
        log2
        modf
        nan
        nextafter
        perm
        pi
        pow
        prod
        radians
        remainder
        sin
        sinh
        sqrt
        sumprod
        tan
        tanh
        tau
        trunc
        ulp
        """
    ),
    "numpy": _ns(
        """
        False_
        True_
        abs
        absolute
        acos
        acosh
        add
        all
        allclose
        amax
        amin
        angle
        any
        append
        apply_along_axis
        apply_over_axes
        arange
        arccos
        arccosh
        arcsin
        arcsinh
        arctan
        arctan2
        arctanh
        argmax
        argmin
        argpartition
        argsort
        argwhere
        around
        array
        array2string
        array_equal
        array_equiv
        array_repr
        array_split
        array_str
        asanyarray
        asarray
        asarray_chkfinite
        ascontiguousarray
        asfortranarray
        asin
        asinh
        asmatrix
        astype
        atan
        atan2
        atanh
        atleast_1d
        atleast_2d
        atleast_3d
        average
        bartlett
        base_repr
        binary_repr
        bincount
        bitwise_and
        bitwise_count
        bitwise_invert
        bitwise_left_shift
        bitwise_not
        bitwise_or
        bitwise_right_shift
        bitwise_xor
        blackman
        block
        bool
        bool_
        broadcast
        broadcast_arrays
        broadcast_shapes
        broadcast_to
        busday_count
        busday_offset
        busdaycalendar
        byte
        bytes_
        c_
        can_cast
        cbrt
        cdouble
        ceil
        character
        choose
        clip
        clongdouble
        column_stack
        common_type
        complex128
        complex256
        complex64
        complexfloating
        compress
        concat
        concatenate
        conj
        conjugate
        convolve
        copy
        copysign
        copyto
        corrcoef
        correlate
        cos
        cosh
        count_nonzero
        cov
        cross
        csingle
        cumprod
        cumsum
        cumulative_prod
        cumulative_sum
        datetime64
        datetime_as_string
        datetime_data
        deg2rad
        degrees
        delete
        diag
        diag_indices
        diag_indices_from
        diagflat
        diagonal
        diff
        digitize
        divide
        divmod
        dot
        double
        dsplit
        dstack
        dtype
        e
        ediff1d
        einsum
        einsum_path
        empty
        empty_like
        equal
        euler_gamma
        exp
        exp2
        expand_dims
        expm1
        extract
        eye
        fabs
        fill_diagonal
        finfo
        fix
        flatiter
        flatnonzero
        flexible
        flip
        fliplr
        flipud
        float128
        float16
        float32
        float64
        float_power
        floating
        floor
        floor_divide
        fmax
        fmin
        fmod
        format_float_positional
        format_float_scientific
        frexp
        frombuffer
        fromfunction
        fromiter
        frompyfunc
        fromstring
        full
        full_like
        gcd
        generic
        geomspace
        get_printoptions
        getbufsize
        geterr
        geterrcall
        gradient
        greater
        greater_equal
        half
        hamming
        hanning
        heaviside
        histogram
        histogram2d
        histogram_bin_edges
        histogramdd
        hsplit
        hstack
        hypot
        i0
        identity
        iinfo
        imag
        index_exp
        indices
        inexact
        inf
        inner
        insert
        int16
        int32
        int64
        int8
        int_
        intc
        integer
        interp
        intersect1d
        intp
        invert
        is_busday
        isclose
        iscomplex
        iscomplexobj
        isdtype
        isfinite
        isfortran
        isin
        isinf
        isnan
        isnat
        isneginf
        isposinf
        isreal
        isrealobj
        isscalar
        issubdtype
        iterable
        ix_
        kaiser
        kron
        lcm
        ldexp
        left_shift
        less
        less_equal
        lexsort
        linspace
        little_endian
        log
        log10
        log1p
        log2
        logaddexp
        logaddexp2
        logical_and
        logical_not
        logical_or
        logical_xor
        logspace
        long
        longdouble
        longlong
        mask_indices
        matmul
        matrix
        matrix_transpose
        matvec
        max
        maximum
        may_share_memory
        mean
        median
        meshgrid
        mgrid
        min
        min_scalar_type
        minimum
        mintypecode
        mod
        modf
        moveaxis
        multiply
        nan
        nan_to_num
        nanargmax
        nanargmin
        nancumprod
        nancumsum
        nanmax
        nanmean
        nanmedian
        nanmin
        nanpercentile
        nanprod
        nanquantile
        nanstd
        nansum
        nanvar
        ndarray
        ndenumerate
        ndim
        ndindex
        nditer
        negative
        nested_iters
        newaxis
        nextafter
        nonzero
        not_equal
        number
        object_
        ogrid
        ones
        ones_like
        outer
        packbits
        pad
        partition
        percentile
        permute_dims
        pi
        piecewise
        place
        poly
        poly1d
        polyadd
        polyder
        polydiv
        polyfit
        polyint
        polymul
        polysub
        polyval
        positive
        pow
        power
        prod
        promote_types
        ptp
        put
        put_along_axis
        putmask
        quantile
        r_
        rad2deg
        radians
        ravel
        ravel_multi_index
        real
        real_if_close
        recarray
        reciprocal
        record
        remainder
        repeat
        require
        reshape
        resize
        result_type
        right_shift
        rint
        roll
        rollaxis
        roots
        rot90
        round
        row_stack
        s_
        searchsorted
        select
        setdiff1d
        setxor1d
        shape
        shares_memory
        short
        sign
        signbit
        signedinteger
        sin
        sinc
        single
        sinh
        size
        sort
        sort_complex
        spacing
        split
        sqrt
        square
        squeeze
        stack
        std
        str_
        subtract
        sum
        swapaxes
        take
        take_along_axis
        tan
        tanh
        tensordot
        tile
        timedelta64
        trace
        transpose
        trapezoid
        tri
        tril
        tril_indices
        tril_indices_from
        trim_zeros
        triu
        triu_indices
        triu_indices_from
        true_divide
        trunc
        typename
        ubyte
        ufunc
        uint
        uint16
        uint32
        uint64
        uint8
        uintc
        uintp
        ulong
        ulonglong
        union1d
        unique
        unique_all
        unique_counts
        unique_inverse
        unique_values
        unpackbits
        unravel_index
        unsignedinteger
        unstack
        unwrap
        ushort
        vander
        var
        vdot
        vecdot
        vecmat
        vectorize
        void
        vsplit
        vstack
        where
        zeros
        zeros_like
        """,
        {
            "char": _ns(
                """
                add
                array
                asarray
                capitalize
                center
                chararray
                compare_chararrays
                count
                decode
                encode
                endswith
                equal
                expandtabs
                find
                greater
                greater_equal
                index
                isalnum
                isalpha
                isdecimal
                isdigit
                islower
                isnumeric
                isspace
                istitle
                isupper
                join
                less
                less_equal
                ljust
                lower
                lstrip
                mod
                multiply
                not_equal
                partition
                replace
                rfind
                rindex
                rjust
                rpartition
                rsplit
                rstrip
                split
                splitlines
                startswith
                str_len
                strip
                swapcase
                title
                translate
                upper
                zfill
                """
            ),
            "emath": _ns(
                """
                arccos
                arcsin
                arctanh
                log
                log10
                log2
                logn
                power
                sqrt
                """
            ),
            "fft": _ns(
                """
                fft
                fft2
                fftfreq
                fftn
                fftshift
                hfft
                ifft
                ifft2
                ifftn
                ifftshift
                ihfft
                irfft
                irfft2
                irfftn
                rfft
                rfft2
                rfftfreq
                rfftn
                """
            ),
            "linalg": _ns(
                """
                LinAlgError
                cholesky
                cond
                cross
                det
                diagonal
                eig
                eigh
                eigvals
                eigvalsh
                inv
                lstsq
                matmul
                matrix_norm
                matrix_power
                matrix_rank
                matrix_transpose
                multi_dot
                norm
                outer
                pinv
                qr
                slogdet
                solve
                svd
                svdvals
                tensordot
                tensorinv
                tensorsolve
                trace
                vecdot
                vector_norm
                """
            ),
            "ma": _ns(
                """
                MAError
                MaskError
                MaskType
                MaskedArray
                abs
                absolute
                add
                all
                allclose
                allequal
                alltrue
                amax
                amin
                angle
                anom
                anomalies
                any
                append
                apply_along_axis
                apply_over_axes
                arange
                arccos
                arccosh
                arcsin
                arcsinh
                arctan
                arctan2
                arctanh
                argmax
                argmin
                argsort
                around
                array
                asanyarray
                asarray
                atleast_1d
                atleast_2d
                atleast_3d
                average
                bitwise_and
                bitwise_or
                bitwise_xor
                bool_
                ceil
                choose
                clip
                clump_masked
                clump_unmasked
                column_stack
                common_fill_value
                compress
                compress_cols
                compress_nd
                compress_rowcols
                compress_rows
                compressed
                concatenate
                conjugate
                convolve
                copy
                corrcoef
                correlate
                cos
                cosh
                count
                count_masked
                cov
                cumprod
                cumsum
                default_fill_value
                diag
                diagflat
                diagonal
                diff
                divide
                dot
                dstack
                ediff1d
                empty
                empty_like
                equal
                exp
                expand_dims
                fabs
                filled
                fix_invalid
                flatnotmasked_contiguous
                flatnotmasked_edges
                flatten_mask
                flatten_structured_array
                floor
                floor_divide
                fmod
                frombuffer
                fromflex
                fromfunction
                getdata
                getmask
                getmaskarray
                greater
                greater_equal
                harden_mask
                hsplit
                hstack
                hypot
                identity
                in1d
                indices
                inner
                innerproduct
                intersect1d
                isMA
                isMaskedArray
                is_mask
                is_masked
                isarray
                isin
                left_shift
                less
                less_equal
                log
                log10
                log2
                logical_and
                logical_not
                logical_or
                logical_xor
                make_mask
                make_mask_descr
                make_mask_none
                mask_cols
                mask_or
                mask_rowcols
                mask_rows
                masked
                masked_all
                masked_all_like
                masked_array
                masked_equal
                masked_greater
                masked_greater_equal
                masked_inside
                masked_invalid
                masked_less
                masked_less_equal
                masked_not_equal
                masked_object
                masked_outside
                masked_singleton
                masked_values
                masked_where
                max
                maximum
                maximum_fill_value
                mean
                median
                min
                minimum
                minimum_fill_value
                mod
                mr_
                multiply
                mvoid
                ndenumerate
                ndim
                negative
                nomask
                nonzero
                not_equal
                notmasked_contiguous
                notmasked_edges
                ones
                ones_like
                outer
                outerproduct
                polyfit
                power
                prod
                product
                ptp
                put
                putmask
                ravel
                remainder
                repeat
                reshape
                resize
                right_shift
                round
                round_
                row_stack
                set_fill_value
                setdiff1d
                setxor1d
                shape
                sin
                sinh
                size
                soften_mask
                sometrue
                sort
                sqrt
                squeeze
                stack
                std
                subtract
                sum
                swapaxes
                take
                tan
                tanh
                trace
                transpose
                true_divide
                union1d
                unique
                vander
                var
                vstack
                where
                zeros
                zeros_like
                """
            ),
            "polynomial": _ns(
                """
                Chebyshev
                Hermite
                HermiteE
                Laguerre
                Legendre
                Polynomial
                """,
                {
                    "chebyshev": _ns(
                        """
                        ABCPolyBase
                        Chebyshev
                        cheb2poly
                        chebadd
                        chebcompanion
                        chebder
                        chebdiv
                        chebdomain
                        chebfit
                        chebfromroots
                        chebgauss
                        chebgrid2d
                        chebgrid3d
                        chebint
                        chebinterpolate
                        chebline
                        chebmul
                        chebmulx
                        chebone
                        chebpow
                        chebpts1
                        chebpts2
                        chebroots
                        chebsub
                        chebtrim
                        chebval
                        chebval2d
                        chebval3d
                        chebvander
                        chebvander2d
                        chebvander3d
                        chebweight
                        chebx
                        chebzero
                        poly2cheb
                        """
                    ),
                    "hermite": _ns(
                        """
                        ABCPolyBase
                        Hermite
                        herm2poly
                        hermadd
                        hermcompanion
                        hermder
                        hermdiv
                        hermdomain
                        hermfit
                        hermfromroots
                        hermgauss
                        hermgrid2d
                        hermgrid3d
                        hermint
                        hermline
                        hermmul
                        hermmulx
                        hermone
                        hermpow
                        hermroots
                        hermsub
                        hermtrim
                        hermval
                        hermval2d
                        hermval3d
                        hermvander
                        hermvander2d
                        hermvander3d
                        hermweight
                        hermx
                        hermzero
                        poly2herm
                        """
                    ),
                    "hermite_e": _ns(
                        """
                        ABCPolyBase
                        HermiteE
                        herme2poly
                        hermeadd
                        hermecompanion
                        hermeder
                        hermediv
                        hermedomain
                        hermefit
                        hermefromroots
                        hermegauss
                        hermegrid2d
                        hermegrid3d
                        hermeint
                        hermeline
                        hermemul
                        hermemulx
                        hermeone
                        hermepow
                        hermeroots
                        hermesub
                        hermetrim
                        hermeval
                        hermeval2d
                        hermeval3d
                        hermevander
                        hermevander2d
                        hermevander3d
                        hermeweight
                        hermex
                        hermezero
                        poly2herme
                        """
                    ),
                    "laguerre": _ns(
                        """
                        ABCPolyBase
                        Laguerre
                        lag2poly
                        lagadd
                        lagcompanion
                        lagder
                        lagdiv
                        lagdomain
                        lagfit
                        lagfromroots
                        laggauss
                        laggrid2d
                        laggrid3d
                        lagint
                        lagline
                        lagmul
                        lagmulx
                        lagone
                        lagpow
                        lagroots
                        lagsub
                        lagtrim
                        lagval
                        lagval2d
                        lagval3d
                        lagvander
                        lagvander2d
                        lagvander3d
                        lagweight
                        lagx
                        lagzero
                        poly2lag
                        """
                    ),
                    "legendre": _ns(
                        """
                        ABCPolyBase
                        Legendre
                        leg2poly
                        legadd
                        legcompanion
                        legder
                        legdiv
                        legdomain
                        legfit
                        legfromroots
                        leggauss
                        leggrid2d
                        leggrid3d
                        legint
                        legline
                        legmul
                        legmulx
                        legone
                        legpow
                        legroots
                        legsub
                        legtrim
                        legval
                        legval2d
                        legval3d
                        legvander
                        legvander2d
                        legvander3d
                        legweight
                        legx
                        legzero
                        poly2leg
                        """
                    ),
                    "polynomial": _ns(
                        """
                        ABCPolyBase
                        Polynomial
                        polyadd
                        polycompanion
                        polyder
                        polydiv
                        polydomain
                        polyfit
                        polyfromroots
                        polygrid2d
                        polygrid3d
                        polyint
                        polyline
                        polymul
                        polymulx
                        polyone
                        polypow
                        polyroots
                        polysub
                        polytrim
                        polyval
                        polyval2d
                        polyval3d
                        polyvalfromroots
                        polyvander
                        polyvander2d
                        polyvander3d
                        polyx
                        polyzero
                        """
                    ),
                },
            ),
            "random": _ns(
                """
                BitGenerator
                Generator
                MT19937
                PCG64
                PCG64DXSM
                Philox
                RandomState
                SFC64
                SeedSequence
                beta
                binomial
                bytes
                chisquare
                choice
                default_rng
                dirichlet
                exponential
                f
                gamma
                geometric
                get_bit_generator
                get_state
                gumbel
                hypergeometric
                laplace
                logistic
                lognormal
                logseries
                multinomial
                multivariate_normal
                negative_binomial
                noncentral_chisquare
                noncentral_f
                normal
                pareto
                permutation
                poisson
                power
                rand
                randint
                randn
                random
                random_integers
                random_sample
                ranf
                rayleigh
                sample
                shuffle
                standard_cauchy
                standard_exponential
                standard_gamma
                standard_normal
                standard_t
                triangular
                uniform
                vonmises
                wald
                weibull
                zipf
                """
            ),
            "strings": _ns(
                """
                add
                capitalize
                center
                count
                decode
                encode
                endswith
                equal
                expandtabs
                find
                greater
                greater_equal
                index
                isalnum
                isalpha
                isdecimal
                isdigit
                islower
                isnumeric
                isspace
                istitle
                isupper
                less
                less_equal
                ljust
                lower
                lstrip
                mod
                multiply
                not_equal
                partition
                replace
                rfind
                rindex
                rjust
                rpartition
                rstrip
                slice
                startswith
                str_len
                strip
                swapcase
                title
                translate
                upper
                zfill
                """
            ),
        },
    ),
    "pandas": _ns(
        """
        ArrowDtype
        BooleanDtype
        Categorical
        CategoricalDtype
        CategoricalIndex
        DataFrame
        DateOffset
        DatetimeIndex
        DatetimeTZDtype
        Flags
        Float32Dtype
        Float64Dtype
        Grouper
        Index
        IndexSlice
        Int16Dtype
        Int32Dtype
        Int64Dtype
        Int8Dtype
        Interval
        IntervalDtype
        IntervalIndex
        MultiIndex
        NA
        NaT
        Period
        PeriodDtype
        PeriodIndex
        RangeIndex
        Series
        SparseDtype
        StringDtype
        Timedelta
        TimedeltaIndex
        Timestamp
        UInt16Dtype
        UInt32Dtype
        UInt64Dtype
        UInt8Dtype
        array
        bdate_range
        concat
        cut
        date_range
        factorize
        from_dummies
        get_dummies
        infer_freq
        interval_range
        isna
        isnull
        json_normalize
        lreshape
        melt
        merge
        merge_asof
        merge_ordered
        notna
        notnull
        period_range
        pivot
        qcut
        timedelta_range
        to_datetime
        to_numeric
        to_timedelta
        unique
        wide_to_long
        """,
        {
            "offsets": _ns(
                """
                BDay
                BHalfYearBegin
                BHalfYearEnd
                BMonthBegin
                BMonthEnd
                BQuarterBegin
                BQuarterEnd
                BYearBegin
                BYearEnd
                BaseOffset
                BusinessDay
                BusinessHour
                BusinessMonthBegin
                BusinessMonthEnd
                CBMonthBegin
                CBMonthEnd
                CDay
                CustomBusinessDay
                CustomBusinessHour
                CustomBusinessMonthBegin
                CustomBusinessMonthEnd
                DateOffset
                Day
                Easter
                FY5253
                FY5253Quarter
                HalfYearBegin
                HalfYearEnd
                Hour
                LastWeekOfMonth
                Micro
                Milli
                Minute
                MonthBegin
                MonthEnd
                Nano
                QuarterBegin
                QuarterEnd
                Second
                SemiMonthBegin
                SemiMonthEnd
                Tick
                Week
                WeekOfMonth
                YearBegin
                YearEnd
                """
            ),
        },
    ),
    "scipy": _ns(
        """

        """,
        {
            "cluster": _ns(
                """

                """,
                {
                    "hierarchy": _ns(
                        """
                        ClusterNode
                        ClusterWarning
                        DisjointSet
                        array_namespace
                        average
                        centroid
                        complete
                        cophenet
                        correspond
                        cut_tree
                        fcluster
                        fclusterdata
                        from_mlab_linkage
                        inconsistent
                        int_floor
                        is_dask
                        is_isomorphic
                        is_lazy_array
                        is_monotonic
                        is_valid_im
                        is_valid_linkage
                        lazy_cython
                        leaders
                        leaves_list
                        linkage
                        maxRstat
                        maxdists
                        maxinconsts
                        median
                        num_obs_linkage
                        optimal_leaf_ordering
                        single
                        to_mlab_linkage
                        to_tree
                        ward
                        weighted
                        xp_capabilities
                        xp_copy
                        """
                    ),
                    "vq": _ns(
                        """
                        ClusterError
                        array_namespace
                        cdist
                        check_random_state
                        is_lazy_array
                        kmeans
                        kmeans2
                        py_vq
                        rng_integers
                        vq
                        whiten
                        xp_capabilities
                        xp_copy
                        xp_size
                        """
                    ),
                },
            ),
            "constants": _ns(
                """
                Avogadro
                Boltzmann
                Btu
                Btu_IT
                Btu_th
                ConstantWarning
                G
                Julian_year
                N_A
                Planck
                R
                Rydberg
                Stefan_Boltzmann
                Wien
                acre
                alpha
                angstrom
                arcmin
                arcminute
                arcsec
                arcsecond
                astronomical_unit
                atm
                atmosphere
                atomic_mass
                atto
                au
                bar
                barrel
                bbl
                blob
                c
                calorie
                calorie_IT
                calorie_th
                carat
                centi
                convert_temperature
                day
                deci
                degree
                degree_Fahrenheit
                deka
                dyn
                dyne
                e
                eV
                electron_mass
                electron_volt
                elementary_charge
                epsilon_0
                erg
                exa
                exbi
                femto
                fermi
                find
                fine_structure
                fluid_ounce
                fluid_ounce_US
                fluid_ounce_imp
                foot
                g
                gallon
                gallon_US
                gallon_imp
                gas_constant
                gibi
                giga
                golden
                golden_ratio
                grain
                gram
                gravitational_constant
                h
                hbar
                hectare
                hecto
                horsepower
                hour
                hp
                inch
                k
                kgf
                kibi
                kilo
                kilogram_force
                kmh
                knot
                lambda2nu
                lb
                lbf
                light_year
                liter
                litre
                long_ton
                m_e
                m_n
                m_p
                m_u
                mach
                mebi
                mega
                metric_ton
                micro
                micron
                mil
                mile
                milli
                minute
                mmHg
                mph
                mu_0
                nano
                nautical_mile
                neutron_mass
                nu2lambda
                ounce
                oz
                parsec
                pebi
                peta
                pi
                pico
                point
                pound
                pound_force
                precision
                proton_mass
                psi
                pt
                quecto
                quetta
                ronna
                ronto
                short_ton
                sigma
                slinch
                slug
                speed_of_light
                speed_of_sound
                stone
                survey_foot
                survey_mile
                tebi
                tera
                ton_TNT
                torr
                troy_ounce
                troy_pound
                u
                unit
                value
                week
                yard
                year
                yobi
                yocto
                yotta
                zebi
                zepto
                zero_Celsius
                zetta
                """
            ),
            "differentiate": _ns(
                """
                array_namespace
                derivative
                hessian
                jacobian
                xp_capabilities
                xp_copy
                xp_promote
                """
            ),
            "fft": _ns(
                """
                dct
                dctn
                dst
                dstn
                fft
                fft2
                fftfreq
                fftn
                fftshift
                fht
                fhtoffset
                get_workers
                hfft
                hfft2
                hfftn
                idct
                idctn
                idst
                idstn
                ifft
                ifft2
                ifftn
                ifftshift
                ifht
                ihfft
                ihfft2
                ihfftn
                irfft
                irfft2
                irfftn
                next_fast_len
                prev_fast_len
                rfft
                rfft2
                rfftfreq
                rfftn
                """
            ),
            "fftpack": _ns(
                """
                cc_diff
                cs_diff
                dct
                dctn
                diff
                dst
                dstn
                fft
                fft2
                fftn
                hilbert
                idct
                idctn
                idst
                idstn
                ifft
                ifft2
                ifftn
                ihilbert
                irfft
                itilbert
                next_fast_len
                rfft
                rfftfreq
                sc_diff
                shift
                ss_diff
                tilbert
                """
            ),
            "integrate": _ns(
                """
                BDF
                DOP853
                DenseOutput
                IntegrationWarning
                LSODA
                ODEintWarning
                OdeSolution
                OdeSolver
                RK23
                RK45
                Radau
                complex_ode
                cubature
                cumulative_simpson
                cumulative_trapezoid
                dblquad
                fixed_quad
                lebedev_rule
                newton_cotes
                nquad
                nsum
                ode
                odeint
                qmc_quad
                quad
                quad_vec
                romb
                simpson
                solve_bvp
                solve_ivp
                tanhsinh
                tplquad
                trapezoid
                """
            ),
            "interpolate": _ns(
                """
                AAA
                Akima1DInterpolator
                BPoly
                BSpline
                BarycentricInterpolator
                BivariateSpline
                CloughTocher2DInterpolator
                CubicHermiteSpline
                CubicSpline
                FloaterHormannInterpolator
                InterpolatedUnivariateSpline
                KroghInterpolator
                LSQBivariateSpline
                LSQSphereBivariateSpline
                LSQUnivariateSpline
                LinearNDInterpolator
                NdBSpline
                NdPPoly
                NearestNDInterpolator
                PPoly
                PchipInterpolator
                RBFInterpolator
                Rbf
                RectBivariateSpline
                RectSphereBivariateSpline
                RegularGridInterpolator
                SmoothBivariateSpline
                SmoothSphereBivariateSpline
                UnivariateSpline
                approximate_taylor_polynomial
                barycentric_interpolate
                bisplev
                bisplrep
                generate_knots
                griddata
                insert
                interp1d
                interp2d
                interpn
                krogh_interpolate
                lagrange
                make_interp_spline
                make_lsq_spline
                make_smoothing_spline
                make_splprep
                make_splrep
                pade
                pchip
                pchip_interpolate
                spalde
                splantider
                splder
                splev
                splint
                splprep
                splrep
                sproot
                """
            ),
            "linalg": _ns(
                """
                LinAlgWarning
                bandwidth
                block_diag
                cdf2rdf
                cho_factor
                cho_solve
                cho_solve_banded
                cholesky
                cholesky_banded
                circulant
                clarkson_woodruff_transform
                companion
                convolution_matrix
                coshm
                cosm
                cossin
                det
                dft
                diagsvd
                eig
                eig_banded
                eigh
                eigh_tridiagonal
                eigvals
                eigvals_banded
                eigvalsh
                eigvalsh_tridiagonal
                expm
                expm_cond
                expm_frechet
                fiedler
                fiedler_companion
                find_best_blas_type
                fractional_matrix_power
                funm
                hadamard
                hankel
                helmert
                hessenberg
                hilbert
                inv
                invhilbert
                invpascal
                ishermitian
                issymmetric
                khatri_rao
                ldl
                leslie
                logm
                lstsq
                lu
                lu_factor
                lu_solve
                matmul_toeplitz
                matrix_balance
                norm
                null_space
                ordqz
                orth
                orthogonal_procrustes
                pascal
                pinv
                pinvh
                polar
                qr
                qr_delete
                qr_insert
                qr_multiply
                qr_update
                qz
                rq
                rsf2csf
                schur
                signm
                sinhm
                sinm
                solve
                solve_banded
                solve_circulant
                solve_continuous_are
                solve_continuous_lyapunov
                solve_discrete_are
                solve_discrete_lyapunov
                solve_lyapunov
                solve_sylvester
                solve_toeplitz
                solve_triangular
                solveh_banded
                sqrtm
                subspace_angles
                svd
                svdvals
                tanhm
                tanm
                toeplitz
                """,
                {
                    "interpolative": _ns(
                        """
                        estimate_rank
                        estimate_spectral_norm
                        estimate_spectral_norm_diff
                        id_to_svd
                        interp_decomp
                        reconstruct_interp_matrix
                        reconstruct_matrix_from_id
                        reconstruct_skel_matrix
                        svd
                        """
                    ),
                },
            ),
            "ndimage": _ns(
                """
                affine_transform
                binary_closing
                binary_dilation
                binary_erosion
                binary_fill_holes
                binary_hit_or_miss
                binary_opening
                binary_propagation
                black_tophat
                center_of_mass
                convolve
                convolve1d
                correlate
                correlate1d
                distance_transform_bf
                distance_transform_cdt
                distance_transform_edt
                extrema
                find_objects
                fourier_ellipsoid
                fourier_gaussian
                fourier_shift
                fourier_uniform
                gaussian_filter
                gaussian_filter1d
                gaussian_gradient_magnitude
                gaussian_laplace
                generate_binary_structure
                generic_filter
                generic_filter1d
                generic_gradient_magnitude
                generic_laplace
                geometric_transform
                grey_closing
                grey_dilation
                grey_erosion
                grey_opening
                histogram
                iterate_structure
                label
                labeled_comprehension
                laplace
                map_coordinates
                maximum
                maximum_filter
                maximum_filter1d
                maximum_position
                mean
                median
                median_filter
                minimum
                minimum_filter
                minimum_filter1d
                minimum_position
                morphological_gradient
                morphological_laplace
                percentile_filter
                prewitt
                rank_filter
                rotate
                shift
                sobel
                spline_filter
                spline_filter1d
                standard_deviation
                sum
                sum_labels
                uniform_filter
                uniform_filter1d
                value_indices
                variance
                vectorized_filter
                watershed_ift
                white_tophat
                zoom
                """
            ),
            "optimize": _ns(
                """
                BFGS
                Bounds
                BroydenFirst
                HessianUpdateStrategy
                InverseJacobian
                KrylovJacobian
                LbfgsInvHessProduct
                LinearConstraint
                NoConvergence
                NonlinearConstraint
                OptimizeResult
                OptimizeWarning
                RootResults
                SR1
                anderson
                approx_fprime
                basinhopping
                bisect
                bracket
                brent
                brenth
                brentq
                broyden1
                broyden2
                brute
                check_grad
                curve_fit
                diagbroyden
                differential_evolution
                direct
                dual_annealing
                excitingmixing
                fixed_point
                fmin
                fmin_bfgs
                fmin_cg
                fmin_cobyla
                fmin_l_bfgs_b
                fmin_ncg
                fmin_powell
                fmin_slsqp
                fmin_tnc
                fminbound
                fsolve
                golden
                isotonic_regression
                least_squares
                leastsq
                line_search
                linear_sum_assignment
                linearmixing
                linprog
                linprog_verbose_callback
                lsq_linear
                milp
                minimize
                minimize_scalar
                newton
                newton_krylov
                nnls
                quadratic_assignment
                ridder
                root
                root_scalar
                rosen
                rosen_der
                rosen_hess
                rosen_hess_prod
                shgo
                toms748
                """
            ),
            "signal": _ns(
                """
                BadCoefficients
                CZT
                ShortTimeFFT
                StateSpace
                TransferFunction
                ZerosPolesGain
                ZoomFFT
                abcd_normalize
                argrelextrema
                argrelmax
                argrelmin
                band_stop_obj
                bessel
                besselap
                bilinear
                bilinear_zpk
                bode
                buttap
                butter
                buttord
                cheb1ap
                cheb1ord
                cheb2ap
                cheb2ord
                cheby1
                cheby2
                check_COLA
                check_NOLA
                chirp
                choose_conv_method
                closest_STFT_dual_window
                coherence
                cont2discrete
                convolve
                convolve2d
                correlate
                correlate2d
                correlation_lags
                csd
                cspline1d
                cspline1d_eval
                cspline2d
                czt
                czt_points
                dbode
                decimate
                deconvolve
                detrend
                dfreqresp
                dimpulse
                dlsim
                dlti
                dstep
                ellip
                ellipap
                ellipord
                envelope
                fftconvolve
                filtfilt
                find_peaks
                find_peaks_cwt
                findfreqs
                firls
                firwin
                firwin2
                firwin_2d
                freqresp
                freqs
                freqs_zpk
                freqz
                freqz_sos
                freqz_zpk
                gammatone
                gauss_spline
                gausspulse
                get_window
                group_delay
                hilbert
                hilbert2
                iircomb
                iirdesign
                iirfilter
                iirnotch
                iirpeak
                impulse
                invres
                invresz
                istft
                kaiser_atten
                kaiser_beta
                kaiserord
                lfilter
                lfilter_zi
                lfiltic
                lombscargle
                lp2bp
                lp2bp_zpk
                lp2bs
                lp2bs_zpk
                lp2hp
                lp2hp_zpk
                lp2lp
                lp2lp_zpk
                lsim
                lti
                max_len_seq
                medfilt
                medfilt2d
                minimum_phase
                normalize
                oaconvolve
                order_filter
                peak_prominences
                peak_widths
                periodogram
                place_poles
                qspline1d
                qspline1d_eval
                qspline2d
                remez
                resample
                resample_poly
                residue
                residuez
                savgol_coeffs
                savgol_filter
                sawtooth
                sepfir2d
                sos2tf
                sos2zpk
                sosfilt
                sosfilt_zi
                sosfiltfilt
                sosfreqz
                spectrogram
                spline_filter
                square
                ss2tf
                ss2zpk
                step
                stft
                sweep_poly
                symiirorder1
                symiirorder2
                tf2sos
                tf2ss
                tf2zpk
                unique_roots
                unit_impulse
                upfirdn
                vectorstrength
                welch
                wiener
                zoom_fft
                zpk2sos
                zpk2ss
                zpk2tf
                """,
                {
                    "windows": _ns(
                        """
                        barthann
                        bartlett
                        blackman
                        blackmanharris
                        bohman
                        boxcar
                        chebwin
                        cosine
                        dpss
                        exponential
                        flattop
                        gaussian
                        general_cosine
                        general_gaussian
                        general_hamming
                        get_window
                        hamming
                        hann
                        kaiser
                        kaiser_bessel_derived
                        lanczos
                        nuttall
                        parzen
                        taylor
                        triang
                        tukey
                        """
                    ),
                },
            ),
            "sparse": _ns(
                """
                SparseEfficiencyWarning
                SparseWarning
                block_array
                block_diag
                bmat
                bsr_array
                bsr_matrix
                coo_array
                coo_matrix
                csc_array
                csc_matrix
                csr_array
                csr_matrix
                dia_array
                dia_matrix
                diags
                diags_array
                dok_array
                dok_matrix
                expand_dims
                eye
                eye_array
                find
                get_index_dtype
                hstack
                identity
                issparse
                isspmatrix
                isspmatrix_bsr
                isspmatrix_coo
                isspmatrix_csc
                isspmatrix_csr
                isspmatrix_dia
                isspmatrix_dok
                isspmatrix_lil
                kron
                kronsum
                lil_array
                lil_matrix
                permute_dims
                rand
                random
                random_array
                safely_cast_index_arrays
                sparray
                spdiags
                spmatrix
                swapaxes
                tril
                triu
                vstack
                """,
                {
                    "csgraph": _ns(
                        """
                        NegativeCycleError
                        bellman_ford
                        breadth_first_order
                        breadth_first_tree
                        connected_components
                        construct_dist_matrix
                        csgraph_from_dense
                        csgraph_from_masked
                        csgraph_masked_from_dense
                        csgraph_to_dense
                        csgraph_to_masked
                        depth_first_order
                        depth_first_tree
                        dijkstra
                        floyd_warshall
                        johnson
                        laplacian
                        maximum_bipartite_matching
                        maximum_flow
                        min_weight_full_bipartite_matching
                        minimum_spanning_tree
                        reconstruct_path
                        reverse_cuthill_mckee
                        shortest_path
                        structural_rank
                        yen
                        """
                    ),
                    "linalg": _ns(
                        """
                        ArpackError
                        ArpackNoConvergence
                        LaplacianNd
                        LinearOperator
                        MatrixRankWarning
                        aslinearoperator
                        bicg
                        bicgstab
                        cg
                        cgs
                        eigs
                        eigsh
                        expm
                        expm_multiply
                        factorized
                        funm_multiply_krylov
                        gcrotmk
                        gmres
                        inv
                        is_sptriangular
                        lgmres
                        lobpcg
                        lsmr
                        lsqr
                        matrix_power
                        minres
                        norm
                        onenormest
                        qmr
                        spbandwidth
                        spilu
                        splu
                        spsolve
                        spsolve_triangular
                        svds
                        tfqmr
                        """
                    ),
                },
            ),
            "spatial": _ns(
                """
                ConvexHull
                Delaunay
                HalfspaceIntersection
                KDTree
                QhullError
                Rectangle
                SphericalVoronoi
                Voronoi
                cKDTree
                distance_matrix
                geometric_slerp
                minkowski_distance
                minkowski_distance_p
                procrustes
                tsearch
                """,
                {
                    "distance": _ns(
                        """
                        CDistMetricWrapper
                        MetricInfo
                        PDistMetricWrapper
                        braycurtis
                        canberra
                        cdist
                        chebyshev
                        cityblock
                        correlation
                        cosine
                        dice
                        directed_hausdorff
                        euclidean
                        hamming
                        is_valid_dm
                        is_valid_y
                        jaccard
                        jensenshannon
                        mahalanobis
                        minkowski
                        norm
                        num_obs_dm
                        num_obs_y
                        pdist
                        rel_entr
                        rogerstanimoto
                        russellrao
                        seuclidean
                        sokalsneath
                        sqeuclidean
                        squareform
                        yule
                        """
                    ),
                    "transform": _ns(
                        """
                        RigidTransform
                        Rotation
                        RotationSpline
                        Slerp
                        """
                    ),
                },
            ),
            "special": _ns(
                """
                SpecialFunctionError
                SpecialFunctionWarning
                agm
                ai_zeros
                airy
                airye
                assoc_laguerre
                assoc_legendre_p
                assoc_legendre_p_all
                bdtr
                bdtrc
                bdtri
                bdtrik
                bdtrin
                bei
                bei_zeros
                beip
                beip_zeros
                ber
                ber_zeros
                bernoulli
                berp
                berp_zeros
                besselpoly
                beta
                betainc
                betaincc
                betainccinv
                betaincinv
                betaln
                bi_zeros
                binom
                boxcox
                boxcox1p
                btdtria
                btdtrib
                c_roots
                cbrt
                cg_roots
                chdtr
                chdtrc
                chdtri
                chdtriv
                chebyc
                chebys
                chebyt
                chebyu
                chndtr
                chndtridf
                chndtrinc
                chndtrix
                comb
                cosdg
                cosm1
                cotdg
                dawsn
                digamma
                diric
                ellip_harm
                ellip_harm_2
                ellip_normal
                ellipe
                ellipeinc
                ellipj
                ellipk
                ellipkinc
                ellipkm1
                elliprc
                elliprd
                elliprf
                elliprg
                elliprj
                entr
                erf
                erf_zeros
                erfc
                erfcinv
                erfcx
                erfi
                erfinv
                euler
                eval_chebyc
                eval_chebys
                eval_chebyt
                eval_chebyu
                eval_gegenbauer
                eval_genlaguerre
                eval_hermite
                eval_hermitenorm
                eval_jacobi
                eval_laguerre
                eval_legendre
                eval_sh_chebyt
                eval_sh_chebyu
                eval_sh_jacobi
                eval_sh_legendre
                exp1
                exp10
                exp2
                expi
                expit
                expm1
                expn
                exprel
                factorial
                factorial2
                factorialk
                fdtr
                fdtrc
                fdtri
                fdtridfd
                fresnel
                fresnel_zeros
                fresnelc_zeros
                fresnels_zeros
                gamma
                gammainc
                gammaincc
                gammainccinv
                gammaincinv
                gammaln
                gammasgn
                gdtr
                gdtrc
                gdtria
                gdtrib
                gdtrix
                gegenbauer
                genlaguerre
                geterr
                h1vp
                h2vp
                h_roots
                hankel1
                hankel1e
                hankel2
                hankel2e
                he_roots
                hermite
                hermitenorm
                huber
                hyp0f1
                hyp1f1
                hyp2f1
                hyperu
                i0
                i0e
                i1
                i1e
                inv_boxcox
                inv_boxcox1p
                it2i0k0
                it2j0y0
                it2struve0
                itairy
                iti0k0
                itj0y0
                itmodstruve0
                itstruve0
                iv
                ive
                ivp
                j0
                j1
                j_roots
                jacobi
                jn
                jn_zeros
                jnjnp_zeros
                jnp_zeros
                jnyn_zeros
                js_roots
                jv
                jve
                jvp
                k0
                k0e
                k1
                k1e
                kei
                kei_zeros
                keip
                keip_zeros
                kelvin
                kelvin_zeros
                ker
                ker_zeros
                kerp
                kerp_zeros
                kl_div
                kn
                kolmogi
                kolmogorov
                kv
                kve
                kvp
                l_roots
                la_roots
                laguerre
                lambertw
                legendre
                legendre_p
                legendre_p_all
                lmbda
                log1p
                log_expit
                log_ndtr
                log_softmax
                log_wright_bessel
                loggamma
                logit
                logsumexp
                lpmv
                lqmn
                lqn
                mathieu_a
                mathieu_b
                mathieu_cem
                mathieu_even_coef
                mathieu_modcem1
                mathieu_modcem2
                mathieu_modsem1
                mathieu_modsem2
                mathieu_odd_coef
                mathieu_sem
                modfresnelm
                modfresnelp
                modstruve
                multigammaln
                nbdtr
                nbdtrc
                nbdtri
                nbdtrik
                nbdtrin
                ncfdtr
                ncfdtri
                ncfdtridfd
                ncfdtridfn
                ncfdtrinc
                nctdtr
                nctdtridf
                nctdtrinc
                nctdtrit
                ndtr
                ndtri
                ndtri_exp
                nrdtrimn
                nrdtrisd
                obl_ang1
                obl_ang1_cv
                obl_cv
                obl_cv_seq
                obl_rad1
                obl_rad1_cv
                obl_rad2
                obl_rad2_cv
                owens_t
                p_roots
                pbdn_seq
                pbdv
                pbdv_seq
                pbvv
                pbvv_seq
                pbwa
                pdtr
                pdtrc
                pdtri
                pdtrik
                perm
                poch
                polygamma
                powm1
                pro_ang1
                pro_ang1_cv
                pro_cv
                pro_cv_seq
                pro_rad1
                pro_rad1_cv
                pro_rad2
                pro_rad2_cv
                ps_roots
                pseudo_huber
                psi
                radian
                rel_entr
                rgamma
                riccati_jn
                riccati_yn
                roots_chebyc
                roots_chebys
                roots_chebyt
                roots_chebyu
                roots_gegenbauer
                roots_genlaguerre
                roots_hermite
                roots_hermitenorm
                roots_jacobi
                roots_laguerre
                roots_legendre
                roots_sh_chebyt
                roots_sh_chebyu
                roots_sh_jacobi
                roots_sh_legendre
                round
                s_roots
                sh_chebyt
                sh_chebyu
                sh_jacobi
                sh_legendre
                shichi
                sici
                sindg
                smirnov
                smirnovi
                softmax
                softplus
                spence
                sph_harm_y
                sph_harm_y_all
                sph_legendre_p
                sph_legendre_p_all
                spherical_in
                spherical_jn
                spherical_kn
                spherical_yn
                stdtr
                stdtridf
                stdtrit
                stirling2
                struve
                t_roots
                tandg
                tklmbda
                ts_roots
                u_roots
                us_roots
                voigt_profile
                wofz
                wright_bessel
                wrightomega
                xlog1py
                xlogy
                y0
                y0_zeros
                y1
                y1_zeros
                y1p_zeros
                yn
                yn_zeros
                ynp_zeros
                yv
                yve
                yvp
                zeta
                zetac
                """
            ),
            "stats": _ns(
                """
                Binomial
                BootstrapMethod
                CensoredData
                ConstantInputWarning
                Covariance
                DegenerateDataWarning
                FitError
                Logistic
                Mixture
                MonteCarloMethod
                NearConstantInputWarning
                Normal
                PermutationMethod
                Uniform
                abs
                alexandergovern
                alpha
                anderson
                anderson_ksamp
                anglit
                ansari
                arcsine
                argus
                barnard_exact
                bartlett
                bayes_mvs
                bernoulli
                beta
                betabinom
                betanbinom
                betaprime
                binned_statistic
                binned_statistic_2d
                binned_statistic_dd
                binom
                binomtest
                boltzmann
                bootstrap
                boschloo_exact
                boxcox
                boxcox_llf
                boxcox_normmax
                boxcox_normplot
                bradford
                brunnermunzel
                burr
                burr12
                bws_test
                cauchy
                chatterjeexi
                chi
                chi2
                chi2_contingency
                chisquare
                circmean
                circstd
                circvar
                combine_pvalues
                cosine
                cramervonmises
                cramervonmises_2samp
                crystalball
                cumfreq
                describe
                dgamma
                differential_entropy
                directional_stats
                dirichlet
                dirichlet_multinomial
                dlaplace
                dpareto_lognorm
                dunnett
                dweibull
                ecdf
                energy_distance
                entropy
                epps_singleton_2samp
                erlang
                exp
                expectile
                expon
                exponnorm
                exponpow
                exponweib
                f
                f_oneway
                false_discovery_control
                fatiguelife
                fisher_exact
                fisk
                fit
                fligner
                foldcauchy
                foldnorm
                friedmanchisquare
                gamma
                gausshyper
                gaussian_kde
                genexpon
                genextreme
                gengamma
                genhalflogistic
                genhyperbolic
                geninvgauss
                genlogistic
                gennorm
                genpareto
                geom
                gibrat
                gmean
                gompertz
                goodness_of_fit
                gstd
                gumbel_l
                gumbel_r
                gzscore
                halfcauchy
                halfgennorm
                halflogistic
                halfnorm
                hmean
                hypergeom
                hypsecant
                invgamma
                invgauss
                invweibull
                invwishart
                iqr
                irwinhall
                jarque_bera
                jf_skew_t
                johnsonsb
                johnsonsu
                kappa3
                kappa4
                kendalltau
                kruskal
                ks_1samp
                ks_2samp
                ksone
                kstat
                kstatvar
                kstest
                kstwo
                kstwobign
                kurtosis
                kurtosistest
                landau
                laplace
                laplace_asymmetric
                levene
                levy
                levy_l
                levy_stable
                linregress
                lmoment
                log
                loggamma
                logistic
                loglaplace
                lognorm
                logrank
                logser
                loguniform
                lomax
                make_distribution
                mannwhitneyu
                matrix_normal
                matrix_t
                maxwell
                median_abs_deviation
                median_test
                mielke
                mode
                moment
                monte_carlo_test
                mood
                moyal
                multinomial
                multiscale_graphcorr
                multivariate_hypergeom
                multivariate_normal
                multivariate_t
                mvsdist
                nakagami
                nbinom
                ncf
                nchypergeom_fisher
                nchypergeom_wallenius
                nct
                ncx2
                nhypergeom
                norm
                normal_inverse_gamma
                normaltest
                norminvgauss
                obrientransform
                order_statistic
                ortho_group
                page_trend_test
                pareto
                pearson3
                pearsonr
                percentileofscore
                permutation_test
                planck
                pmean
                pointbiserialr
                poisson
                poisson_binom
                poisson_means_test
                power
                power_divergence
                powerlaw
                powerlognorm
                powernorm
                ppcc_max
                ppcc_plot
                probplot
                quantile
                quantile_test
                randint
                random_correlation
                random_table
                rankdata
                ranksums
                rayleigh
                rdist
                recipinvgauss
                reciprocal
                rel_breitwigner
                relfreq
                rice
                rv_continuous
                rv_discrete
                rv_histogram
                scoreatpercentile
                sem
                semicircular
                shapiro
                siegelslopes
                sigmaclip
                skellam
                skew
                skewcauchy
                skewnorm
                skewtest
                sobol_indices
                somersd
                spearmanr
                spearmanrho
                special_ortho_group
                studentized_range
                t
                theilslopes
                tiecorrect
                tmax
                tmean
                tmin
                trapezoid
                triang
                trim1
                trim_mean
                trimboth
                truncate
                truncexpon
                truncnorm
                truncpareto
                truncweibull_min
                tsem
                tstd
                ttest_1samp
                ttest_ind
                ttest_ind_from_stats
                ttest_rel
                tukey_hsd
                tukeylambda
                tvar
                uniform
                uniform_direction
                unitary_group
                variation
                vonmises
                vonmises_fisher
                vonmises_line
                wald
                wasserstein_distance
                wasserstein_distance_nd
                weibull_max
                weibull_min
                weightedtau
                wilcoxon
                wishart
                wrapcauchy
                yeojohnson
                yeojohnson_llf
                yeojohnson_normmax
                yeojohnson_normplot
                yulesimon
                zipf
                zipfian
                zmap
                zscore
                """,
                {
                    "contingency": _ns(
                        """
                        Chi2ContingencyResult
                        association
                        chi2_contingency
                        crosstab
                        expected_freq
                        margins
                        odds_ratio
                        power_divergence
                        relative_risk
                        xp_capabilities
                        """
                    ),
                    "mstats": _ns(
                        """
                        argstoarray
                        brunnermunzel
                        chisquare
                        compare_medians_ms
                        count_tied_groups
                        describe
                        f_oneway
                        find_repeats
                        friedmanchisquare
                        gmean
                        hdmedian
                        hdquantiles
                        hdquantiles_sd
                        hmean
                        idealfourths
                        kendalltau
                        kendalltau_seasonal
                        kruskal
                        kruskalwallis
                        ks_1samp
                        ks_2samp
                        ks_twosamp
                        kstest
                        kurtosis
                        kurtosistest
                        linregress
                        mannwhitneyu
                        median_cihs
                        meppf
                        mjci
                        mode
                        moment
                        mquantiles
                        mquantiles_cimj
                        msign
                        normaltest
                        obrientransform
                        pearsonr
                        plotting_positions
                        pointbiserialr
                        rankdata
                        rsh
                        scoreatpercentile
                        sem
                        sen_seasonal_slopes
                        siegelslopes
                        skew
                        skewtest
                        spearmanr
                        theilslopes
                        tmax
                        tmean
                        tmin
                        trim
                        trima
                        trimboth
                        trimmed_mean
                        trimmed_mean_ci
                        trimmed_std
                        trimmed_stde
                        trimmed_var
                        trimr
                        trimtail
                        tsem
                        ttest_1samp
                        ttest_ind
                        ttest_onesamp
                        ttest_rel
                        tvar
                        variation
                        winsorize
                        zmap
                        zscore
                        """
                    ),
                    "qmc": _ns(
                        """
                        Halton
                        LatinHypercube
                        MultinomialQMC
                        MultivariateNormalQMC
                        PoissonDisk
                        QMCEngine
                        Sobol
                        discrepancy
                        geometric_discrepancy
                        scale
                        update_discrepancy
                        """
                    ),
                    "sampling": _ns(
                        """
                        DiscreteAliasUrn
                        DiscreteGuideTable
                        FastGeneratorInversion
                        NumericalInverseHermite
                        NumericalInversePolynomial
                        RatioUniforms
                        SimpleRatioUniforms
                        TransformedDensityRejection
                        UNURANError
                        """
                    ),
                },
            ),
        },
    ),
}

# Attributes/methods allowed on any other object (Series, DataFrame, ndarray, str, ...).
ALLOWED_ATTRIBUTES = _names(
    """
    A
    A1
    A_EXTRA
    B
    C
    C_EXTRA
    D
    E
    E3
    E5
    H
    I
    L
    MAXDIM
    MAX_ITER
    P
    T
    TOL
    TOO_SMALL_STEP
    U
    a
    ab
    abs
    accumulate
    active_mask
    add
    add_categories
    add_halfspaces
    add_note
    add_points
    add_prefix
    add_suffix
    add_xi
    adjoint
    advance
    align
    align_vectors
    alignment
    all
    allows_duplicate_labels
    alternative
    anom
    antiderivative
    any
    append
    approx_equal
    arcsin
    arcsinh
    arctan
    arctanh
    area
    argmax
    argmin
    argpartition
    args
    argsort
    array
    as_components
    as_davenport
    as_dual_quat
    as_euler
    as_exp_coords
    as_integer_ratio
    as_matrix
    as_mrp
    as_ordered
    as_quat
    as_rotvec
    as_unit
    as_unordered
    asformat
    asfptype
    asfreq
    asi8
    asm8
    asof
    asof_locs
    aspreconditioner
    assign
    astimezone
    astype
    at
    at_time
    attrs
    autocorr
    axes
    axis
    b
    base
    baseclass
    basis
    basis_element
    basis_name
    batch
    beta
    between
    between_time
    bfill
    binomial
    bit_count
    bit_generator
    bit_length
    bits
    blocksize
    bode
    bootstrap_distribution
    bounds_error
    boxsize
    byteorder
    bytes
    byteswap
    c
    cache_policy
    calculate_areas
    capitalize
    capsule
    case_when
    casefold
    cast
    cat
    categories
    ccdf
    cdf
    ceil
    center
    char
    check_for_ordered
    check_format
    chisquare
    choice
    choose
    clean_up
    clear
    clip
    close
    closed
    closed_left
    closed_right
    codes
    coef
    coefficients
    coeffs
    colorize
    columns
    combine
    combine_first
    compare
    components
    compress
    compressed
    con
    concatenate
    confidence_interval
    conj
    conjugate
    connected
    construct_fast
    contains
    converged
    convert
    convert_dtypes
    convex_hull
    coords
    coplanar
    copy
    corr
    correlation
    corrwith
    cost
    count
    count_neighbors
    count_nonzero
    cov
    covariance
    covariance_factor
    create_group
    critical_values
    crossover_nit
    ctime
    cumcount
    cummax
    cummin
    cumprod
    cumsum
    cutdeg
    d
    data
    date
    day
    day_name
    day_of_week
    day_of_year
    dayofweek
    dayofyear
    days
    days_in_month
    daysinmonth
    debug_print
    decode
    deg2rad
    degree
    delete
    delta_f
    delta_t
    den
    denominator
    dense_output
    density
    deriv
    derivative
    derivatives
    descr
    describe
    design_matrix
    device
    df
    diagonal
    diff
    difference
    difference_update
    dirichlet
    discard
    div
    divide
    divmod
    dof
    domain
    dot
    drop
    drop_duplicates
    droplevel
    dropna
    dst
    dt
    dtype
    dtype_i
    dtypes
    dual_vertices
    dual_win
    duplicated
    eigenvalues
    eigenvectors
    eliminate_zeros
    empty
    enable_external_loop
    encode
    end_time
    endswith
    entropy
    epsneg
    eq
    eqlin
    equal_levels
    equals
    equations
    error_estimator_order
    ev
    evaluate
    evaluate_error
    ewm
    exclusions
    expanding
    expandtabs
    expect
    expected_freq
    explode
    expm1
    exponential
    extend
    extent
    extract
    extractall
    extrapolate
    f
    f_pts
    fac_magnitude
    fac_psd
    factorize
    fast_forward
    ffill
    fft_mode
    fields
    fill
    fill_space
    fill_value
    filled
    fillna
    filter
    find
    find_simplex
    findall
    finished
    first
    first_valid_index
    fit
    fit_loc_scale
    fit_result
    flag
    flags
    flat
    flatten
    floor
    floordiv
    fold
    freeze
    freq
    freqresp
    freqstr
    from_arrays
    from_arrow
    from_bernstein_basis
    from_breaks
    from_bytes
    from_cholesky
    from_codes
    from_components
    from_coo
    from_davenport
    from_derivatives
    from_diagonal
    from_dict
    from_dual
    from_dual_quat
    from_eigendecomposition
    from_euler
    from_exp_coords
    from_fields
    from_frame
    from_matrix
    from_mrp
    from_ordinals
    from_power_basis
    from_precision
    from_product
    from_quat
    from_range
    from_records
    from_rotation
    from_rotvec
    from_spline
    from_translation
    from_tuples
    from_win_equals_dual
    from_window
    fromhex
    fromisocalendar
    fromisoformat
    fromkeys
    fromordinal
    fromroots
    fromtimestamp
    fs
    fullmatch
    fun
    function_calls
    furthest_site
    gain
    gamma
    ge
    generate_state
    geometric
    get
    getA
    getA1
    getH
    getI
    getT
    get_coeffs
    get_count
    get_dummies
    get_fill_value
    get_group
    get_id
    get_imag
    get_indexer
    get_indexer_for
    get_indexer_non_unique
    get_knots
    get_left
    get_level_values
    get_loc
    get_loc_level
    get_locs
    get_matrix
    get_real
    get_residual
    get_return_code
    get_right
    get_shape
    get_slice_bound
    get_state
    getcol
    getfield
    getformat
    getmaxprint
    getnnz
    getrow
    getrowview
    good
    grad
    grid
    groupby
    groups
    gt
    gumbel
    halfspaces
    harden_mask
    hardmask
    has_canonical_format
    has_delayed_bufalloc
    has_duplicates
    has_index
    has_multi_index
    has_samecoef
    has_samedomain
    has_sametype
    has_samewindow
    has_sorted_indices
    hasnans
    hasobject
    hat_area
    head
    hess
    hess_inv
    hex
    high_slope
    hop
    hour
    hypergeometric
    iat
    iccdf
    icdf
    identical
    identity
    idxmax
    idxmin
    iexp
    iloc
    ilogccdf
    ilogcdf
    imag
    impulse
    index
    indexer_at_time
    indexer_between_time
    indices
    indptr
    ineqlin
    infer_objects
    inferred_freq
    inferred_type
    initialize
    innernode
    inputs
    insert
    insert_knot
    integ
    integers
    integral
    integrate
    integrate_1d
    integrate_box
    integrate_box_1d
    integrate_gaussian
    integrate_kde
    intercept
    intercept_stderr
    interpolate
    intersection
    intersection_update
    interval
    interval_censored
    intervals
    inv
    inv_cov
    invertible
    is_
    is_empty
    is_full
    is_integer
    is_leaf
    is_leap_year
    is_monotonic_decreasing
    is_monotonic_increasing
    is_month_end
    is_month_start
    is_non_overlapping_monotonic
    is_normalized
    is_on_offset
    is_overlapping
    is_quarter_end
    is_quarter_start
    is_unique
    is_year_end
    is_year_start
    isalignedstruct
    isalnum
    isalpha
    isascii
    isbuiltin
    iscontiguous
    isdecimal
    isdigit
    isdisjoint
    isetitem
    isf
    isidentifier
    isin
    islower
    isna
    isnative
    isnull
    isnumeric
    isocalendar
    isoformat
    isoweekday
    isprintable
    isspace
    issubset
    issuperset
    istft
    istitle
    isupper
    item
    items
    itemsize
    iterationneedsapi
    iterations
    iterindex
    iternext
    iterrange
    iterrows
    iters
    itersize
    itertuples
    itviews
    jac
    join
    jumped
    k
    k_max
    k_min
    keys
    kind
    kurt
    kurtosis
    kwds
    laplace
    last
    last_valid_index
    le
    leafnode
    leafsize
    left
    left_censored
    len
    length
    level
    levels
    levshape
    lift_points
    linspace
    list
    ljust
    loc
    log1p
    log_pdet
    logccdf
    logcdf
    logentropy
    logistic
    lognormal
    logpdf
    logpmf
    logseries
    logsf
    low_slope
    lower
    lower_border_end
    lstrip
    lt
    m
    mT
    m_num
    m_num_mid
    machep
    magnitude
    maketrans
    map
    mapparms
    marginal
    mask
    match
    matmat
    matvec
    max
    max_bound
    max_distance_point
    max_distance_rectangle
    maxcv
    maxes
    maximum
    maxn
    maxpower
    maxprint
    mean
    median
    melt
    memory_usage
    merge
    message
    metadata
    method
    mfft
    microsecond
    microseconds
    mid
    midpoint_error
    millisecond
    min
    min_bound
    min_distance_point
    min_distance_rectangle
    minimum
    minmax
    mins
    minute
    mip_dual_bound
    mip_gap
    mip_node_count
    mod
    mode
    moment
    month
    month_name
    mu
    mul
    multi_index
    multinomial
    multiply
    multivariate_hypergeometric
    multivariate_normal
    n
    n_children_spawned
    n_resamples
    n_stages
    name
    names
    nanmax
    nanmin
    nanos
    nanosecond
    nanoseconds
    nargs
    nbytes
    nd
    ndim
    ne
    nearest
    nearest_k_p
    neff
    negative_binomial
    negep
    neighbors
    newbyteorder
    nexp
    nfev
    ngroup
    ngroups
    nhev
    nin
    nit
    njev
    nlargest
    nlevels
    nlu
    nnlf
    nnz
    nobs
    node
    noncentral_chisquare
    noncentral_f
    nonzero
    nop
    normal
    normalize
    notna
    notnull
    nout
    now
    npoints
    nsimplex
    nsmallest
    nth
    ntypes
    num
    num_censored
    num_generated
    numerator
    numiter
    nunique
    o
    offsets
    ohlc
    onesided_fft
    online
    open_left
    open_right
    operands
    optimality
    optimization_method
    order
    ordered
    ordinal
    outer
    output
    outputs
    overlaps
    p
    p_max
    p_min
    p_num
    p_range
    pad
    paraboloid_scale
    paraboloid_shift
    pareto
    partial_derivative
    partition
    pct_change
    pdf
    perm_c
    perm_r
    permutation
    permuted
    phase_shift
    pipe
    pivot
    plane_distance
    pmf
    points
    poisson
    poles
    pool
    pool_size
    pop
    popitem
    pow
    power
    ppf
    ppf_hat
    pre_order
    prod
    product
    proportion_ci
    proportion_estimate
    prune
    ptp
    put
    putmask
    pvalue
    qrvs
    quantile
    quarter
    query_ball_point
    query_ball_tree
    query_pairs
    qyear
    r
    rad2deg
    radd
    rand
    randint
    randn
    random
    random_base2
    random_integers
    random_raw
    random_sample
    random_state
    rank
    ravel
    rayleigh
    rdiv
    rdivmod
    real
    recordmask
    reduce
    reduceat
    reindex
    reindex_like
    remove
    remove_axis
    remove_categories
    remove_multi_index
    remove_unused_categories
    remove_unused_levels
    removeprefix
    removesuffix
    rename
    rename_axis
    rename_categories
    reorder_categories
    reorder_levels
    repeat
    replace
    requires_contiguous_out
    resample
    reset
    reset_cache
    reset_index
    reshape
    residual
    residues
    resolution
    resolution_string
    resolve_dtypes
    reverse
    rfind
    rfloordiv
    ridge_dict
    right
    right_censored
    rindex
    rint
    rjust
    rmatmat
    rmatvec
    rmod
    rmul
    rng
    rng_seed
    rollback
    rollforward
    rolling
    root
    roots
    rotation
    round
    row
    rows
    rpartition
    rpow
    rsolve
    rsplit
    rstrip
    rsub
    rtruediv
    rule_code
    rvalue
    rvs
    sample
    scale
    scale_to
    scaling
    scotts_factor
    scramble
    searchsorted
    second
    seconds
    seed_seq
    select_dtypes
    sem
    set_axis
    set_bandwidth
    set_categories
    set_closed
    set_codes
    set_f_params
    set_fill_value
    set_flags
    set_index
    set_initial_value
    set_integrator
    set_jac_params
    set_levels
    set_names
    set_ordered
    set_random_state
    set_shape
    set_smoothing_factor
    set_solout
    set_yi
    setdefault
    setdiag
    setfield
    setup
    sf
    shape
    sharedmask
    shift
    shrink_mask
    shuffle
    sigma
    sign
    signature
    significance_level
    silverman_factor
    simplices
    sin
    single
    sinh
    size
    skew
    skewness
    slack
    slice
    slice_indexer
    slice_locs
    slice_replace
    slope
    snap
    soften_mask
    sol
    solve
    sort
    sort_index
    sort_indices
    sort_values
    sort_vertices_of_regions
    sorted_indices
    sortlevel
    sp_values
    sparse
    sparse_distance_matrix
    spawn
    spawn_key
    spectrogram
    split
    splitlines
    sqrt
    squeeze
    squeeze_area
    squeeze_hat_ratio
    stack
    standard_cauchy
    standard_deviation
    standard_error
    standard_exponential
    standard_gamma
    standard_normal
    standard_t
    start
    start_time
    startswith
    state
    statistic
    statistic_location
    statistic_sign
    stats
    status
    std
    stderr
    step
    step_size
    stft
    stft_detrend
    stop
    str
    strftime
    strides
    strip
    strptime
    struct
    sub
    subdtype
    subset
    subset_size
    subsets
    subtract
    success
    successful
    sum
    sum_duplicates
    support
    support_points
    support_values
    swapaxes
    swapcase
    swaplevel
    symbol
    symmetric_difference
    symmetric_difference_update
    t
    t_events
    tail
    take
    tan
    tanh
    tck
    tensordot
    time
    timestamp
    timetuple
    timetz
    tiny
    title
    to_bytes
    to_coo
    to_datetime64
    to_dense
    to_device
    to_dict
    to_discrete
    to_flat_index
    to_frame
    to_julian_date
    to_list
    to_numpy
    to_period
    to_pydatetime
    to_pytimedelta
    to_records
    to_series
    to_ss
    to_tf
    to_timedelta64
    to_timestamp
    to_tuples
    to_zpk
    toarray
    tobsr
    tobytes
    tocoo
    tocsc
    tocsr
    today
    todense
    todia
    todok
    toflex
    tol
    tolil
    tolist
    tomaxint
    toordinal
    torecords
    tosparse
    total_seconds
    trace
    translate
    translation
    transpose
    tree
    triangular
    trim
    truediv
    trunc
    truncate
    type
    types
    tz
    tz_convert
    tz_localize
    tzinfo
    tzname
    u_error
    uniform
    union
    unique
    unit
    unshare_mask
    unstack
    update
    upper
    upper_border_begin
    utcfromtimestamp
    utcnow
    utcoffset
    utctimetuple
    validate_input
    validation_policy
    validator
    value
    value_counts
    values
    var
    variable
    variance
    vertex_neighbor_vertices
    vertex_to_simplex
    vertices
    view
    volume
    vonmises
    wald
    week
    weekday
    weekofyear
    weibull
    weights
    where
    whiten
    win
    window
    with_traceback
    wrap
    x
    xs
    y
    y_events
    year
    zeros
    zfill
    zipf
    """
)

# Methods that resolve a *string* argument to an attribute. They may only be called
# directly, with a function or an allowed method name (see the validator above).
GUARDED_METHODS = _names("agg aggregate apply transform")

# Attribute names in ALLOWED_ATTRIBUTES that are also non-allowed attributes of an
# enumerated library module; reviewed and judged harmless (COLLISION_OK in the
# generator). A test checks that no *other* such collision exists.
REVIEWED_MODULE_COLLISIONS = _names(
    """
    base
    bit_generator
    compressed
    data
    dtypes
    extract
    interpolate
    reduce
    rotation
    stats
    zeros
    """
)
# fmt: on
# END GENERATED ALLOW-LISTS
