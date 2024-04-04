.. contents::

.. _helloworld:

***************
Getting Started
***************

Loading a PyPES Model
=====================

For most users, the first step to using PyPES will be to pip install the Python package:

.. code-block:: python

    pip install pype-schema

This installation should come with a sample facility configuration represented by `sample.json`. 
To load this facility, you can run the following code from the `pype_schema/data` folder:

.. code-block:: python

    from pype_schema.parse_json import JSONParser

    parser = JSONParser("sample.json")
    result = parser.initialize_network()

The :ref:`visualize`

Modifying the Model
===================

The graphical representation of the facility can be modified programmatically. 
This can be useful for modeling upgrades to existing infrastructure by seamlessly comparing two configurations side-by-side.

For example, to add a battery to existing facility:

.. code-block:: python

    # create the battery node

    # add the node to the facility

    # be sure to add required connections

Rather than adding components to the model one-by-one in Python, 
a user can edit the JSON file directly and then re-load the model (see :ref:`json_rep`) 



