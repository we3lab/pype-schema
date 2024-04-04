.. contents::

.. _json_rep:

*******************
JSON Representation
*******************

The PyPES JSON file format is broken into four categories at the top level:

1. String ``Node`` ID list
2. String ``Connection`` ID list
3. String ``VirtualTag`` ID list
4. Key-value entries for each of actual :ref:`node` or :ref:`connection` objects (see :ref:`node_rep` and :ref:`conn_rep`),
   where keys are the string IDs from 1-3

As a simple example:

.. code-block:: python
    
    INSERT EXAMPLE WITH EMPTY CONTENTS


Certain types of nodes, like ``Facility``, can have nodes and connections nested inside them. 
They take on the same structure as the top level. 
For example a wastewater treatment facility inside of the larger water system:

.. code-block:: python

    SKELETONIZE sample.json

.. _node_rep:

Representing Nodes
==================

.. _conn_rep:

Representing Connections
========================

.. _tag_rep:

Representing Tags
==================

Both nodes and connections can have tags nested inside them.
These tags represent sensors or data points at the facility.
The JSON format to represent a tag in PyPES is as follows:

.. code-block:: python
    
    TAG EXAMPLE