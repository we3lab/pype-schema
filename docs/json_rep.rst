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

Here is the simplest example of this structure, with two nodes, one connection, and no virtual tags:

.. code-block:: json
    
    {
        "nodes": ["PowerGrid", "WWTP"],
        "connections": ["GridToPlant"],
        "virtual_tags": {},
        "PowerGrid": {
            "type": "Network",
            "contents": ["Electricity", "NaturalGas"],
            "tags": {},
            "nodes": [],
            "connections": []
        },
        "WWTP": {
            "input_contents": ["UntreatedSewage", "Electricity"],
            "output_contents": ["TreatedSewage"],
            "tags": {},
            "nodes": [],
            "connections": []
        },
        "GridToPlant": {
            "type": "Wire",
            "source": "PowerGrid",
            "destination": "WWTP",
            "contents": "Electricity",
            "bidirectional": true,
            "tags": {}
        }
    }

For integration with data-driven modeling applications, ``Tag`` objects that represent real-world sensors can
be added to any other object. As a basica example, if there was an electrical meter with a database column name 
"grid_to_plant_kW", then we would add the following tag specification to the connection:

.. code-block:: json

    "GridToPlant": {
        "type": "Wire",
        "source": "PowerGrid",
        "destination": "WWTP",
        "contents": "Electricity",
        "bidirectional": true,
        "tags": {
            "grid_to_plant_kW": {
                "type": "Flow",
                "units": "kWh",
                "contents": "Electricity",
                "totalized": false
            }
        }
    }

One other thing to note about this connection is that "bidirectional" is set to ``true``.
In the real world this means that electricity exports are allowed. PyPES will also take this 
into account (e.g., when querying all connections entering a node, it will return conncections
that leave the node with "bidirectional"=``true``).

Certain types of nodes, like the "WWTP" ``Facility`` and "PowerGrid" ``Network`` objects above, 
can have nodes and connections nested inside them. They take on the same structure as the top level. 
For example we could fill in the wastewater treatment facility with some basic processes:

.. code-block:: json
    
    "WWTP": {
        "nodes": ["ProcessA", "ProcessB", ...],
        "connections": ["AtoB", ...],
        "ProcessA": {
            "type": "Clarification",
            "input_contents": "UntreatedSewage",
            "output_contents": "PrimaryEffluent",

        }
        "ProcessB": {
            
        },
        "AtoB": {
            "type": "Pipe",
            "source": "ProcessA",
            "destination": "ProcessB",
            "contents": "Electricity"
        }
        ...
    }

The following sections will detail how to represent different types of nodes (:ref:`node_rep`), 
connections (:ref:`conn_rep`), and tags (:ref:`tag_rep`) 
so that the meaning of fields such as "type", "num_units", "contents", etc. is clear. 

Putting all the above together, we have the following valid PyPES JSON representation:

.. code-block:: json

    {
        "nodes": ["PowerGrid", "WWTP"],
        "connections": ["GridToPlant"],
        "virtual_tags": {},
        "PowerGrid": {
            "type": "Network",
            "contents": ["Electricity", "NaturalGas"],
            "tags": {},
            "nodes": [],
            "connections": []
        },
        "WWTP": {
            "input_contents": ["UntreatedSewage", "Electricity"],
            "output_contents": ["TreatedSewage"],
            "nodes": ["ProcessA", "ProcessB"],
            "connections": ["AtoB"],
            "ProcessA": {
                "type": "Clarification",
                "input_contents": "UntreatedSewage",
                "output_contents": "PrimaryEffluent",
                "num_units": 4,
                "flowrate": {
                    "min": null,
                    "max": null,
                    "avg": 2,
                    "units": "MGD"
                }
            }
            "ProcessB": {
                "type": "Aeration",
                "contents": ["PrimaryEffluent", "WasteActivatedSludge"],
                "num_units": 8,
                "flowrate": {
                    "min": null,
                    "max": null,
                    "avg": 1.5,
                    "units": "MGD"
                }
            },
            "AtoB": {
                "type": "Pipe",
                "source": "ProcessA",
                "destination": "ProcessB",
                "contents": "Electricity"
            },
            "tags": {}
        },
        "GridToPlant": {
            "type": "Wire",
            "source": "PowerGrid",
            "destination": "WWTP",
            "contents": "Electricity",
            "bidirectional": true,
            "tags": {
                "grid_to_plant_kW": {
                    "type": "Flow",
                    "units": "kWh",
                    "contents": "Electricity",
                    "totalized": false
                }
            }
        }
    }

.. _node_rep:

Representing Nodes
==================

MORE FORMALLY ENUMERATE STRUCTURE (USE THE TABLES FROM GQE!)

.. _conn_rep:

Representing Connections
========================

MORE FORMALLY ENUMERATE STRUCTURE, DEAFAULT VALUES, ETC.

INCLUDE INFORMATION ON ENTRY/EXIT POINTS

.. _tag_rep:

Representing Tags
==================

Both nodes and connections can have tags nested inside them.
These tags represent sensors or data points at the facility.
The JSON format to represent a tag in PyPES is as follows:

.. code-block:: json
    
    TAG EXAMPLE

.. code-block:: json
    
    VIRTUAL TAG EXAMPLE

.. _contents_type:

ContentsType Enum
=================

A fundamental facet of process engineering is the conversion of reactants to products. 
In PyPES, these changes are represented by the ``ContentsType`` enum.
Each node has distinct input and output contents, while a connection is assumed to have a single 
``ContentsType`` since it is simply transporting the contents.

As a shorthand, instead of specifying ``input_contents`` and ``output_contents`` separately,
the user can simply enter ``contents`` and the value will be set to both attributes.
I.e., the below are two ways to represent the same node in JSON format:

.. code-block:: json

    "PowerGrid": {
        "type": "Network",
        "contents": ["Electricity", "NaturalGas"],
        "tags": {},
        "nodes": [],
        "connections": []
    }

.. code-block:: json

    "PowerGrid": {
        "type": "Network",
        "input_contents": ["Electricity", "NaturalGas"],
        "output_contents": ["Electricity", "NaturalGas"],
        "tags": {},
        "nodes": [],
        "connections": []
    }

A full list of supported ``ContentsType`` can be found in the source code (see :ref:`utils`).