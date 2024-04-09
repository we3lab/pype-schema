.. contents::

.. _advanced:

*****************
Advanced Features
*****************

Some attributes in PyPES are not static metadata. For example, a ``Pump`` may have an efficiency curve rather
than a single efficiency value. To define an efficiency curve, first define a function and then use 
``set_pump_curve()`` to set the ``pump_curve`` attribute to that function. ``thermal_efficiency``
and ``electrical_efficiency`` of ``Cogenerator`` and ``Boiler`` objects can be similarly defined.

.. code-block:: python

    from pype_schema.node import Pump
    from utils import parse_quantity, PumpType, ContentsType

    min_flow = parse_quantity(0, "gpm")
    max_flow = parse_quantity(1000, "gpm")
    avg_flow = parse_quantity(750, "gpm")
    elevation = parse_quantity(10, "m")
    horsepower = parse_quantity(100, "hp")

    def efficiency_curve(flowrate):
        return - (flowrate ** 2)

    pump = Pump(
        "PumpA",
        ContentsType.UntreatedSewage,
        ContentsType.UntreatedSewage,
        min_flow,
        max_flow,
        avg_flow,
        elevation,
        horsepower,
        1, 
        pump_type=PumpType.VFD
    )
    pump.set_pump_curve(efficiency_curve)

Currently, only static efficiency values are supported in the JSON format, but the long-term plan is to
support dictionaries (through interpolation) and lambda functions.