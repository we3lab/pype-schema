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
    network = parser.initialize_network()

Model Structure
===============

The :ref:`visualize` module can be used to view the loaded PyPES representation with either of the ``pyvis`` or ``networkx`` packages.

.. code-block:: python
    
    from pype_schema.visualize import draw_graph
    
    pyvis = True
    draw_graph(network, pyvis)

If you run the code above you should produce the following HTML visualization:

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



