import ast
import builtins
from enum import Enum, auto
from pint import UndefinedUnitError

from .units import u

# AST node types permitted anywhere inside a custom operation. This allows the
# arithmetic/comparison/boolean grammar plus the calls, attribute access,
# subscripts, slices, and comprehensions needed to use pandas/numpy/scipy
# (e.g. ``x.diff()``, ``x.shift(-1)``, ``np.where(...)``, ``[f(z) for z in x]``).
ALLOWED_NODES = (
    ast.Expression,
    ast.Lambda,
    ast.arguments,
    ast.arg,
    ast.Name,
    ast.Load,
    ast.Store,
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
    ast.comprehension,
    ast.IfExp,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.MatMult,
    ast.USub,
    ast.UAdd,
    ast.Invert,
    ast.And,
    ast.Or,
    ast.Not,
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

# Free (unbound) names a custom operation may reference. Only the scientific
# libraries users expect are exposed -- nothing that reaches the OS, the
# filesystem, or the import system.
ALLOWED_NAMES = frozenset({"np", "numpy", "pd", "pandas", "sp", "scipy", "math"})

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

# Attribute/method names a custom operation may call. This is an explicit
# allow-list (default-deny): any attribute not listed here is rejected, so a
# new or unforeseen pandas/numpy/scipy entry point can never be reached. Every
# entry is a pure, I/O-free numeric operation. Extend deliberately.
ALLOWED_CALLS = frozenset(
    {
        # reductions / summary statistics
        "sum",
        "prod",
        "mean",
        "median",
        "std",
        "var",
        "sem",
        "min",
        "max",
        "count",
        "nunique",
        "quantile",
        "mode",
        "skew",
        "kurt",
        "kurtosis",
        "any",
        "all",
        # cumulative
        "cumsum",
        "cumprod",
        "cummax",
        "cummin",
        # transforms
        "diff",
        "shift",
        "pct_change",
        "rank",
        # clip / fill / select
        "clip",
        "fillna",
        "ffill",
        "bfill",
        "replace",
        "interpolate",
        "mask",
        "where",
        "dropna",
        "round",
        "abs",
        "astype",
        # null checks
        "isna",
        "notna",
        "isnull",
        "notnull",
        # windowing
        "rolling",
        "expanding",
        "ewm",
        # function application / combination (see DISPATCH_CALLS guard below)
        "apply",
        "applymap",
        "agg",
        "aggregate",
        "transform",
        "map",
        "pipe",
        "dot",
        # arithmetic methods
        "add",
        "sub",
        "mul",
        "div",
        "truediv",
        "floordiv",
        "mod",
        "pow",
        # numpy ufuncs / elementwise math
        "sqrt",
        "cbrt",
        "exp",
        "expm1",
        "log",
        "log1p",
        "log2",
        "log10",
        "power",
        "square",
        "sign",
        "floor",
        "ceil",
        "trunc",
        "rint",
        "sin",
        "cos",
        "tan",
        "arcsin",
        "arccos",
        "arctan",
        "arctan2",
        "sinh",
        "cosh",
        "tanh",
        "hypot",
        "degrees",
        "radians",
        "maximum",
        "minimum",
        "subtract",
        "multiply",
        "divide",
        "true_divide",
        "remainder",
        "nan_to_num",
        "isfinite",
        "isnan",
        "isinf",
        # numpy nan-aware aggregations
        "nansum",
        "nanmean",
        "nanstd",
        "nanmax",
        "nanmin",
        "nanmedian",
        "nanprod",
        "percentile",
        "average",
    }
)

# Dispatch methods that accept a *function spec* -- a callable, a method-name
# string, or a list/dict of them (e.g. ``x.agg("sum")``, ``x.apply("mean")``).
# A string spec names a method by name, which would bypass the attribute
# allow-list, so every method-name string passed to one of these is itself
# checked against `ALLOWED_CALLS` (see `_CustomOperationValidator.visit_Call`).
# Callable specs are validated as ordinary nodes.
DISPATCH_CALLS = frozenset({"apply", "applymap", "agg", "aggregate", "transform"})


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


class _CustomOperationValidator(ast.NodeVisitor):
    """Scope-aware AST validator for ``custom_operations`` lambda strings.

    Enforces the module allow-lists while maintaining a stack of lexical
    scopes, so that names bound by a lambda's parameters or a comprehension's
    targets are treated as bound only within that scope (and nested lambdas get
    their own scope). This closes several holes a flat "bound names" set has:
    cross-scope name leakage, attribute/subscript assignment targets that can
    monkeypatch shared modules, and names collected from Load-context bases of
    a store target.
    """

    def __init__(self):
        self.scopes = []  # stack of sets: names bound in each enclosing scope

    def _is_bound(self, name):
        return any(name in scope for scope in self.scopes)

    def _bind_target(self, target, scope):
        """Bind the names in an assignment target, rejecting unsafe targets.

        Only ``Name`` targets (optionally nested in ``Tuple``/``List`` or
        prefixed by ``*``) may be bound. ``Attribute`` (``np.sum``) and
        ``Subscript`` (``x[0]``) targets are stores into existing objects and
        are rejected outright, since they could rebind a shared module/object.
        """
        if isinstance(target, ast.Name):
            scope.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                self._bind_target(element, scope)
        elif isinstance(target, ast.Starred):
            self._bind_target(target.value, scope)
        else:
            raise ValueError(
                "Assignment targets in `custom_operations` must be plain "
                f"names; `{type(target).__name__}` targets are not allowed"
            )

    def generic_visit(self, node):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(
                f"Disallowed syntax in `custom_operations`: {type(node).__name__}"
            )
        super().generic_visit(node)

    def visit_Lambda(self, node):
        if node.args.defaults or any(
            default is not None for default in node.args.kw_defaults
        ):
            raise ValueError(
                "Default argument values are not allowed in `custom_operations`"
            )
        scope = {
            arg.arg
            for arg in (node.args.posonlyargs + node.args.args + node.args.kwonlyargs)
        }
        if node.args.vararg is not None:
            scope.add(node.args.vararg.arg)
        if node.args.kwarg is not None:
            scope.add(node.args.kwarg.arg)
        self.scopes.append(scope)
        self.visit(node.body)
        self.scopes.pop()

    def _visit_comprehension(self, node, elements):
        scope = set()
        self.scopes.append(scope)
        for generator in node.generators:
            # the iterable is evaluated before its target is bound
            self.visit(generator.iter)
            self._bind_target(generator.target, scope)
            for condition in generator.ifs:
                self.visit(condition)
        for element in elements:
            self.visit(element)
        self.scopes.pop()

    def visit_ListComp(self, node):
        self._visit_comprehension(node, [node.elt])

    def visit_SetComp(self, node):
        self._visit_comprehension(node, [node.elt])

    def visit_GeneratorExp(self, node):
        self._visit_comprehension(node, [node.elt])

    def visit_DictComp(self, node):
        self._visit_comprehension(node, [node.key, node.value])

    def visit_Attribute(self, node):
        if node.attr.startswith("_"):
            raise ValueError(
                f"Access to attribute `{node.attr}` is not allowed "
                "in `custom_operations`"
            )
        if node.attr not in ALLOWED_CALLS:
            raise ValueError(
                f"`{node.attr}` is not an allowed operation in "
                f"`custom_operations`; allowed operations are "
                f"{sorted(ALLOWED_CALLS)}"
            )
        self.visit(node.value)

    def _check_dispatch_spec(self, spec):
        """Reject method-name strings in a dispatch spec that aren't allowed.

        Callables and other expressions are left to the normal walk; only
        string method names (scalar, in a list/tuple/set, or as dict values)
        are checked, so e.g. ``agg("sum")`` is fine but ``agg("to_pickle")``
        is rejected. Dict keys (column labels) are not method names and are
        skipped.
        """
        if isinstance(spec, ast.Constant) and isinstance(spec.value, str):
            if spec.value not in ALLOWED_CALLS:
                raise ValueError(
                    f"`{spec.value}` is not an allowed operation in "
                    f"`custom_operations`; allowed operations are "
                    f"{sorted(ALLOWED_CALLS)}"
                )
        elif isinstance(spec, (ast.List, ast.Tuple, ast.Set)):
            for element in spec.elts:
                self._check_dispatch_spec(element)
        elif isinstance(spec, ast.Dict):
            for value in spec.values:
                self._check_dispatch_spec(value)

    def visit_Call(self, node):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in DISPATCH_CALLS:
            spec = None
            if node.args:
                spec = node.args[0]
            else:
                spec = next(
                    (kw.value for kw in node.keywords if kw.arg == "func"), None
                )
            if spec is not None:
                self._check_dispatch_spec(spec)
        self.generic_visit(node)

    def visit_Name(self, node):
        if not isinstance(node.ctx, ast.Load):
            return
        name = node.id
        if self._is_bound(name):
            return
        if name.startswith("_"):
            raise ValueError(
                f"Reference to `{name}` is not allowed in `custom_operations`"
            )
        if name not in ALLOWED_NAMES and name not in SAFE_BUILTIN_NAMES:
            raise ValueError(
                f"Unknown name `{name}` in `custom_operations`; only "
                f"{sorted(ALLOWED_NAMES)} and basic builtins are allowed"
            )


def _parse_custom_operation(func_str):
    """Parse and validate a custom operation string, returning its AST.

    Both `validate_custom_operation` and `build_custom_operation` go through
    this single parse so that the exact tree that was validated is also the one
    that gets compiled -- there is no "validate one string, evaluate another"
    gap (e.g. differing leading whitespace between validation and ``eval``).
    """
    tree = ast.parse(func_str.strip(), mode="eval")
    if not isinstance(tree.body, ast.Lambda):
        raise ValueError("`custom_operations` must be a single lambda expression")
    _CustomOperationValidator().visit(tree)
    return tree


def validate_custom_operation(func_str):
    """Validate that a custom operation string is a safe lambda expression.

    Parses `func_str` and walks its abstract syntax tree with a scope-aware
    validator, enforcing allow-lists so the expression can use
    pandas/numpy/scipy (method calls, attribute access, subscripts,
    comprehensions, nested lambdas, and functions from the allowed modules)
    while remaining unable to execute arbitrary code. It rejects:

    - any syntax node outside ``ALLOWED_NODES`` (e.g. assignments, ``with``),
    - default argument values (they are evaluated when the lambda is built and
      would bypass the free-name check),
    - assignment targets that are not plain names (an ``Attribute``/``Subscript``
      target such as ``np.sum`` could rebind a shared module),
    - any attribute whose name begins with ``_`` (blocks dunder traversal such
      as ``__class__`` / ``__globals__`` / ``__subclasses__``),
    - any attribute/method not in `ALLOWED_CALLS` (default-deny, so code/IO
      entry points such as ``read_pickle``, ``load``, ``eval``, ``query`` are
      never reachable, nor is any future addition to the libraries),
    - any free (unbound) name that is not in `ALLOWED_NAMES` or the safe
      builtin set (blocks ``__import__``, ``open``, ``getattr``, ``eval`` ...).

    Names bound by lambda parameters and comprehension targets are scoped, so a
    name bound inside a comprehension is not treated as bound outside it.

    This is validation only; use `build_custom_operation` to additionally
    compile the expression in a restricted namespace.

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
    ValueError
        When `func_str` is not a single lambda expression,
        or contains syntax, names, or attributes that are not allowed
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
    whose only module globals are the allowed scientific libraries. This
    replaces a bare ``eval`` so that, even if validation were bypassed, the
    execution environment exposes no dangerous callables.

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
    ValueError
        When `func_str` fails `validate_custom_operation`
    SyntaxError
        When `func_str` is not valid Python syntax
    """
    tree = _parse_custom_operation(func_str)

    import math
    import numpy
    import pandas
    import scipy

    safe_globals = {
        "__builtins__": SAFE_BUILTINS,
        "np": numpy,
        "numpy": numpy,
        "pd": pandas,
        "pandas": pandas,
        "sp": scipy,
        "scipy": scipy,
        "math": math,
    }

    return eval(compile(tree, "<custom_operation>", "eval"), safe_globals, {})


def get_tag_sum_lambda_func(unit_ids):
    """Generate a lambda function string to sum tags

    Parameters
    ----------
    unit_ids : list
        A list of unit IDs to sum

    Returns
    -------
    str :
        A string representation of a lambda function that sums tags

    """
    arguments = ",".join(["tag" + str(unit + 1) for unit, _ in enumerate(unit_ids)])
    ops = "+".join(["tag" + str(unit + 1) for unit, _ in enumerate(unit_ids)])
    return f"lambda {arguments}: {ops}"


def parse_quantity(value, units):
    """Convert a value and unit string to a Pint quantity

    Parameters
    ----------
    value : float

    units : str

    Returns
    -------
    pint.Quantity
        a Pint Quantity with the given value and units
    """
    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            value = float(value)

    if value is not None:
        if units:
            return value * parse_units(units)
        else:
            return value
    else:
        return None


def parse_units(units):
    """Convert a unit string to a Pint Unit object

    Parameters
    ----------
    units : str

    Returns
    -------
    Unit
        a Pint Unit for the given string
    """
    if units is None or units == "" or units.lower() == "none":
        return
    else:
        clean_units = units.lower().replace(" ", "")
        try:
            return u(clean_units).units
        except UndefinedUnitError:
            if (
                clean_units == "mgd"
                or clean_units == "milliongalperday"
                or clean_units == "milliongal/day"
                or clean_units == "10**6gal/day"
                or clean_units == "milliongallonperday"
                or clean_units == "milliongallon/day"
                or clean_units == "10**6gallon/day"
                or clean_units == "milliongallonsperday"
                or clean_units == "milliongallons/day"
                or clean_units == "10**6gallons/day"
                or clean_units == "milliongalperd"
                or clean_units == "milliongal/d"
                or clean_units == "10**6gal/d"
                or clean_units == "milliongallonperd"
                or clean_units == "milliongallon/d"
                or clean_units == "10**6gallon/d"
                or clean_units == "milliongallonsperd"
                or clean_units == "milliongallons/d"
                or clean_units == "10**6gallons/d"
            ):
                return u.MGD
            elif (
                clean_units == "cubicmeters"
                or clean_units == "cubicmeter"
                or clean_units == "m**3"
                or clean_units == "m^3"
                or clean_units == "m3"
                or clean_units == "meter3"
                or clean_units == "meter**3"
                or clean_units == "meter^3"
                or clean_units == "meters3"
                or clean_units == "meters**3"
                or clean_units == "meters^3"
            ):
                return u.m**3
            elif clean_units == "horsepower" or clean_units == "hp":
                return u.hp
            elif (
                clean_units == "scfm"
                or clean_units == "cfm"
                or clean_units == "cubicfeet/min"
                or clean_units == "cubicfoot/min"
                or clean_units == "ft3/min"
                or clean_units == "ft**3/min"
                or clean_units == "ft^3/min"
                or clean_units == "foot3/min"
                or clean_units == "foot^3/min"
                or clean_units == "foot**3/min"
                or clean_units == "feet3/min"
                or clean_units == "feet**3/min"
                or clean_units == "feet^3/min"
                or clean_units == "cubicfeet/minute"
                or clean_units == "cubicfoot/minute"
                or clean_units == "ft3/minute"
                or clean_units == "ft**3/minute"
                or clean_units == "ft^3/minute"
                or clean_units == "foot3/minute"
                or clean_units == "foot^3/minute"
                or clean_units == "foot**3/minute"
                or clean_units == "feet3/minute"
                or clean_units == "feet**3/minute"
                or clean_units == "feet^3/minute"
            ):
                return u.ft**3 / u.min
            elif (
                clean_units == "scf"
                or clean_units == "cubicfeet"
                or clean_units == "cubicfoot"
                or clean_units == "ft3"
                or clean_units == "ft**3"
                or clean_units == "ft^3"
                or clean_units == "foot3"
                or clean_units == "foot**3"
                or clean_units == "foot^3"
                or clean_units == "feet3"
                or clean_units == "feet**3"
                or clean_units == "feet^3"
            ):
                return u.ft**3
            elif (
                clean_units == "gpm"
                or clean_units == "galpermin"
                or clean_units == "gallonpermin"
                or clean_units == "gallonspermin"
                or clean_units == "galperminute"
                or clean_units == "gallonperminute"
                or clean_units == "gallonsperminute"
                or clean_units == "gal/min"
                or clean_units == "gal/minute"
                or clean_units == "gallon/min"
                or clean_units == "gallon/minute"
                or clean_units == "gallons/min"
                or clean_units == "gallons/minute"
            ):
                return u.gal / u.min
            elif (
                clean_units == "gal"
                or clean_units == "gallon"
                or clean_units == "gallons"
            ):
                return u.gal
            elif (
                clean_units == "gpd"
                or clean_units == "galperday"
                or clean_units == "gallonperday"
                or clean_units == "gallonsperday"
                or clean_units == "gal/d"
                or clean_units == "gal/day"
                or clean_units == "gallon/d"
                or clean_units == "gallon/day"
                or clean_units == "gallons/d"
                or clean_units == "gallons/day"
            ):
                return u.gal / u.day
            elif (
                clean_units == "m/s"
                or clean_units == "meter/s"
                or clean_units == "meters/s"
                or clean_units == "m/second"
                or clean_units == "meter/second"
                or clean_units == "meters/second"
            ):
                return u.m / u.s
            elif (
                clean_units == "cubicmeters/day"
                or clean_units == "m3pd"
                or clean_units == "cubicmeter/day"
                or clean_units == "m**3/day"
                or clean_units == "m^3/day"
                or clean_units == "m3/day"
                or clean_units == "meter3/day"
                or clean_units == "meter**3/day"
                or clean_units == "meter^3/day"
                or clean_units == "meters3/day"
                or clean_units == "meters**3/day"
                or clean_units == "meters^3/day"
                or clean_units == "cubicmeters/d"
                or clean_units == "cubicmeter/d"
                or clean_units == "m**3/d"
                or clean_units == "m^3/d"
                or clean_units == "m3/d"
                or clean_units == "meter3/d"
                or clean_units == "meter**3/d"
                or clean_units == "meter^3/d"
                or clean_units == "meters3/d"
                or clean_units == "meters**3/d"
                or clean_units == "meters^3/d"
            ):
                return u.m**3 / u.day
            elif (
                clean_units == "psi"
                or clean_units == "poundspersquareinch"
                or clean_units == "poundpersquareinch"
                or clean_units == "poundspersquarein"
                or clean_units == "poundpersquarein"
                or clean_units == "poundspersqin"
                or clean_units == "poundpersqin"
                or clean_units == "pound/inch**2"
                or clean_units == "pounds/inch**2"
                or clean_units == "lbs/inch**2"
                or clean_units == "lb/inch**2"
                or clean_units == "pound/inch^2"
                or clean_units == "pounds/inch^2"
                or clean_units == "lbs/inch^2"
                or clean_units == "lb/inch^2"
                or clean_units == "pound/squareinch"
                or clean_units == "pounds/squareinch"
                or clean_units == "lbs/squareinch"
                or clean_units == "lb/squareinch"
                or clean_units == "pound/in**2"
                or clean_units == "pounds/in**2"
                or clean_units == "lbs/in**2"
                or clean_units == "lb/in**2"
                or clean_units == "pound/in^2"
                or clean_units == "pounds/in^2"
                or clean_units == "lbs/in^2"
                or clean_units == "lb/in^2"
            ):
                return u.force_pound / (u.inch**2)
            elif (
                clean_units == "btu"
                or clean_units == "btus"
                or clean_units == "britishthermalunit"
                or clean_units == "britishthermalunits"
            ):
                return u.BTU
            elif (
                clean_units == "btu/scf"
                or clean_units == "btus/scf"
                or clean_units == "britishthermalunit/scf"
                or clean_units == "britishthermalunits/scf"
                or clean_units == "btu/cubicfeet"
                or clean_units == "btus/cubicfeet"
                or clean_units == "britishthermalunit/cubicfeet"
                or clean_units == "britishthermalunits/cubicfeet"
                or clean_units == "btu/cubicfoot"
                or clean_units == "btus/cubicfoot"
                or clean_units == "britishthermalunit/cubicfoot"
                or clean_units == "britishthermalunits/cubicfoot"
                or clean_units == "btu/ft3"
                or clean_units == "btus/ft3"
                or clean_units == "britishthermalunit/ft3"
                or clean_units == "britishthermalunits/ft3"
                or clean_units == "btu/ft**3"
                or clean_units == "btus/ft**3"
                or clean_units == "britishthermalunit/ft**3"
                or clean_units == "britishthermalunits/ft**3"
                or clean_units == "btu/ft^3"
                or clean_units == "btus/ft^3"
                or clean_units == "britishthermalunit/ft^3"
                or clean_units == "britishthermalunits/ft^3"
                or clean_units == "btu/foot3"
                or clean_units == "btus/foot3"
                or clean_units == "britishthermalunit/foot3"
                or clean_units == "britishthermalunits/foot3"
                or clean_units == "btu/foot**3"
                or clean_units == "btus/foot**3"
                or clean_units == "britishthermalunit/foot**3"
                or clean_units == "britishthermalunits/foot**3"
                or clean_units == "btu/feet3"
                or clean_units == "btus/feet3"
                or clean_units == "britishthermalunit/feet3"
                or clean_units == "britishthermalunits/feet3"
                or clean_units == "btu/foot^3"
                or clean_units == "btus/foot^3"
                or clean_units == "britishthermalunit/foot^3"
                or clean_units == "britishthermalunits/foot^3"
                or clean_units == "btu/feet**3"
                or clean_units == "btus/feet**3"
                or clean_units == "britishthermalunit/feet**3"
                or clean_units == "britishthermalunits/feet**3"
                or clean_units == "btu/feet^3"
                or clean_units == "btus/feet^3"
                or clean_units == "britishthermalunit/feet^3"
                or clean_units == "britishthermalunits/feet^3"
            ):
                return u.BTU / (u.ft**3)
            elif (
                clean_units == "kw*hour/scfm"
                or clean_units == "kwhr/scfm"
                or clean_units == "kwh/scfm"
                or clean_units == "kilowatthr/scfm"
                or clean_units == "kilowatthour/scfm"
                or clean_units == "kilowatt*hour/scfm"
                or clean_units == "kw*hour/ft**3*min"
                or clean_units == "kwhr/ft**3*min"
                or clean_units == "kwh/ft**3*min"
                or clean_units == "kilowatthr/ft**3*min"
                or clean_units == "kilowatthour/ft**3*min"
                or clean_units == "kilowatt*hour/ft**3*min"
            ):
                return u.kW * u.hr / u.ft**3 * u.min
            elif (
                clean_units == "kwh"
                or clean_units == "kwhr"
                or clean_units == "kilowatthr"
                or clean_units == "hour*kilowatt"
                or clean_units == "kilowatt*hour"
                or clean_units == "kilowatthour"
            ):
                return u.kW * u.hr
            elif (
                clean_units == "kilowatt*hour/meter**3"
                or clean_units == "hour*kilowatt/meter**3"
                or clean_units == "kwh/meter**3"
                or clean_units == "kwhr/meter**3"
                or clean_units == "kilowatthr/meter**3"
                or clean_units == "kilowatthour/meter**3"
                or clean_units == "kilowatt*hour/m^3"
                or clean_units == "hour*kilowatt/m^3"
                or clean_units == "kwh/m^3"
                or clean_units == "kwhr/m^3"
                or clean_units == "kilowatthr/m^3"
                or clean_units == "kilowatthour/m^3"
                or clean_units == "kilowatt*hour/cubicmeters"
                or clean_units == "hour*kilowatt/cubicmeters"
                or clean_units == "kwh/cubicmeters"
                or clean_units == "kwhr/cubicmeters"
                or clean_units == "kilowatthr/cubicmeters"
                or clean_units == "kilowatthour/cubicmeters"
                or clean_units == "kilowatt*hour/cubicmeter"
                or clean_units == "hour*kilowatt/cubicmeter"
                or clean_units == "kwh/cubicmeter"
                or clean_units == "kwhr/cubicmeter"
                or clean_units == "kilowatthr/cubicmeter"
                or clean_units == "kilowatthour/cubicmeter"
                or clean_units == "kilowatt*hour/m**3"
                or clean_units == "hour*kilowatt/m**3"
                or clean_units == "kwh/m**3"
                or clean_units == "kwhr/m**3"
                or clean_units == "kilowatthr/m**3"
                or clean_units == "kilowatthour/m**3"
                or clean_units == "kilowatt*hour/m3"
                or clean_units == "hour*kilowatt/m3"
                or clean_units == "kwh/m3"
                or clean_units == "kwhr/m3"
                or clean_units == "kilowatthr/m3"
                or clean_units == "kilowatthour/m3"
                or clean_units == "kilowatt*hour/meter3"
                or clean_units == "hour*kilowatt/meter3"
                or clean_units == "kwh/meter3"
                or clean_units == "kwhr/meter3"
                or clean_units == "kilowatthr/meter3"
                or clean_units == "kilowatthour/meter3"
                or clean_units == "kilowatt*hour/meter^3"
                or clean_units == "hour*kilowatt/meter^3"
                or clean_units == "kwh/meter^3"
                or clean_units == "kwhr/meter^3"
                or clean_units == "kilowatthr/meter^3"
                or clean_units == "kilowatthour/meter^3"
                or clean_units == "kilowatt*hour/meters3"
                or clean_units == "hour*kilowatt/meters3"
                or clean_units == "kwh/meters3"
                or clean_units == "kwhr/meters3"
                or clean_units == "kilowatthr/meters3"
                or clean_units == "kilowatthour/meters3"
                or clean_units == "kilowatt*hour/meters**3"
                or clean_units == "hour*kilowatt/meters**3"
                or clean_units == "kwh/meters**3"
                or clean_units == "kwhr/meters**3"
                or clean_units == "kilowatthr/meters**3"
                or clean_units == "kilowatthour/meters**3"
                or clean_units == "kilowatt*hour/meters^3"
                or clean_units == "hour*kilowatt/meters^3"
                or clean_units == "kwh/meters^3"
                or clean_units == "kwhr/meters^3"
                or clean_units == "kilowatthr/meters^3"
                or clean_units == "kilowatthour/meters^3"
            ):
                return u.kW * u.hr / (u.m**3)
            elif clean_units == "kw" or clean_units == "kilowatt":
                return u.kW
            elif (
                clean_units == "meters" or clean_units == "m" or clean_units == "meter"
            ):
                return u.m
            elif (
                clean_units == "inches" or clean_units == "in" or clean_units == "inch"
            ):
                return u.inch
            elif (
                clean_units == "hz"
                or clean_units == "hertz"
                or clean_units == "1/s"
                or clean_units == "1/second"
                or clean_units == "1/sec"
            ):
                return u.Hz
            elif (
                clean_units == "lmh"
                or clean_units == "liter**2/meters**2/hour"
                or clean_units == "liter^2/meters^2/hour"
                or clean_units == "liter2/meters2/hour"
                or clean_units == "liter^2/hour/meters^2"
                or clean_units == "liter**2/hour/meters**2"
                or clean_units == "liter2/hour/meters2"
                or clean_units == "l**2/m**2/h"
                or clean_units == "l^2/m^2/h"
                or clean_units == "l2/m2/h"
                or clean_units == "l^2/h/m^2"
                or clean_units == "l**2/h/m**2"
                or clean_units == "l2/h/m2"
            ):
                return u.LMH
            elif (
                clean_units == "permeability"
                or clean_units == "lmh/bar"
                or clean_units == "flux_lmh/bar"
                or clean_units == "liter**2/meters**2/hour/bar"
                or clean_units == "liter^2/meters^2/hour/bar"
                or clean_units == "liter2/meters2/hour/bar"
                or clean_units == "liter^2/hour/meters^2/bar"
                or clean_units == "liter**2/hour/meters**2/bar"
                or clean_units == "liter2/hour/meters2/bar"
                or clean_units == "l**2/m**2/h/bar"
                or clean_units == "l^2/m^2/h/bar"
                or clean_units == "l2/m2/h/bar"
                or clean_units == "l^2/h/m^2/bar"
                or clean_units == "l**2/h/m**2/bar"
                or clean_units == "l2/h/m2/bar"
            ):
                return u.LMH / u.bar
            elif (
                clean_units == "intensity"
                or clean_units == "w/m**2"
                or clean_units == "w/m^2"
                or clean_units == "w/m2"
                or clean_units == "w/meter**2"
                or clean_units == "w/meter^2"
                or clean_units == "w/meter2"
                or clean_units == "watt/meter**2"
                or clean_units == "watt/meter^2"
                or clean_units == "watt/meter2"
            ):
                return u.W / (u.m**2)
            else:
                raise UndefinedUnitError("Unsupported unit: " + units)


class ContentsType(Enum):
    """Class to represent any possible contents,
    whether they are sludge, water, or gas"""

    UntreatedSewage = auto()
    PrimaryEffluent = auto()
    SecondaryEffluent = auto()
    TertiaryEffluent = auto()
    TreatedSewage = auto()
    DrinkingWater = auto()
    PotableReuse = auto()
    NonpotableReuse = auto()
    Biogas = auto()
    NaturalGas = auto()
    GasBlend = auto()
    FatOilGrease = auto()
    PrimarySludge = auto()
    TPS = auto()  # thickened primary sludge
    WasteActivatedSludge = auto()
    TWAS = auto()  # thickened waste activated sludge
    Scum = auto()
    FoodWaste = auto()
    SludgeBlend = auto()
    ThickenedSludgeBlend = auto()
    Electricity = auto()
    Brine = auto()
    Seawater = auto()
    SurfaceWater = auto()
    Groundwater = auto()
    Stormwater = auto()
    Heat = auto()
    Oil = auto()
    Grease = auto()
    Air = auto()
    Oxygen = auto()
    IdealGas = auto()
    Chemical = auto()
    Coagulant = auto()
    Disinfectant = auto()
    Deodorant = auto()
    IndustrialWastewater = auto()
    MunicipalWastewater = auto()
    DisinfectedEffluent = auto()
    SolidWaste = auto()
    PretreatedWater = auto()
    ProductWater = auto()
    ChlorinatedSeawater = auto()
    CoagulatedWater = auto()
    FilterBackwash = auto()
    Filtrate = auto()
    WFBS = auto()  # Water Filter Backwash Solids
    ControlSignal = auto()
    DataTransfer = auto()
    Antiscalant = auto()


class PumpType(Enum):
    """Enum to represent constant vs. variable drive pumps"""

    Constant = auto()
    VFD = auto()  # variable frequency drive
    ERD = auto()  # energy recovery device
    AirBlower = auto()


class DigesterType(Enum):
    """Enum to represent types of digesters"""

    Aerobic = auto()
    Anaerobic = auto()


class DosingType(Enum):
    """Enum to represent types of dosing"""

    NaOCl = auto()  # sodium hypochlorite
    FeCl3 = auto()  # ferric chloride
    Antiscalant = auto()
    CO2 = auto()  # carbon dioxide
    CaOH2 = auto()  # calcium hydroxide
    OrthoPolyphosphate = auto()
    SBS = auto()  # sodium bisulphite
    Polymer = auto()
    UVLight = auto()


def select_objs_helper(
    obj,
    obj_source_node=None,
    obj_dest_node=None,
    obj_source_unit_id=None,
    obj_dest_unit_id=None,
    obj_exit_point=None,
    obj_entry_point=None,
    source_id=None,
    dest_id=None,
    source_unit_id=None,
    dest_unit_id=None,
    exit_point_id=None,
    entry_point_id=None,
    source_node_type=None,
    dest_node_type=None,
    exit_point_type=None,
    entry_point_type=None,
    tag_type=None,
    recurse=False,
):
    """Helper to select from objects which match source/destination node class,
    unit ID, and contents

    Parameters
    ----------
    obj : [Node, Connection, Tag]
        Object to check if it meets the specified filtering criteria

    obj_source_node : Node
        Optional source `Node` to check the type and id of. None by default

    obj_dest_node : Node
        Optional destination `Node` to check the type and id of. None by default

    obj_source_unit_id : int, str
        Object's source unit ID to match against. None by default

    obj_dest_unit_id : int, str
        Object's destination unit ID to match against. None by default

    obj_exit_point : Node
        Optional `exit_point` `Node` to check the type and id of. None by default

    obj_entry_point : Node
        Optional `entry_point` `Node` to check the type and id of. None by default

    source_id : str
        Optional id of the source node to filter by. None by default

    dest_id : str
        Optional id of the destination node to filter by. None by default

    source_unit_id : int, str
        Optional unit id of the source to filter by. None by default

    dest_unit_id : int, str
        Optional unit id of the destination to filter by. None by default

    source_node_type : class
        Optional source `Node` subclass to filter by. None by default

    dest_node_type : class
        Optional destination `Node` subclass to filter by. None by default

    tag_type : TagType
        Optional tag type to filter by. None by default

    recurse : bool
        Whether to search for objects within nodes. False by default

    Raises
    ------
    ValueError
        When a source/destination node type is provided to subset tags

    TypeError
        When the objects to select among are not of type
        {'pype_schema.Tag' or `pype_schema.Connection`}

    Returns
    -------
    bool
        True if `obj` fits the filter criteria; False otherwise.
    """
    # convert string source and destination unit IDs to integers
    if isinstance(source_unit_id, str) and source_unit_id != "total":
        source_unit_id = int(source_unit_id)
    if isinstance(dest_unit_id, str) and dest_unit_id != "total":
        dest_unit_id = int(dest_unit_id)

    if source_id is not None and (
        not hasattr(obj_source_node, "id") or obj_source_node.id != source_id
    ):
        if (
            not recurse
            or not hasattr(obj_exit_point, "id")
            or obj_exit_point.id != source_id
        ):
            return False

    if dest_id is not None and (
        not hasattr(obj_dest_node, "id") or obj_dest_node.id != dest_id
    ):
        if (
            not recurse
            or not hasattr(obj_entry_point, "id")
            or obj_entry_point.id != dest_id
        ):
            return False

    if source_unit_id is not None and source_unit_id != obj_source_unit_id:
        return False

    if dest_unit_id is not None and dest_unit_id != obj_dest_unit_id:
        return False

    if exit_point_id is not None and (
        not hasattr(obj_exit_point, "id") or obj_exit_point.id != exit_point_id
    ):
        return False

    if entry_point_id is not None and (
        not hasattr(obj_entry_point, "id") or obj_entry_point.id != entry_point_id
    ):
        return False

    if source_node_type is not None and not isinstance(
        obj_source_node, source_node_type
    ):
        if not recurse or not isinstance(obj_exit_point, source_node_type):
            return False

    if dest_node_type is not None and not isinstance(obj_dest_node, dest_node_type):
        if not recurse or not isinstance(obj_entry_point, dest_node_type):
            return False

    if exit_point_type is not None and not isinstance(obj_exit_point, exit_point_type):
        return False

    if entry_point_type is not None and isinstance(obj_entry_point, entry_point_type):
        return False

    if tag_type is not None and (
        not hasattr(obj, "tag_type") or obj.tag_type != tag_type
    ):
        return False

    return True


def recursive_get(key, dict_):
    """Recursively search a nested dictionary for a key

    Parameters
    ----------
    key : str
        Key to search

    dict_ : dict
        (nested) dictionary to search

    Returns
    -------
    any, None
        Value of the key if found, None otherwise
    """
    if key in dict_:
        return dict_[key]
    elif isinstance(dict_, dict):
        for k, v in dict_.items():
            if isinstance(v, dict):
                item = recursive_get(key, v)
                if item is not None:
                    return item
