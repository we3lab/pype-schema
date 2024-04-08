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
To load this facility, run the following code from the `pype_schema/data` folder:

.. code-block:: python

    from pype_schema.parse_json import JSONParser

    parser = JSONParser("sample.json")
    network = parser.initialize_network()

.. _model_struct:

Model Structure
===============

The :ref:`visualize` module can be used to view the loaded PyPES representation with either of the ``pyvis`` or ``networkx`` packages.

.. code-block:: python
    
    from pype_schema.visualize import draw_graph
    
    pyvis = True
    draw_graph(network, pyvis)

Running the above code should produce the following HTML visualization:

TODO: insert image

PyPES models can have nodes nested within nodes. See :

.. code-block:: python
    
    from pype_schema.visualize import draw_graph
    
    pyvis = True
    node_id = "WWTP"
    draw_graph(network.get_node(node_id), pyvis)

TODO: insert image

Now, let's discuss some of the components of the graph.

Connection
**********

Conceptually, connections are objects in a WRRF that act as a vector to transport contents from a source to a destination. 

In practice, there will be an abstract Python class ``Connection`` with two subclasses: ``Pipe`` and ``Wire``. :ref:`conn_rep` contains tables with 
required attributes (e.g., source, destination) and optional attributes of those classes (e.g., diameter, contents). 
All ``Connection`` objects have a dictionary of tags with the tag IDs as keys and ``Tag`` or ``VirtualTag`` objects as values.

Node
****
Conceptually, nodes are objects that represent a wide variety of entities, from clarifiers, aerators, and filters for treatment to batteries, pumps, and cogenerators for energy modeling.

In practice, there will be an abstract Python class ``Node`` with many subclasses. :ref:`node_rep` contains tables with all the potential node classes (e..g, ``Tank``, ``Filtration``, ``Battery``, etc.), r
equired attributes of those classes (e.g., id, contents), and optional attributes of those classes (e.g., volume, contents). 
All ``Node`` objects have a dictionary of tags with the tag IDs as keys and ``Tag`` or ``VirtualTag`` objects as values.

Tag
***

Conceptually, tags are sensors that collect WRRF data, such as flow rate or temperature. 
They are not a part of the graph like nodes or connections, but are associated with nodes and connections along with other attributes.

Each ``Tag`` object contains attributes related to data being collected, such as the string ID, type of measurement, and units 
(see :ref:`tag_rep` for more details).

.. _mod_model:

Modifying the Model
===================

The graphical representation of the facility can be modified programmatically. 
This can be useful for modeling upgrades to existing infrastructure by seamlessly comparing two configurations side-by-side.

For example, to add a 10,000 gallon storage tank at 1,000 meters elevation to the water distribution network:

.. code-block:: python

    from pype_schema.node import Tank
    from pype_schema.utils import parse_quantity, ContentsType

    volume = utils.parse_quantity(10000, "gal")
    elevation = utils.parse_quantity(1000, "m")

    # create the battery node
    tank = Tank("StorageTank", ContentsType.DrinkingWater, ContentsType.DrinkingWater, elevation, volume)

    # add the node to the facility
    wds = network.get_node("WaterDistribution")
    wds.add_node(tank)

Now that there is a node inside the water distribution network, the connection can be modified to have an 
``entry_point``. The ``entry_point`` and ``exit_point`` attributes allow 

Rather than adding components to the model one-by-one in Python, 
a user can edit the JSON file directly and then re-load the model (see :ref:`json_rep`) 

.. _query_model:

Querying the Model
==================

PyPES offers built-in search capabilities that allow users to find nodes, connections, and tags
matching desired characteristics.

Modeling applications can be generalized through the use of these queries. For example, to calculate the 
natural gas purchases at a facility without knowing how many boilers or cogenerators (if any) exist, a user
could query for all connections with ``ContentsType`` are ``NaturalGas`` entering the ``WWTP`` node:

.. code-block:: python

    from pype_schema.connection import Connection

    ng_conns = network.select_objs(
        dest_id="WWTP",
        contents_type=contents_type.NaturalGas,
        obj_type=Connection,
        recurse=True
    )

Its often more convenient to get all the tags directly. Then, if the data is in CSV format the tags correspond to
column names that can be operated on:

.. code_block:: python

    from pype_schema.tag import Tag
    import pandas as pd

    pd.read_csv()

    ng_tags = network.select_objs(
        dest_id="WWTP",
        contents_type=contents_type.NaturalGas,
        obj_type=Tag,
        recurse=True
    )

Unit IDs are used to specify identical parallel processes. 
For example, a cogenerator may have two engines. 
Therefore, ``dest_unit_id`` was specified as `"total"` because there may be unit-level tags, 
and summing both unit-level and total tags would lead to overcounting.

There are a number of optional arguments to ``select_objs``, most of which default to ``None``. The function is 
fully documented in :ref:`node`.