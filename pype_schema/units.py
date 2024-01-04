"""Module containing global unit registry.
The `Pint package <https://pint.readthedocs.io/en/latest/>`_ supports arithmetic
of physical quantities, which are combinations of numerical values and units of
measurement. The units of a quantity come from Pint's unit registry. This
module contains a unit registry, named ``u``, based on Pint's unit registry.
It also defines a few additional units.
Frequently Used Units and Constants in ``u``

Prefixes for Metric Units
-------------------------
* pico- =  1e-12 = p-
* nano- =  1e-9  = n-
* micro- = 1e-6  = u- = µ-
* milli- = 1e-3  = m-
* centi- = 1e-2  = c-
* deci- =  1e-1  = d-
* deca- =  1e+1  = da-
* hecto- = 1e2   = h-
* kilo- =  1e3   = k-
* mega- =  1e6   = M-
* giga- =  1e9   = G-
* tera- =  1e12  = T-
Units of Length
---------------
* ``u.meter`` = ``u.metre`` = ``u.m``
* ``u.inch``
* ``u.foot`` = ``u.ft``
* ``u.yard`` = ``u.yd``
* ``u.mile`` = ``u.mi``
Units of Mass
-------------
* ``u.gram`` = ``u.g``
* ``u.metric_ton`` = ``u.tonne`` = ``u.t``
* ``u.ounce`` = ``u.oz``
* ``u.pound`` = ``u.lb``
* ``u.ton``
* ``u.atomic_mass_unit`` = ``u.amu``
Units of Time
-------------
* ``u.second`` = ``u.sec`` = ``u.s``
* ``u.minute`` = ``u.min``
* ``u.hour`` = ``u.hr``
* ``u.day``
* ``u.week``
* ``u.year``
Units of Temperature
--------------------
* ``u.kelvin`` = ``u.degK``
* ``u.celsius`` = ``u.degC``
* ``u.fahrenheit`` = ``u.degF``
Units of Angle
--------------
* ``u.revolution`` = ``u.rev``
* ``u.radian`` = ``u.rad``
* ``u.degree`` = ``u.deg``
Units of Force
--------------
* ``u.newton`` = ``u.N``
* ``u.gram_force`` = ``u.gf``
* ``u.kilogram_force`` = ``u.kgf``
* ``u.pound_force`` = ``u.lbf``
* ``u.ton_force``
* ``u.kip``
Units of Frequency
------------------
* ``u.hertz`` = ``u.Hz``
* ``u.revolutions_per_minute`` = ``u.rpm``
Units of Money
--------------
* ``u.dollar`` = ``u.USD``
* ``u.lempira`` = ``u.HNL``
Units of Power
--------------
* ``u.watt`` = ``u.W``
* ``u.horsepower`` = ``u.hp``
Units of Pressure
-----------------
* ``u.pascal`` = ``u.Pa``
* ``u.bar``
* ``u.atmosphere`` = ``u.atm``
* ``u.torr``
* ``u.millimeter_Hg`` = ``u.mmHg``
Units of Volume
---------------
* ``u.liter`` = ``u.litre`` = ``u.L``
* ``u.cubic_centimeter`` = ``u.cc``
* ``u.gallon`` = ``u.gal``
* ``u.quart`` = ``u.qt``
* ``u.pint`` = ``u.pt``
* ``u.cup``
* ``u.fluid_ounce`` = ``u.floz``
* ``u.tablespoon`` = ``u.tbsp``
* ``u.teaspoon`` = ``tsp``
Other Units
-----------
* ``u.joule`` = ``u.J``
* ``u.mole`` = ``u.mol`` = ``u.equivalent`` = ``u.eq``
* ``u.NTU`` = 1.47 * (``u.mg`` / ``u.L``)
  * This turbidity-concentration relation applies to kaolinite clay and is
    obtained from `Coagulation behavior of polyaluminum chloride (Wei et al.,
    2015) <https://doi.org/10.1016/j.cjche.2015.02.003>`_.
Constants
---------
* ``u.gravity``
* ``u.molar_gas_constant`` = ``u.R``
* ``u.avogadro_number``
* ``u.boltzmann_constant``
"""

import os
import pint

# A global unit registry that can be used by any of other module.
unit_registry = pint.UnitRegistry(system="mks", autoconvert_offset_to_baseunit=True)
u = unit_registry

# default formatting includes 4 significant digits.
# This can be overridden on a per-print basis with
# print('{:.3f}'.format(3 * ureg.m / 9)).
u.default_format = ".4g"

units_path = os.path.join(os.path.dirname(__file__), "data", "unit_definitions.txt")
u.load_definitions(units_path)


def set_sig_figs(n=4):
    """Set the default number of significant figures used to print Pint,
    Pandas and NumPy value quantities.

    Parameters
    ----------
    n : int
        number of significant figures to display. Defaults to 4.
    """
    u.default_format = "." + str(n) + "g"
