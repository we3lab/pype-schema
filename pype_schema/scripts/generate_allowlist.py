#!/usr/bin/env python3
"""Regenerate the allow-lists in ``operations.py`` and write ``allowlist_report.md``.
Pass ``--check`` to change nothing (for CI). The rules, the environment, and the exit
codes are described under Custom Mode in docs/advanced.rst.
"""

import argparse
import ast
import difflib
import importlib
import inspect
import os
import re
import sys
import textwrap
import types
import warnings

import numpy as np
import pandas as pd
import scipy
import scipy.stats

IO, EVAL, DISPATCH, STATE, NATIVE, ENV, OTHER = (
    "IO",
    "EVAL",
    "DISPATCH",
    "STATE",
    "NATIVE",
    "ENV",
    "OTHER",
)
CATEGORY_TITLES = {
    IO: "File, network, clipboard, database, or pickle I/O",
    EVAL: "Evaluates code or expression strings",
    DISPATCH: "Turns a string into a function or attribute lookup",
    STATE: (
        "Changes process-wide state (config, global RNG seed, registries, "
        "mutable globals)"
    ),
    NATIVE: "Raw memory or native-code interface",
    ENV: "Reveals the environment (paths, build config, versions, source)",
    OTHER: (
        "Not computation on data, or not reviewed (plotting, testing, typing, "
        "deprecated, internals)"
    ),
}

# Methods that resolve a *string* argument to an attribute (``x.agg("sum")``).
# They are not in ALLOWED_ATTRIBUTES; operations.py allows them only
# when called directly with a statically known callable (never a string).
GUARDED_METHODS = ("agg", "aggregate", "apply", "transform")

# Namespaces that are enumerated. Everything else (deprecated aliases such as
# scipy.stats.stats, internals, I/O modules, ...) is excluded wholesale.
NAMESPACES = [
    ("math",),
    ("numpy",),
    ("numpy", "char"),
    ("numpy", "emath"),
    ("numpy", "fft"),
    ("numpy", "linalg"),
    ("numpy", "ma"),
    ("numpy", "polynomial"),
    ("numpy", "polynomial", "chebyshev"),
    ("numpy", "polynomial", "hermite"),
    ("numpy", "polynomial", "hermite_e"),
    ("numpy", "polynomial", "laguerre"),
    ("numpy", "polynomial", "legendre"),
    ("numpy", "polynomial", "polynomial"),
    ("numpy", "random"),
    ("numpy", "strings"),
    ("pandas",),
    ("pandas", "offsets"),
    ("scipy",),
    ("scipy", "cluster"),
    ("scipy", "cluster", "hierarchy"),
    ("scipy", "cluster", "vq"),
    ("scipy", "constants"),
    ("scipy", "differentiate"),
    ("scipy", "fft"),
    ("scipy", "fftpack"),
    ("scipy", "integrate"),
    ("scipy", "interpolate"),
    ("scipy", "linalg"),
    ("scipy", "linalg", "interpolative"),
    ("scipy", "ndimage"),
    ("scipy", "optimize"),
    ("scipy", "signal"),
    ("scipy", "signal", "windows"),
    ("scipy", "sparse"),
    ("scipy", "sparse", "csgraph"),
    ("scipy", "sparse", "linalg"),
    ("scipy", "spatial"),
    ("scipy", "spatial", "distance"),
    ("scipy", "spatial", "transform"),
    ("scipy", "special"),
    ("scipy", "stats"),
    ("scipy", "stats", "contingency"),
    ("scipy", "stats", "mstats"),
    ("scipy", "stats", "qmc"),
    ("scipy", "stats", "sampling"),
]
NAMESPACE_SET = set(NAMESPACES)

# Names that look excluded by a rule below but were reviewed and are safe.
# key: ("dotted.namespace", "name")
KEEP = {
    (
        "pandas",
        "json_normalize",
    ): "builds a DataFrame from nested dicts; in-memory only",
    ("numpy", "recarray"): "`buf` is an in-memory buffer, not a path",
    ("numpy", "interp"): "`fp` is the array of function values, not a file pointer",
    ("numpy", "isdtype"): "mentions ctypes only as a dtype-kind name",
    (
        "numpy.ma",
        "set_fill_value",
    ): "sets the fill value of one masked array, not global state",
    (
        "scipy.stats.contingency",
        "crosstab",
    ): "numeric contingency table; unrelated to pandas.crosstab",
}

# Attribute names (on ordinary objects) that a rule would exclude but are safe.
KEEP_ATTRS = {
    "to_device": "`stream` is an array-API device stream, not a file",
}

# Explicit exclusions. key: ("dotted.namespace" or "*", "name")
EXPLICIT = {
    # top-level numpy
    ("numpy", "bmat"): (
        DISPATCH,
        "resolves names in a string from the caller's stack frame",
    ),
    ("numpy", "ScalarType"): (
        NATIVE,
        "contains the builtin `memoryview`, which SAFE_BUILTINS withholds",
    ),
    ("numpy", "from_dlpack"): (NATIVE, "wraps foreign memory buffers"),
    ("numpy", "errstate"): (
        STATE,
        "context manager that changes global floating-point error handling",
    ),
    ("numpy", "printoptions"): (
        STATE,
        "context manager that changes global print options",
    ),
    ("numpy", "core"): (OTHER, "deprecated alias of a private package"),
    ("numpy", "ctypeslib"): (NATIVE, "loads shared libraries and exposes raw pointers"),
    ("numpy", "dtypes"): (OTHER, "dtype class registry; not needed to compute on data"),
    ("numpy", "exceptions"): (OTHER, "exception classes"),
    ("numpy", "f2py"): (EVAL, "compiles and imports Fortran/C code"),
    ("numpy", "lib"): (
        IO,
        "contains npyio (file I/O) and stride_tricks.as_strided "
        "(unchecked memory views)",
    ),
    ("numpy", "rec"): (IO, "record-array helpers include fromfile"),
    ("numpy", "testing"): (OTHER, "test runners and assertions (some execute code)"),
    ("numpy", "typing"): (OTHER, "typing helpers"),
    # pandas
    ("pandas", "eval"): (EVAL, "evaluates an expression string"),
    ("pandas", "pivot_table"): (DISPATCH, "`aggfunc` string is resolved by name"),
    ("pandas", "crosstab"): (DISPATCH, "`aggfunc` string is resolved by name"),
    ("pandas", "NamedAgg"): (DISPATCH, "`aggfunc` string is resolved by name"),
    ("pandas", "NamedFunc"): (DISPATCH, "`aggfunc` string is resolved by name"),
    ("pandas", "col"): (
        OTHER,
        "deferred-expression API (new in pandas 3); not reviewed",
    ),
    ("pandas", "annotations"): (OTHER, "leaked `__future__` feature object"),
    ("pandas", "api"): (
        STATE,
        "includes extension-registration functions that patch pandas classes",
    ),
    ("pandas", "arrays"): (OTHER, "extension-array classes; use pd.array"),
    ("pandas", "compat"): (OTHER, "internal compatibility helpers"),
    ("pandas", "core"): (OTHER, "private package"),
    ("pandas", "errors"): (OTHER, "exception classes"),
    ("pandas", "io"): (IO, "all pandas I/O"),
    ("pandas", "pandas"): (OTHER, "self-reference"),
    ("pandas", "plotting"): (OTHER, "plotting (matplotlib)"),
    ("pandas", "testing"): (OTHER, "test assertions"),
    ("pandas", "tseries"): (OTHER, "use pd.offsets / pd.date_range"),
    ("pandas", "util"): (OTHER, "internal utilities"),
    # scipy
    ("scipy", "LowLevelCallable"): (NATIVE, "wraps raw C function pointers"),
    ("scipy", "datasets"): (IO, "downloads data files from the network"),
    ("scipy", "io"): (IO, "reads and writes files"),
    ("scipy", "odr"): (OTHER, "deprecated in recent SciPy releases"),
    ("scipy.linalg", "blas"): (NATIVE, "raw Fortran BLAS wrappers"),
    ("scipy.linalg", "lapack"): (NATIVE, "raw Fortran LAPACK wrappers"),
    ("scipy.linalg", "cython_blas"): (NATIVE, "exposes C function pointers"),
    ("scipy.linalg", "cython_lapack"): (NATIVE, "exposes C function pointers"),
    ("scipy.special", "cython_special"): (NATIVE, "exposes C function pointers"),
    ("scipy.optimize", "cython_optimize"): (NATIVE, "exposes C function pointers"),
    ("numpy.ma", "masked_print_option"): (
        STATE,
        "mutable global object that controls masked-array printing",
    ),
    ("scipy.spatial", "convex_hull_plot_2d"): (OTHER, "plotting (matplotlib)"),
    ("scipy.spatial", "delaunay_plot_2d"): (OTHER, "plotting (matplotlib)"),
    ("scipy.spatial", "voronoi_plot_2d"): (OTHER, "plotting (matplotlib)"),
    ("scipy.optimize", "show_options"): (ENV, "prints documentation to stdout"),
    ("scipy.special", "print_coercion_tables"): (ENV, "prints to stdout"),
    ("scipy.cluster.hierarchy", "dendrogram"): (OTHER, "plotting (matplotlib)"),
    ("scipy.cluster.hierarchy", "set_link_color_palette"): (
        STATE,
        "global matplotlib color palette",
    ),
    ("scipy.constants", "physical_constants"): (
        STATE,
        "mutable dict shared by the whole process; use constants.value()",
    ),
}

# Name patterns, tried in order after EXPLICIT. (regex, category, reason, scope)
# scope: "module" = names reached through a library, "attr" = attributes of
# ordinary objects (Series, ndarray, str, ...), "both".
NAME_RULES = [
    # I/O
    (r"read_\w+", IO, "reads a file, URL, clipboard, or database", "module"),
    (
        r"(load|loads|loadtxt|loadmat|load_npz|loadarff)",
        IO,
        "reads a file or unpickles data",
        "both",
    ),
    (
        r"(save|savez|savez_compressed|savetxt|savemat|save_npz|to_pickle)",
        IO,
        "writes a file",
        "both",
    ),
    (
        r"(dump|dumps|tofile|fromfile|fromregex|genfromtxt|recfromtxt|recfromcsv)",
        IO,
        "reads/writes a file or pickles data",
        "both",
    ),
    (
        r"(memmap|DataSource|open|ExcelFile|ExcelWriter|HDFStore)",
        IO,
        "opens files or other external resources",
        "both",
    ),
    (
        r"to_(csv|excel|json|hdf|sql|parquet|feather|html|latex|markdown|xml|"
        r"clipboard|stata|orc|gbq|xarray|string|iceberg)",
        IO,
        "writes to a path, buffer, or clipboard, or hands off to an external library",
        "attr",
    ),
    # evaluation
    (
        r"(eval|exec|execfile|compile|query)",
        EVAL,
        "evaluates code or an expression string",
        "both",
    ),
    (
        r"(format|format_map)",
        EVAL,
        "format-string fields can traverse attributes (e.g. `{0.__class__}`)",
        "attr",
    ),
    # dispatch by name
    (
        r"(pivot_table|crosstab|NamedAgg|NamedFunc)",
        DISPATCH,
        "`aggfunc` string is resolved by name",
        "both",
    ),
    # process-wide state
    (
        r"(set_\w+|reset_\w+|use_\w+|register_\w+|unregister_\w+|add_newdoc\w*|"
        r"add_docstring|seterr|seterrcall|setbufsize|errstate|printoptions|seed|"
        r"option_context|options|skip_backend)",
        STATE,
        "changes process-wide configuration or state",
        "module",
    ),
    # native / memory
    (
        r"(as_strided|byte_bounds|from_dlpack|LowLevelCallable|ctypeslib|"
        r"get_blas_funcs|get_lapack_funcs|cython_\w+)",
        NATIVE,
        "raw memory or native-code interface",
        "module",
    ),
    (
        r"(seed|set_state)",
        STATE,
        "reseeds a random generator, which can be the shared global one",
        "attr",
    ),
    (r"(ctypes|cffi)", NATIVE, "exposes raw pointers / C function pointers", "attr"),
    (r"ids", NATIVE, "returns raw memory addresses", "both"),
    (r"lock", OTHER, "exposes an internal threading lock", "attr"),
    (
        r"resize",
        NATIVE,
        "in-place resize (refcheck=False) can leave other views dangling",
        "attr",
    ),
    (
        r"setflags",
        NATIVE,
        "can mark memory writeable/aligned without the usual checks",
        "attr",
    ),
    # environment
    (
        r"(get_include|info|lookfor|source|who|test|tests|show_config|show_runtime|"
        r"show_versions|get_option|describe_option)",
        ENV,
        "reveals paths, build configuration, versions, or source",
        "module",
    ),
    (r"info", ENV, "prints a summary to stdout or a buffer", "attr"),
    # no computation on data
    (
        r"(plot|hist|boxplot|style|dendrogram)",
        OTHER,
        "plotting or styling (matplotlib / jinja2)",
        "both",
    ),
    (r"assert_\w+", OTHER, "test assertion", "both"),
]
NAME_RULES = [(re.compile(p), c, r, s) for p, c, r, s in NAME_RULES]

# Functions defined in these modules are excluded unless KEEP says otherwise.
ORIGIN_RULES = [
    ("pandas.io", IO, "defined in pandas.io"),
    ("scipy.io", IO, "defined in scipy.io"),
    ("scipy.datasets", IO, "defined in scipy.datasets"),
    ("numpy.lib.npyio", IO, "defined in numpy.lib.npyio"),
    ("numpy.lib._npyio_impl", IO, "defined in numpy's file I/O module"),
    ("numpy.testing", OTHER, "defined in numpy.testing"),
    ("numpy.f2py", EVAL, "defined in numpy.f2py"),
    ("numpy.ctypeslib", NATIVE, "defined in numpy.ctypeslib"),
    ("pandas.plotting", OTHER, "defined in pandas.plotting"),
    ("pandas.util._print_versions", ENV, "defined in pandas' version reporter"),
    ("pandas.util._tester", OTHER, "defined in pandas' test runner"),
    ("pandas._config", STATE, "defined in pandas' configuration system"),
    ("matplotlib", OTHER, "defined in matplotlib"),
]

# A library may only expose its own API. Functions/classes defined in another
# package (e.g. functools.reduce imported into scipy.stats.contingency) are
# leaked imports, not part of the API.
ALLOWED_ORIGIN_ROOTS = {
    "math": {"math"},
    "numpy": {"numpy"},
    "pandas": {"pandas"},
    "scipy": {"scipy"},
}

# Executable source (docstrings stripped) of functions written in Python is scanned for
# these. Compiled functions cannot be scanned and rely on the name/signature rules.
SOURCE_RULES = [
    (r"matplotlib|pyplot", OTHER, "imports matplotlib"),
    (
        r"subprocess|os\.system|os\.popen|os\.environ|os\.remove|os\.unlink|"
        r"shutil|tempfile|os\.makedirs|os\.mkdir",
        IO,
        "starts processes or changes the filesystem",
    ),
    (r"urllib|socket|requests|http\.client|ftplib|smtplib", IO, "uses the network"),
    (r"(?<![\w.])open\(|pathlib|Path\(|\.read_text|\.write_text", IO, "opens files"),
    (r"pickle|marshal|shelve", IO, "uses pickle/marshal"),
    (
        r"importlib|__import__|(?<![\w.])(eval|exec)\(|_getframe|currentframe|"
        r"f_globals|f_locals",
        EVAL,
        "imports modules, evaluates code, or inspects stack frames",
    ),
    (r"ctypes|cffi", NATIVE, "uses ctypes/cffi"),
]
SOURCE_RULES = [(re.compile(p), c, r) for p, c, r in SOURCE_RULES]
_source_cache = {}

# Parameter names that mean "this function touches a file/URL/database".
IO_PARAMS = {
    "path",
    "path_or_buf",
    "path_or_buffer",
    "buf",
    "filepath",
    "filepath_or_buffer",
    "fname",
    "fid",
    "file",
    "filename",
    "fp",
    "fileobj",
    "excel_writer",
    "con",
    "conn",
    "url",
    "outfile",
    "out_file",
    "stream",
}

# Attribute names on result objects that are created by calling a function
# (so they cannot be found by looking at classes). Reviewed: all plain data.
EXTRA_ATTRIBUTES = (
    # OptimizeResult
    "x fun success status message nit nfev njev nhev jac hess hess_inv maxcv "
    # RootResults
    "root converged iterations function_calls flag "
    # OdeResult
    "t y t_events y_events sol "
)


class Deprecated:
    """Marks a library member that warns or fails when it is read."""


def public_members(module):
    """Public members of a module, with deprecated ones marked.

    Parameters
    ----------
    module : module
        The module to list

    Returns
    -------
    dict
        Maps each public name to its object, or to a `Deprecated` marker if reading it
        warns or fails
    """
    out = {}
    for name in dir(module):
        if name.startswith("_"):
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            try:
                out[name] = getattr(module, name)
            except (Warning, ImportError, AttributeError):
                out[name] = Deprecated()
    return out


def resolve_namespace(ns):
    """The module object for a namespace path.

    Parameters
    ----------
    ns : tuple of str
        A namespace path such as ``("numpy", "emath")``

    Returns
    -------
    module
        The module that `ns` names
    """
    obj = importlib.import_module(ns[0])
    for i, part in enumerate(ns[1:], start=1):
        try:
            obj = getattr(obj, part)
        except AttributeError:
            obj = importlib.import_module(".".join(ns[: i + 1]))
    return obj


def io_params(obj):
    """The file-like parameter names of a callable.

    Parameters
    ----------
    obj : callable
        The function or class to inspect

    Returns
    -------
    set of str or None
        Parameters that look like they take a file, or None if there is no signature
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            params = set(inspect.signature(obj).parameters)
    except (TypeError, ValueError):
        return None
    return params & IO_PARAMS


def executable_source(obj):
    """Source of a function or method written in Python, without docstrings.

    Parameters
    ----------
    obj : callable
        The function, method, or class to read

    Returns
    -------
    str or None
        The source, or None if it is not available (for example compiled code)
    """
    try:
        code = textwrap.dedent(inspect.getsource(obj))
        tree = ast.parse(code)
    except (TypeError, OSError, SyntaxError):
        return None
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)
        ):
            body = node.body
            first = body[0] if body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def source_verdict(obj):
    """Whether the source of a function does something that is excluded.

    Parameters
    ----------
    obj : callable
        The function, method, or class to scan

    Returns
    -------
    tuple or None
        ``(category, reason)`` if the source matches a SOURCE_RULES pattern
    """
    if inspect.isclass(obj):
        obj = getattr(obj, "__init__", None)
    if not inspect.isfunction(obj):
        return None
    key = id(obj)
    if key not in _source_cache:
        verdict = None
        code = executable_source(obj)
        if code:
            for pattern, category, reason in SOURCE_RULES:
                match = pattern.search(code)
                if match:
                    verdict = (category, f"source scan: {reason} ({match.group(0)!r})")
                    break
        _source_cache[key] = verdict
    return _source_cache[key]


def match_name_rules(name, scope):
    """The first NAME_RULES entry that excludes a name.

    Parameters
    ----------
    name : str
        The member or attribute name

    scope : str
        ``"module"`` for library members, ``"attr"`` for attributes of ordinary objects

    Returns
    -------
    tuple or None
        ``(category, reason)`` of the first matching rule
    """
    for pattern, category, reason, rule_scope in NAME_RULES:
        if rule_scope in (scope, "both") and pattern.fullmatch(name):
            return category, reason
    return None


def classify_member(ns, name, obj, unknown_signatures):
    """Decide whether a library member is excluded.

    Parameters
    ----------
    ns : tuple of str
        The namespace the member is in, such as ``("numpy", "linalg")``

    name : str
        The member's name

    obj : object
        The member itself

    unknown_signatures : list of str
        Collects callables whose signature cannot be inspected (changed in place)

    Returns
    -------
    tuple or None
        ``(category, reason)`` if the member is excluded
    """
    key = ".".join(ns)
    if (key, name) in KEEP:
        return None
    rule = EXPLICIT.get((key, name)) or EXPLICIT.get(("*", name))
    if rule:
        return rule
    if isinstance(obj, Deprecated):
        return (
            OTHER,
            "deprecated alias (accessing it warns) or optional dependency missing",
        )
    if isinstance(obj, types.ModuleType):
        return (
            OTHER,
            "namespace not enumerated (deprecated alias, internal, or not needed)",
        )
    hit = match_name_rules(name, "module")
    if hit:
        return hit
    origin = getattr(obj, "__module__", None)
    if (
        isinstance(origin, str)
        and origin.split(".")[0] not in ALLOWED_ORIGIN_ROOTS[ns[0]]
    ):
        return OTHER, f"leaked import from another package ({origin})"
    if isinstance(origin, str):
        for prefix, category, reason in ORIGIN_RULES:
            if (
                origin == prefix
                or origin.startswith(prefix + ".")
                or origin.startswith(prefix)
            ):
                return category, f"{reason} ({origin})"
    if callable(obj) and not isinstance(obj, np.ufunc):
        params = io_params(obj)
        if params:
            return IO, f"has file-like parameter(s) {sorted(params)}"
        if params is None and inspect.isroutine(obj):
            unknown_signatures.append(f"{key}.{name}")
    if isinstance(obj, (dict, list, set, bytearray)):
        return STATE, f"mutable {type(obj).__name__} shared by the whole process"
    return source_verdict(obj)


def build_namespaces():
    """Enumerate the allowed members of every namespace in NAMESPACES.

    Returns
    -------
    tree : dict
        Maps each namespace path to its allowed ``names`` and ``modules``

    excluded : list of tuple
        ``(category, namespace, name, reason)`` for each excluded member

    unknown_signatures : list of str
        Callables whose signature cannot be inspected
    """
    tree = {}  # dotted path -> {"names": set, "modules": set}
    excluded = []  # (category, namespace, name, reason)
    unknown_signatures = []
    for ns in NAMESPACES:
        module = resolve_namespace(ns)
        names, children = set(), set()
        for name, obj in public_members(module).items():
            if isinstance(obj, types.ModuleType) and ns + (name,) in NAMESPACE_SET:
                children.add(name)
                continue
            verdict = classify_member(ns, name, obj, unknown_signatures)
            if verdict:
                excluded.append((verdict[0], ".".join(ns), name, verdict[1]))
            else:
                names.add(name)
        tree[ns] = {"names": names, "modules": children}
    # a submodule that is not imported yet may be missing from dir(parent)
    for ns in NAMESPACES:
        if len(ns) > 1:
            tree[ns[:-1]]["modules"].add(ns[-1])
    return tree, excluded, unknown_signatures


def attribute_universe(tree):
    """The objects whose attributes a custom operation may touch.

    Parameters
    ----------
    tree : dict
        Allowed members per namespace; members that are excluded are skipped

    Returns
    -------
    list of tuple
        ``(label, class or instance)`` for each object
    """
    items = []

    def add(label, obj):
        """Record an object whose attributes are to be enumerated.

        Parameters
        ----------
        label : str
            A name for the object, used in the report

        obj : class or instance
            The object to take attribute names from
        """
        items.append((label, obj))

    for t in (
        str,
        bytes,
        int,
        float,
        complex,
        bool,
        list,
        tuple,
        dict,
        set,
        frozenset,
        range,
        slice,
    ):
        add(t.__name__, t)

    arr = np.arange(6.0).reshape(2, 3)
    for label, obj in [
        ("ndarray", np.ndarray),
        ("float64", np.float64),
        ("int64", np.int64),
        ("bool_", np.bool_),
        ("complex128", np.complex128),
        ("datetime64", np.datetime64),
        ("timedelta64", np.timedelta64),
        ("str_", np.str_),
        ("dtype", np.dtype),
        ("dtype instance", type(np.dtype("f8"))),
        ("flatiter", type(arr.flat)),
        ("ufunc", type(np.add)),
        ("matrix", np.matrix),
        ("MaskedArray", np.ma.MaskedArray),
        ("poly1d", np.poly1d),
        ("vectorize", np.vectorize),
        ("finfo", np.finfo),
        ("iinfo", np.iinfo),
        ("nditer", np.nditer),
        ("broadcast", np.broadcast),
        ("Polynomial", np.polynomial.Polynomial),
        ("Chebyshev", np.polynomial.Chebyshev),
        ("Legendre", np.polynomial.Legendre),
        ("Laguerre", np.polynomial.Laguerre),
        ("Hermite", np.polynomial.Hermite),
        ("HermiteE", np.polynomial.HermiteE),
        ("Generator", np.random.Generator),
        ("RandomState", np.random.RandomState),
        ("PCG64", np.random.PCG64),
        ("SeedSequence", np.random.SeedSequence),
    ]:
        add(label, obj)

    idx = pd.date_range("2020-01-01", periods=4)
    s = pd.Series([1.0, 2.0, 3.0, 4.0], index=idx)
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0], "b": [1, 1, 2, 2]}, index=idx)
    for label, obj in [
        ("Series", pd.Series),
        ("DataFrame", pd.DataFrame),
        ("Index", pd.Index),
        ("DatetimeIndex", pd.DatetimeIndex),
        ("PeriodIndex", pd.PeriodIndex),
        ("TimedeltaIndex", pd.TimedeltaIndex),
        ("MultiIndex", pd.MultiIndex),
        ("RangeIndex", pd.RangeIndex),
        ("CategoricalIndex", pd.CategoricalIndex),
        ("IntervalIndex", pd.IntervalIndex),
        ("Timestamp", pd.Timestamp),
        ("Timedelta", pd.Timedelta),
        ("Period", pd.Period),
        ("Interval", pd.Interval),
        ("Categorical", pd.Categorical),
        ("DateOffset", pd.DateOffset),
        ("Flags", pd.Flags),
        ("Grouper", pd.Grouper),
        ("str accessor", type(pd.Series(["a"]).str)),
        ("dt accessor", type(pd.Series(idx).dt)),
        ("dt (timedelta)", type(pd.Series(pd.to_timedelta([1, 2], unit="D")).dt)),
        (
            "dt (period)",
            type(pd.Series(pd.period_range("2020", periods=2, freq="M")).dt),
        ),
        ("cat accessor", type(pd.Series(["a", "b"], dtype="category").cat)),
        ("sparse accessor", type(s.astype(pd.SparseDtype(float)).sparse)),
        ("DataFrameGroupBy", type(df.groupby("b"))),
        ("SeriesGroupBy", type(s.groupby([1, 1, 2, 2]))),
        ("Rolling", type(s.rolling(2))),
        ("Expanding", type(s.expanding())),
        ("ExponentialMovingWindow", type(s.ewm(span=2))),
        ("Resampler", type(s.resample("2D"))),
        ("NAType", type(pd.NA)),
        ("NaTType", type(pd.NaT)),
    ]:
        add(label, obj)

    # scipy: every class, and every module-level instance (e.g. stats.norm)
    for ns in NAMESPACES:
        if ns[0] != "scipy":
            continue
        module = resolve_namespace(ns)
        reachable = tree[ns]["names"]
        for name, obj in public_members(module).items():
            if name not in reachable or isinstance(obj, (Deprecated, types.ModuleType)):
                # excluded members cannot be reached, so their attributes do not matter
                continue
            if inspect.isclass(obj):
                add(f"{'.'.join(ns)}.{name}", obj)
            elif not callable(obj) and not isinstance(
                obj, (int, float, complex, str, bool, tuple, dict, list)
            ):
                add(f"{'.'.join(ns)}.{name}", type(obj))
    add("rv_frozen", type(scipy.stats.norm(0, 1)))
    add("rv_discrete_frozen", type(scipy.stats.poisson(2)))
    return items


def sample_results():
    """Result objects returned by functions, so their field names are seen.

    Returns
    -------
    list
        Instances such as the results of ``linregress`` or ``minimize``
    """
    import scipy.integrate as si
    import scipy.interpolate as sin
    import scipy.optimize as so
    import scipy.signal as ssg
    import scipy.sparse as ssp
    import scipy.spatial as ssa
    import scipy.stats as st

    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 7.0])
    y = np.array([1.1, 1.9, 3.2, 3.9, 5.1, 6.8])
    calls = [
        lambda: st.linregress(x, y),
        lambda: st.ttest_ind(x, y),
        lambda: st.ttest_1samp(x, 2),
        lambda: st.ttest_rel(x, y),
        lambda: st.mannwhitneyu(x, y),
        lambda: st.kstest(x, "norm"),
        lambda: st.ks_2samp(x, y),
        lambda: st.shapiro(x),
        lambda: st.pearsonr(x, y),
        lambda: st.spearmanr(x, y),
        lambda: st.kendalltau(x, y),
        lambda: st.describe(x),
        lambda: st.mode(x),
        lambda: st.f_oneway(x, y),
        lambda: st.theilslopes(y, x),
        lambda: st.binomtest(3, 10),
        lambda: st.anderson(x),
        lambda: st.chi2_contingency([[3, 4], [5, 6]]),
        lambda: st.bootstrap((x,), np.mean, n_resamples=50, random_state=0),
        lambda: st.norm.fit(x),
        lambda: st.rankdata(x),
        lambda: st.zscore(x),
        lambda: so.minimize(lambda v: (v[0] - 1) ** 2, [0.0]),
        lambda: so.minimize_scalar(lambda v: (v - 1) ** 2),
        lambda: so.root_scalar(lambda v: v - 1, bracket=[0, 2]),
        lambda: so.least_squares(lambda v: v - 1, [0.0]),
        lambda: so.linprog([1, 1], A_ub=[[-1, 0]], b_ub=[-1]),
        lambda: si.solve_ivp(lambda t, v: -v, (0, 1), [1.0]),
        lambda: sin.CubicSpline(x, y),
        lambda: sin.interp1d(x, y),
        lambda: sin.PchipInterpolator(x, y),
        lambda: ssg.TransferFunction([1], [1, 1]),
        lambda: ssg.butter(2, 0.3, output="sos"),
        lambda: ssa.KDTree(np.c_[x, y]),
        lambda: ssa.Delaunay(np.c_[x, y]),
        lambda: ssa.ConvexHull(np.c_[x, y]),
        lambda: ssa.transform.Rotation.identity(),
        lambda: ssp.csr_array(np.eye(3)),
        lambda: ssp.coo_array(np.eye(3)),
        lambda: ssp.csc_array(np.eye(3)),
        lambda: ssp.lil_array(np.eye(3)),
        lambda: ssp.dok_array(np.eye(3)),
        lambda: ssp.dia_array(np.eye(3)),
        lambda: ssp.bsr_array(np.eye(4), blocksize=(2, 2)),
        lambda: __import__("scipy.sparse.linalg", fromlist=["splu"]).splu(
            ssp.csc_array(np.eye(3))
        ),
        lambda: __import__("scipy.stats.qmc", fromlist=["Sobol"]).Sobol(2),
    ]
    out = []
    for call in calls:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                out.append(call())
        except Exception:
            pass
    return out


def build_attributes(tree):
    """Decide which attribute names are allowed on ordinary objects.

    Parameters
    ----------
    tree : dict
        Allowed members per namespace, from `build_namespaces`

    Returns
    -------
    allowed : set of str
        Attribute names that are allowed

    excluded : dict
        Maps each excluded name to ``(category, reason, label)``

    guarded_seen : set of str
        GUARDED_METHODS names found on some object

    unknown_signatures : list of str
        Callables whose signature cannot be inspected
    """
    seen = {}  # name -> set(labels)
    excluded = {}  # name -> (category, reason, label)
    guarded_seen = set()
    unknown_signatures = []

    def consider(label, owner, name):
        """Allow or exclude one attribute name, recording it in the enclosing sets.

        Parameters
        ----------
        label : str
            The object's label, kept as an example in the report

        owner : class or instance
            The object the attribute belongs to

        name : str
            The attribute name
        """
        verdict = match_name_rules(name, "attr")
        if name in KEEP_ATTRS:
            verdict = None
        elif verdict is None:
            static = inspect.getattr_static(owner, name, None)
            if isinstance(static, (staticmethod, classmethod)):
                static = static.__func__
            if inspect.isroutine(static):
                params = io_params(static)
                if params:
                    verdict = (
                        IO,
                        f"method `{label}.{name}` has file-like parameter(s) "
                        f"{sorted(params)}",
                    )
                else:
                    verdict = source_verdict(static)
        if name in GUARDED_METHODS:
            guarded_seen.add(name)
            return
        if verdict:
            excluded.setdefault(name, (verdict[0], verdict[1], label))
        else:
            seen.setdefault(name, set()).add(label)

    for label, obj in attribute_universe(tree):
        for name in dir(obj):
            if not name.startswith("_"):
                consider(label, obj, name)
    for result in sample_results():
        label = f"result:{type(result).__name__}"
        for name in dir(result):
            if not name.startswith("_"):
                consider(label, result, name)
    for name in EXTRA_ATTRIBUTES.split():
        seen.setdefault(name, set()).add("result fields (EXTRA_ATTRIBUTES)")

    allowed = {n for n in seen if n not in excluded}
    return allowed, excluded, guarded_seen, unknown_signatures


BLOCK_BEGIN = "# BEGIN GENERATED ALLOW-LISTS"
BLOCK_END = "# END GENERATED ALLOW-LISTS"


def versions_string():
    """The Python, numpy, pandas, and scipy versions of this environment.

    Returns
    -------
    str
        For example ``"Python 3.12.3, numpy 2.4.4, pandas 3.0.2, scipy 1.17.1"``
    """
    return (
        f"Python {sys.version.split()[0]}, numpy {np.__version__}, "
        f"pandas {pd.__version__}, scipy {scipy.__version__}"
    )


def _triple(names, indent):
    """A triple-quoted string of names, one per line.

    Parameters
    ----------
    names : iterable of str
        The names to write, which are sorted in the output

    indent : str
        Indentation of every line

    Returns
    -------
    str
        Source code for the string literal
    """
    body = "\n".join(f"{indent}{name}" for name in sorted(names))
    return f'{indent}"""\n{body}\n{indent}"""'


def render_node(ns, tree, depth):
    """Source code for one namespace's ``_ns(...)`` call, including its submodules.

    Parameters
    ----------
    ns : tuple of str
        The namespace path

    tree : dict
        Allowed members per namespace: path -> ``names`` and ``modules``

    depth : int
        Nesting level, used for indentation

    Returns
    -------
    str
        The source code
    """
    pad = "    " * depth
    node = tree[ns]
    names = _triple(node["names"], pad + "    ")
    children = sorted(node["modules"])
    if not children:
        return f"_ns(\n{names}\n{pad})"
    inner = "\n".join(
        f'{pad}        "{child}": {render_node(ns + (child,), tree, depth + 2)},'
        for child in children
    )
    return f"_ns(\n{names},\n{pad}    {{\n{inner}\n{pad}    }},\n{pad})"


def render_block(tree, attrs, versions):
    """The exact text of the generated block, markers included.

    Parameters
    ----------
    tree : dict
        Allowed members per namespace: path -> ``names`` and ``modules``

    attrs : iterable of str
        Allowed attribute names

    versions : str
        The environment recorded in the block's header

    Returns
    -------
    str
        The block, which is identical for identical inputs
    """
    roots = [ns for ns in NAMESPACES if len(ns) == 1]
    lines = [
        f"{BLOCK_BEGIN} -- written by generate_allowlist.py; do not edit by hand.",
        f"# Generated with {versions}.",
        "# To change a decision, edit the rules in generate_allowlist.py and",
        "# re-run it, then review the diff. allowlist_report.md lists everything",
        "# that was excluded and why. A test fails if this block differs from",
        "# what the generator writes.",
        "# fmt: off",
        "",
        "",
        "def _names(space_separated):",
        '    """Split a string of names into a frozenset.',
        "",
        "    Parameters",
        "    ----------",
        "    space_separated : str",
        "        The names, separated by whitespace",
        "",
        "    Returns",
        "    -------",
        "    frozenset of str",
        '    """',
        "    return frozenset(space_separated.split())",
        "",
        "",
        "def _ns(names, modules=None):",
        '    """One namespace: its members, and its submodules.',
        "",
        "    Parameters",
        "    ----------",
        "    names : str",
        "        The member names, separated by whitespace",
        "",
        "    modules : dict, optional",
        "        Maps each submodule's name to its own namespace",
        "",
        "    Returns",
        "    -------",
        "    dict",
        '        ``{"names": frozenset, "modules": dict}``',
        '    """',
        '    return {"names": _names(names), "modules": modules or {}}',
        "",
        "",
        "# What may be reached through a library name (np.sqrt, sp.stats.zscore, ...).",
        "ALLOWED_MODULE_MEMBERS = {",
    ]
    for ns in roots:
        lines.append(f'    "{ns[0]}": {render_node(ns, tree, 1)},')
    lines += [
        "}",
        "",
        "# Attributes/methods allowed on any other object (Series, ndarray, ...).",
        "ALLOWED_ATTRIBUTES = _names(",
        _triple(attrs, "    "),
        ")",
        "",
        "# Methods that resolve a *string* argument to an attribute. They may only",
        "# be called directly, with a function or an allowed method name.",
        f'GUARDED_METHODS = _names("{" ".join(GUARDED_METHODS)}")',
        "# fmt: on",
        BLOCK_END,
    ]
    return "\n".join(lines)


def extract_block(source):
    """The generated block, markers included, inside the text of operations.py.

    Parameters
    ----------
    source : str
        The text of operations.py

    Returns
    -------
    str
        The block

    Raises
    ------
    ValueError
        When the BEGIN/END markers are missing
    """
    start = source.index(BLOCK_BEGIN)
    end = source.index(BLOCK_END, start) + len(BLOCK_END)
    return source[start:end]


def inject_block(source, block):
    """Replace the generated block in the text of operations.py.

    Parameters
    ----------
    source : str
        The text of operations.py

    block : str
        The new block, markers included

    Returns
    -------
    str
        `source` with its block replaced

    Raises
    ------
    ValueError
        When the BEGIN/END markers are missing from `source`
    """
    old = extract_block(source)
    return source.replace(old, block, 1)


def block_versions(block):
    """The environment recorded in a generated block's header.

    Parameters
    ----------
    block : str
        The generated block

    Returns
    -------
    str or None
        The versions string, or None if the header has none
    """
    match = re.search(r"^# Generated with (.*)\.$", block, re.M)
    return match.group(1) if match else None


def tree_from_frozen(allowed_module_members):
    """Flatten the nested ALLOWED_MODULE_MEMBERS into one entry per namespace.

    Parameters
    ----------
    allowed_module_members : dict
        ALLOWED_MODULE_MEMBERS as defined in operations.py

    Returns
    -------
    dict
        Maps each namespace path to its ``names`` and ``modules``, like
        `build_namespaces`
    """
    tree = {}

    def visit(ns, node):
        """Add a namespace and its submodules to the enclosing `tree`.

        Parameters
        ----------
        ns : tuple of str
            The namespace path

        node : dict
            The namespace's entry in ALLOWED_MODULE_MEMBERS
        """
        tree[ns] = {"names": set(node["names"]), "modules": set(node["modules"])}
        for child, child_node in node["modules"].items():
            visit(ns + (child,), child_node)

    for root, node in allowed_module_members.items():
        visit((root,), node)
    return tree


def render_report(
    tree,
    member_excl,
    attr_excl,
    guarded_seen,
    attrs,
    unknown_sigs,
    parallel,
):
    """The Markdown report of what is allowed and what was excluded, and why.

    Parameters
    ----------
    tree : dict
        Allowed members per namespace: path -> ``names`` and ``modules``

    member_excl : list of tuple
        Excluded library members, ``(category, namespace, name, reason)``

    attr_excl : dict
        Excluded attribute names, mapping to ``(category, reason, label)``

    guarded_seen : set of str
        Guarded methods that were found

    attrs : set of str
        Allowed attribute names

    unknown_sigs : list of str
        Callables whose signature cannot be inspected

    parallel : list of str
        Callables that accept a parallelism argument

    Returns
    -------
    str
        The report
    """
    versions = versions_string()
    guarded_list = ", ".join(sorted(guarded_seen))
    out = [
        "# Allow-list report",
        "",
        f"Generated with {versions}.",
        "",
        "Everything below was decided by the rules in `generate_allowlist.py`.",
        "To overrule a decision, edit `KEEP` (allow a module member), `KEEP_ATTRS`",
        "(allow an attribute name), `EXPLICIT`, or `NAME_RULES` there and re-run",
        "`python generate_allowlist.py`; then review the diff of the generated",
        "block in `operations.py`.",
        "",
    ]
    total = sum(len(n["names"]) for n in tree.values())
    out += [
        "## What is allowed",
        "",
        f"- **{total}** library members across **{len(tree)}** namespaces",
        f"- **{len(attrs)}** attribute/method names for ordinary objects",
        f"- **{len(guarded_seen)}** guarded methods ({guarded_list}): "
        "callable only with a statically known function, never a string",
        "",
        "| namespace | allowed members |",
        "|---|---:|",
    ]
    for ns in NAMESPACES:
        out.append(f"| `{'.'.join(ns)}` | {len(tree[ns]['names'])} |")
    out.append("")

    out += ["## What is excluded, and why", ""]
    by_cat = {}
    for category, ns, name, reason in member_excl:
        by_cat.setdefault(category, []).append((ns, name, reason))
    for name, (category, reason, label) in attr_excl.items():
        by_cat.setdefault(category, []).append(
            (f"(attribute on {label})", name, reason)
        )
    for category in (IO, EVAL, DISPATCH, STATE, NATIVE, ENV, OTHER):
        rows = sorted(by_cat.get(category, []))
        out += [f"### {category}: {CATEGORY_TITLES[category]}  ({len(rows)})", ""]
        grouped = {}
        for ns, name, reason in rows:
            grouped.setdefault(reason, []).append(
                f"{ns}.{name}" if not ns.startswith("(") else f"{name} {ns}"
            )
        for reason, items in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
            out.append(f"- *{reason}* ({len(items)}):")
            out.append(
                textwrap.fill(
                    ", ".join(f"`{i}`" for i in sorted(items)),
                    110,
                    initial_indent="  ",
                    subsequent_indent="  ",
                )
            )
        out.append("")

    if parallel:
        out += [
            "## Allowed callables that accept a parallelism argument",
            "",
            "Not excluded (resource use, not a security boundary), but a",
            "`workers`/`n_jobs` argument can start threads or worker processes:",
            "",
            textwrap.fill(", ".join(f"`{n}`" for n in sorted(parallel)), 110),
            "",
        ]
    if unknown_sigs:
        out += [
            "## Allowed callables whose signature could not be inspected",
            "",
            "These were allowed by name/origin only (no file-like parameter check",
            "was possible).",
            "",
            textwrap.fill(", ".join(f"`{n}`" for n in sorted(set(unknown_sigs))), 110),
            "",
        ]
    return "\n".join(out)


def find_parallel(tree):
    """Allowed library callables that accept a ``workers``-style argument.

    Parameters
    ----------
    tree : dict
        Allowed members per namespace: path -> ``names`` and ``modules``

    Returns
    -------
    list of str
        Dotted names such as ``scipy.optimize.differential_evolution``
    """
    found = []
    for ns, node in tree.items():
        module = resolve_namespace(ns)
        for name in node["names"]:
            obj = getattr(module, name, None)
            if callable(obj) and not isinstance(obj, np.ufunc):
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        params = set(inspect.signature(obj).parameters)
                except (TypeError, ValueError):
                    continue
                if params & {"workers", "n_jobs", "parallel", "num_threads", "threads"}:
                    found.append(".".join(ns) + "." + name)
    return found


def generate():
    """Run the whole pipeline.

    Returns
    -------
    dict
        Everything needed to render or test the lists: ``tree``, ``member_excl``,
        ``attrs``, ``attr_excl``, ``guarded_seen``, ``unknown_sigs``, and ``parallel``
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tree, member_excl, unknown_sigs = build_namespaces()
        attrs, attr_excl, guarded_seen, unknown2 = build_attributes(tree)
        parallel = find_parallel(tree)
    return {
        "tree": tree,
        "member_excl": member_excl,
        "attrs": attrs,
        "attr_excl": attr_excl,
        "guarded_seen": guarded_seen,
        "unknown_sigs": unknown_sigs + unknown2,
        "parallel": parallel,
    }


CHECK_OK, CHECK_DRIFT, CHECK_WRONG_ENV = 0, 1, 2


def normalize_versions(versions):
    """Compare Python by major.minor and the libraries exactly.

    Parameters
    ----------
    versions : str or None
        A versions string, such as the one in a generated block's header

    Returns
    -------
    str
        `versions` without the Python patch number
    """
    return re.sub(r"Python (\d+\.\d+)\.\d+", r"Python \1", versions or "")


def check_block(source, result, versions_now):
    """Compare the generated block with what this environment generates.

    Parameters
    ----------
    source : str
        The text of operations.py

    result : dict or None
        The output of `generate`; not used if the environment differs

    versions_now : str
        The versions of this environment, from `versions_string`

    Returns
    -------
    code : int
        CHECK_OK, CHECK_DRIFT, or CHECK_WRONG_ENV

    message : str
        What to tell the user

    Raises
    ------
    ValueError
        When the BEGIN/END markers are missing from `source`
    """
    block = extract_block(source)
    recorded = block_versions(block)
    if normalize_versions(recorded) != normalize_versions(versions_now):
        return CHECK_WRONG_ENV, (
            "this environment is not the one the allow-lists were generated in, "
            "so they cannot be compared here.\n"
            f"  recorded : {recorded}\n"
            f"  this one : {versions_now}\n"
            "Run the check in the recorded environment, or regenerate in a new one."
        )
    expected = render_block(result["tree"], result["attrs"], recorded)
    if block == expected:
        return CHECK_OK, "the generated block is up to date"
    diff = [
        line
        for line in difflib.unified_diff(
            block.splitlines(),
            expected.splitlines(),
            "operations.py",
            "generated",
            n=0,
            lineterm="",
        )
        if line[:1] in "+-" and line[:3] not in ("+++", "---")
    ]
    shown = "\n".join(f"  {line.strip()}" for line in diff[:40])
    more = f"\n  ... and {len(diff) - 40} more" if len(diff) > 40 else ""
    return CHECK_DRIFT, (
        "the generated block is out of date: this environment generates a "
        "different allow-list. Run `python generate_allowlist.py`, review the diff, "
        "and commit it.\n"
        "Regenerating would add (+) or remove (-):\n" + shown + more
    )


def is_installed_path(path):
    """Whether a path is inside an installed package, not a source checkout.

    Parameters
    ----------
    path : str
        A file path

    Returns
    -------
    bool
        True for a path under ``site-packages`` or ``dist-packages``
    """
    parts = os.path.realpath(path).split(os.sep)
    return "site-packages" in parts or "dist-packages" in parts


def default_target(here):
    """Where operations.py is, relative to the generator.

    Parameters
    ----------
    here : str
        The folder that contains the generator

    Returns
    -------
    str
        The first of ``../operations.py`` and ``../pype_schema/operations.py`` that
        exists
    """
    candidates = [
        os.path.join(here, "..", "operations.py"),
        os.path.join(here, "..", "pype_schema", "operations.py"),
    ]
    return next((c for c in candidates if os.path.isfile(c)), candidates[0])


def main():
    """Rewrite the generated block, or check it with ``--check``.

    Raises
    ------
    SystemExit
        With the ``--check`` result as the exit code, or when asked to rewrite an
        installed copy
    """
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(
        description="Regenerate the allow-lists inside operations.py."
    )
    parser.add_argument(
        "--target",
        default=default_target(here),
        help="module whose generated block is rewritten (needs the BEGIN/END markers)",
    )
    parser.add_argument("--report", default=os.path.join(here, "allowlist_report.md"))
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write anything: exit 0 if the block is up to date, 1 if "
        "regenerating would change it, 2 if this environment is not the one it "
        "was generated in",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="allow rewriting a copy installed in site-packages (normally refused)",
    )
    args = parser.parse_args()
    if args.check:
        with open(args.target) as handle:
            source = handle.read()
        recorded = block_versions(extract_block(source))
        same_env = normalize_versions(recorded) == normalize_versions(versions_string())
        result = generate() if same_env else None  # no point generating in another env
        code, message = check_block(source, result, versions_string())
        print(message)
        sys.exit(code)
    if is_installed_path(args.target) and not args.force:
        sys.exit(
            f"refusing to rewrite {args.target}: it is an installed copy, and the "
            "allow-list should only change through a reviewed commit in a source "
            "checkout. Re-run there, or pass --force if you really mean it."
        )

    result = generate()
    block = render_block(result["tree"], result["attrs"], versions_string())
    with open(args.target) as handle:
        source = handle.read()
    updated = inject_block(source, block)
    with open(args.target, "w") as handle:
        handle.write(updated)
    with open(args.report, "w") as handle:
        handle.write(
            render_report(
                result["tree"],
                result["member_excl"],
                result["attr_excl"],
                result["guarded_seen"],
                result["attrs"],
                result["unknown_sigs"],
                result["parallel"],
            )
        )
    print(
        f"rewrote the generated block in {os.path.normpath(args.target)}"
        f" ({'changed' if updated != source else 'unchanged'})"
    )
    print(f"wrote {os.path.normpath(args.report)}")


if __name__ == "__main__":
    main()
