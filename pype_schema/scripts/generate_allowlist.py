#!/usr/bin/env python3
"""Generate `the generated block in `operations.py`` and ``allowlist_report.md``.

``operations.py`` only lets a custom operation reach functions and attributes
that appear in the allow-lists in its generated block (between the BEGIN/END
GENERATED ALLOW-LISTS markers). This script produces
them by enumerating the public API of the *installed* math, numpy, pandas, and
scipy, and then removing everything that is judged dangerous.

Why generate and freeze, instead of computing the lists when the module is
imported? A newer library version can add functions. If the lists were
computed at import time, a new function with a harmless-looking name would be
allowed automatically. A frozen file keeps the default "deny": new API is
unreachable until someone re-runs this script and reviews the diff.

What "dangerous" means here (see CATEGORY_TITLES). Everything not excluded for
one of these reasons is allowed:

IO        reads or writes files, URLs, the clipboard, databases, or pickles
EVAL      evaluates code or expression strings
DISPATCH  turns a *string* into a function/attribute lookup (``df.agg("sum")``).
          ``apply``/``agg``/``aggregate``/``transform`` are allowed only in a
          guarded form (see operations.py); the rest are excluded
STATE     changes process-wide state (config, global RNG seed, registries,
          mutable module-level containers)
NATIVE    raw memory or native-code interfaces
ENV       reveals the environment (paths, build config, versions, source)
OTHER     not computation on data, or not reviewed (plotting, testing,
          typing, deprecated aliases, internals)

To change a decision, edit KEEP / EXPLICIT / NAME_RULES below and re-run:

    python scripts/generate_allowlist.py [--target pype_schema/operations.py]

then review the diff of the two generated files.
"""

import argparse
import ast
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
    STATE: "Changes process-wide state (config, global RNG seed, registries, mutable globals)",
    NATIVE: "Raw memory or native-code interface",
    ENV: "Reveals the environment (paths, build config, versions, source)",
    OTHER: "Not computation on data, or not reviewed (plotting, testing, typing, deprecated, internals)",
}

# Methods that resolve a *string* argument to an attribute (``x.agg("sum")``).
# They are not in ALLOWED_ATTRIBUTES; operations.py allows them only
# when called directly with a statically known callable (never a string).
GUARDED_METHODS = ("agg", "aggregate", "apply", "transform")

# --------------------------------------------------------------------------
# Namespaces that are enumerated. Everything else (deprecated aliases such as
# scipy.stats.stats, internals, I/O modules, ...) is excluded wholesale.
# --------------------------------------------------------------------------
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

# --------------------------------------------------------------------------
# Decisions
# --------------------------------------------------------------------------
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

# Attribute names that exist on an enumerated library module that was NOT
# allowed as a member (so a module passed around as a value could reach it),
# reviewed and judged harmless. Anything else that collides is dropped from
# ALLOWED_ATTRIBUTES.
COLLISION_OK = {
    "interpolate": "scipy.interpolate.interpolate is a deprecated alias module of numeric functions",
    "stats": "scipy.stats.stats is a deprecated alias module of numeric functions",
    "zeros": "scipy.optimize.zeros is a deprecated alias module of numeric functions",
    "compressed": "scipy.sparse.compressed is a deprecated alias module",
    "extract": "scipy.sparse.extract is a deprecated alias module",
    "rotation": "scipy.spatial.transform.rotation is a deprecated alias module",
    "dtypes": "numpy.dtypes only holds dtype classes",
    "bit_generator": "numpy.random.bit_generator only holds bit-generator base classes",
    "base": "scipy.sparse.base is a deprecated alias module of sparse-matrix classes",
    "data": "scipy.sparse.data is a deprecated alias module of sparse-matrix classes",
    "reduce": "scipy.stats.contingency leaks functools.reduce, which only applies a callable to an iterable",
}

# Explicit exclusions. key: ("dotted.namespace" or "*", "name")
EXPLICIT = {
    # ---- numpy (top level) ----
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
        "contains npyio (file I/O) and stride_tricks.as_strided (unchecked memory views)",
    ),
    ("numpy", "rec"): (IO, "record-array helpers include fromfile"),
    ("numpy", "testing"): (OTHER, "test runners and assertions (some execute code)"),
    ("numpy", "typing"): (OTHER, "typing helpers"),
    # ---- numpy.random ----
    # ---- pandas ----
    ("pandas", "eval"): (EVAL, "evaluates an expression string"),
    ("pandas", "pivot_table"): (DISPATCH, "`aggfunc` string is resolved by name"),
    ("pandas", "crosstab"): (DISPATCH, "`aggfunc` string is resolved by name"),
    ("pandas", "NamedAgg"): (DISPATCH, "`aggfunc` string is resolved by name"),
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
    # ---- scipy ----
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
    # ---- I/O ----
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
        r"to_(csv|excel|json|hdf|sql|parquet|feather|html|latex|markdown|xml|clipboard|stata|orc|gbq|xarray|string|iceberg)",
        IO,
        "writes to a path, buffer, or clipboard, or hands off to an external library",
        "attr",
    ),
    # ---- evaluation ----
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
    # ---- dispatch by name ----
    (
        r"(pivot_table|crosstab|NamedAgg)",
        DISPATCH,
        "`aggfunc` string is resolved by name",
        "both",
    ),
    # ---- process-wide state ----
    (
        r"(set_\w+|reset_\w+|use_\w+|register_\w+|unregister_\w+|add_newdoc\w*|add_docstring|"
        r"seterr|seterrcall|setbufsize|errstate|printoptions|seed|option_context|options|skip_backend)",
        STATE,
        "changes process-wide configuration or state",
        "module",
    ),
    # ---- native / memory ----
    (
        r"(as_strided|byte_bounds|from_dlpack|LowLevelCallable|ctypeslib|get_blas_funcs|get_lapack_funcs|cython_\w+)",
        NATIVE,
        "raw memory or native-code interface",
        "module",
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
    # ---- environment ----
    (
        r"(get_include|info|lookfor|source|who|test|tests|show_config|show_runtime|show_versions|"
        r"get_option|describe_option)",
        ENV,
        "reveals paths, build configuration, versions, or source",
        "module",
    ),
    (r"info", ENV, "prints a summary to stdout or a buffer", "attr"),
    # ---- not computation on data ----
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
        r"subprocess|os\.system|os\.popen|os\.environ|os\.remove|os\.unlink|shutil|tempfile|os\.makedirs|os\.mkdir",
        IO,
        "starts processes or changes the filesystem",
    ),
    (r"urllib|socket|requests|http\.client|ftplib|smtplib", IO, "uses the network"),
    (r"(?<![\w.])open\(|pathlib|Path\(|\.read_text|\.write_text", IO, "opens files"),
    (r"pickle|marshal|shelve", IO, "uses pickle/marshal"),
    (
        r"importlib|__import__|(?<![\w.])(eval|exec)\(|_getframe|currentframe|f_globals|f_locals",
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
    "x fun success status message nit nfev njev nhev jac hess hess_inv maxcv "  # OptimizeResult
    "root converged iterations function_calls flag "  # RootResults
    "t y t_events y_events sol "  # OdeResult
)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
class Deprecated:
    pass


def public_members(module):
    """{name: object | Deprecated()} for the public names of `module`."""
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
    """The module object for a namespace path such as ("numpy", "emath").

    Some public namespaces (numpy.emath) are attributes, not importable module
    paths, so walk attributes first and fall back to importing.
    """
    obj = importlib.import_module(ns[0])
    for i, part in enumerate(ns[1:], start=1):
        try:
            obj = getattr(obj, part)
        except AttributeError:
            obj = importlib.import_module(".".join(ns[: i + 1]))
    return obj


def io_params(obj):
    """Set of I/O-looking parameter names, or None if no signature is available."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            params = set(inspect.signature(obj).parameters)
    except (TypeError, ValueError):
        return None
    return params & IO_PARAMS


def executable_source(obj):
    """Source of a function/method written in Python, with docstrings removed, or None."""
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
    """(category, reason) if the executable source of `obj` does something excluded."""
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
    for pattern, category, reason, rule_scope in NAME_RULES:
        if rule_scope in (scope, "both") and pattern.fullmatch(name):
            return category, reason
    return None


def classify_member(ns, name, obj, unknown_signatures):
    """(category, reason) if `name` in namespace `ns` is excluded, else None."""
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


# --------------------------------------------------------------------------
# module members
# --------------------------------------------------------------------------
def build_namespaces():
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


# --------------------------------------------------------------------------
# attributes of ordinary objects
# --------------------------------------------------------------------------
def attribute_universe(tree):
    """[(label, class-or-instance, use_instance_dir)] of the objects whose
    attributes custom operations may meaningfully touch."""
    items = []

    def add(label, obj, instance_dir=False):
        items.append((label, obj, instance_dir))

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
                continue  # excluded members cannot be reached, so their attributes do not matter
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
    """Instances of result objects returned by functions, so their field names are seen."""
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
    seen = {}  # name -> set(labels)
    excluded = {}  # name -> (category, reason, label)
    guarded_seen = set()
    unknown_signatures = []

    def consider(label, owner, name):
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
                        f"method `{label}.{name}` has file-like parameter(s) {sorted(params)}",
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

    for label, obj, instance_dir in attribute_universe(tree):
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


def _has(module, name):
    try:
        return hasattr(module, name)
    except Exception:  # lazy import of an optional dependency failed
        return True  # be conservative: treat as present


def drop_module_collisions(allowed_attrs, tree):
    """Modules can be passed around as values (`lambda m: m.load`), and then
    ALLOWED_ATTRIBUTES applies to them. Remove any attribute name that is also
    an attribute of an enumerated module but was *not* allowed there."""
    dropped, reviewed = {}, {}
    for ns, node in tree.items():
        module = resolve_namespace(ns)
        reachable = node["names"] | node["modules"]
        for name in sorted(allowed_attrs):
            if name in dropped:
                continue
            if _has(module, name) and name not in reachable:
                if name in COLLISION_OK:
                    reviewed.setdefault(name, []).append(".".join(ns))
                else:
                    dropped[name] = ".".join(ns)
    return allowed_attrs - set(dropped), dropped, reviewed


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------
BLOCK_BEGIN = "# BEGIN GENERATED ALLOW-LISTS"
BLOCK_END = "# END GENERATED ALLOW-LISTS"


def versions_string():
    return (
        f"Python {sys.version.split()[0]}, numpy {np.__version__}, "
        f"pandas {pd.__version__}, scipy {scipy.__version__}"
    )


def _triple(names, indent):
    """A triple-quoted string with one name per line, so that adding or removing
    a name shows up as a single added or removed line in a diff."""
    body = "\n".join(f"{indent}{name}" for name in sorted(names))
    return f'{indent}"""\n{body}\n{indent}"""'


def render_node(ns, tree, depth):
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


def render_block(tree, attrs, reviewed, versions):
    """The exact text of the generated block, markers included. Deterministic:
    the same inputs always give the same text, which is what lets a test tell a
    hand edit from the real thing."""
    roots = [ns for ns in NAMESPACES if len(ns) == 1]
    lines = [
        f"{BLOCK_BEGIN} -- written by generate_allowlist.py; do not edit by hand.",
        f"# Generated with {versions}.",
        "# To change a decision, edit the rules in generate_allowlist.py and re-run it, then",
        "# review the diff. allowlist_report.md lists everything that was excluded and why.",
        "# A test fails if this block differs from what the generator writes.",
        "# fmt: off",
        "",
        "",
        "def _names(space_separated):",
        "    return frozenset(space_separated.split())",
        "",
        "",
        "def _ns(names, modules=None):",
        '    """One namespace: the members reachable as ``lib.name`` and its submodules."""',
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
        "# Attributes/methods allowed on any other object (Series, DataFrame, ndarray, str, ...).",
        "ALLOWED_ATTRIBUTES = _names(",
        _triple(attrs, "    "),
        ")",
        "",
        "# Methods that resolve a *string* argument to an attribute. They may only be called",
        "# directly, with a function or an allowed method name (see the validator above).",
        f'GUARDED_METHODS = _names("{" ".join(GUARDED_METHODS)}")',
        "",
        "# Attribute names in ALLOWED_ATTRIBUTES that are also non-allowed attributes of an",
        "# enumerated library module; reviewed and judged harmless (COLLISION_OK in the",
        "# generator). A test checks that no *other* such collision exists.",
        "REVIEWED_MODULE_COLLISIONS = _names(",
        _triple(reviewed, "    "),
        ")",
        "# fmt: on",
        BLOCK_END,
    ]
    return "\n".join(lines)


def extract_block(source):
    """The generated block (markers included) inside the text of operations.py."""
    start = source.index(BLOCK_BEGIN)
    end = source.index(BLOCK_END, start) + len(BLOCK_END)
    return source[start:end]


def inject_block(source, block):
    old = extract_block(source)
    return source.replace(old, block, 1)


def block_versions(block):
    match = re.search(r"^# Generated with (.*)\.$", block, re.M)
    return match.group(1) if match else None


def tree_from_frozen(allowed_module_members):
    """The nested ALLOWED_MODULE_MEMBERS dict, flattened back to {namespace: ...}."""
    tree = {}

    def visit(ns, node):
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
    dropped,
    reviewed,
    attrs,
    unknown_sigs,
    parallel,
):
    versions = versions_string()
    out = [
        "# Allow-list report",
        "",
        f"Generated with {versions}.",
        "",
        "Everything below was decided by the rules in `generate_allowlist.py`. To overrule a",
        "decision, edit `KEEP` (allow a module member), `KEEP_ATTRS` (allow an attribute name),",
        "`EXPLICIT`, or `NAME_RULES` there and re-run `python generate_allowlist.py`; then review",
        "the diff of the generated block in `operations.py`.",
        "",
    ]
    total = sum(len(n["names"]) for n in tree.values())
    out += [
        "## What is allowed",
        "",
        f"- **{total}** library members across **{len(tree)}** namespaces",
        f"- **{len(attrs)}** attribute/method names for ordinary objects",
        f"- **{len(guarded_seen)}** guarded methods ({', '.join(sorted(guarded_seen))}): "
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

    if dropped:
        out += [
            "## Attribute names dropped because they collide with an excluded module member",
            "",
            "A module can be passed around as a value, so an attribute name that is allowed on",
            "Series/ndarray/... must not also reach an *excluded* member of a library.",
            "",
            textwrap.fill(
                ", ".join(f"`{n}` ({ns})" for n, ns in sorted(dropped.items())), 110
            ),
            "",
        ]
    if reviewed:
        out += [
            "## Attribute names kept despite colliding with a non-allowed module attribute",
            "",
            "Reviewed and judged harmless (reasons in COLLISION_OK in the generator):",
            "",
            textwrap.fill(", ".join(f"`{n}`" for n in sorted(reviewed)), 110),
            "",
        ]
    if parallel:
        out += [
            "## Allowed callables that accept a parallelism argument",
            "",
            "Not excluded (resource use, not a security boundary), but a `workers`/`n_jobs`",
            "argument can start threads or worker processes:",
            "",
            textwrap.fill(", ".join(f"`{n}`" for n in sorted(parallel)), 110),
            "",
        ]
    if unknown_sigs:
        out += [
            "## Allowed callables whose signature could not be inspected",
            "",
            "These were allowed by name/origin only (no file-like parameter check was possible).",
            "",
            textwrap.fill(", ".join(f"`{n}`" for n in sorted(set(unknown_sigs))), 110),
            "",
        ]
    return "\n".join(out)


def find_parallel(tree):
    """Allowed module-level callables with a workers/n_jobs/parallel parameter."""
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
    """Run the whole pipeline; returns everything needed to render or to test."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tree, member_excl, unknown_sigs = build_namespaces()
        attrs, attr_excl, guarded_seen, unknown2 = build_attributes(tree)
        attrs, dropped, reviewed = drop_module_collisions(attrs, tree)
        parallel = find_parallel(tree)
    return {
        "tree": tree,
        "member_excl": member_excl,
        "attrs": attrs,
        "attr_excl": attr_excl,
        "guarded_seen": guarded_seen,
        "dropped": dropped,
        "reviewed": reviewed,
        "unknown_sigs": unknown_sigs + unknown2,
        "parallel": parallel,
    }


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(
        description="Regenerate the allow-lists inside operations.py."
    )
    parser.add_argument(
        "--target",
        default=os.path.join(here, "..", "pype_schema", "operations.py"),
        help="module whose generated block is rewritten (must contain the BEGIN/END markers)",
    )
    parser.add_argument("--report", default=os.path.join(here, "allowlist_report.md"))
    args = parser.parse_args()

    result = generate()
    block = render_block(
        result["tree"], result["attrs"], result["reviewed"], versions_string()
    )
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
                result["dropped"],
                result["reviewed"],
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
