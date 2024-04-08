.. contents::

.. _advanced:

*****************
Advanced Features
*****************

Some attributes in PyPES are not static metadata. For example, a pump may have an efficiency curve rather
than a single efficiency value. To define an efficiency 

.. code_block:: python



Currently, only static efficiency values are supported in the JSON format, but the long-term plan is to
support dictionaries (through interpolation) and lambda functions.