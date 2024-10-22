import warnings
from abc import ABC
from . import utils
from .tag import Tag, VirtualTag
from collections import defaultdict

EFFICIENCY_ATTRS = ["thermal_efficiency", "electrical_efficiency", "rte"]

CAPACITY_ATTRS = [
    "volume",
    "energy_capacity",
    "discharge_rate",
    "charge_rate",
    "min_flow",
    "max_flow",
    "design_flow",
    "min_gen",
    "max_gen",
    "design_gen",
    "power_rating",
]


class Node(ABC):
    """Abstract class for all nodes

    Attributes
    ----------
    id : str
        Node ID

    input_contents : list of ContentsType
        Contents entering the node.

    output_contents : list of ContentsType
        Contents leaving the node.

    tags : dict of Tag
        Data tags associated with this node
    """

    id: str = NotImplemented
    input_contents: list[utils.ContentsType] = NotImplemented
    output_contents: list[utils.ContentsType] = NotImplemented
    tags: dict = NotImplemented

    def __repr__(self):
        return (
            f"<pype_schema.node.Node id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} "
            f"tags:{self.tags}>\n"
        )

    def set_dosing(self, dose_rate, mode="rate"):
        """Set the dosing rate of the node

        Parameters
        ----------
        dose_rate : dict of str:float
            Dosing rate of the chemical in the node

        mode : str
            whether or not the dosing is defined as a volumetric 'rate' or by 'area'
        """
        if mode not in ["rate", "area"]:
            raise ValueError(
                "Dosing mode must be either 'rate' or 'area' not '" + mode + "'"
            )

        dosing_dict = defaultdict(float)

        for k, v in dose_rate.items():
            if isinstance(k, utils.DosingType):
                dosing_dict[k] = v
            else:
                if k not in utils.DosingType.__members__:
                    raise ValueError(f"{k} is not a valid dosing type")
                dosing_dict[utils.DosingType[k]] = v

        if mode == "rate":
            self._dosing_rate = dosing_dict
        elif mode == "area":
            self._dosing_area = dosing_dict

    def set_flow_rate(self, min, max, design):
        """Set the minimum, maximum, and design flow rate of the node

        Parameters
        ----------
        min : int
            Minimum flow rate through the node

        max : int
            Maximum flow rate through the node

        design : int
            Design flow rate through the node
        """
        warnings.warn(
            "Please switch from `flow_rate` tuple to separate "
            + "`min_flow`, `max_flow` and `design_flow` attributes",
            DeprecationWarning,
        )
        self.flow_rate = (min, max, design)
        self._min_flow = min
        self._max_flow = max
        self._design_flow = design

    def get_min_flow(self):
        try:
            return self._min_flow
        except AttributeError:
            warnings.warn(
                "Please switch from `flow_rate` tuple to new `min_flow` attribute",
                DeprecationWarning,
            )
            return self.flow_rate[0]

    def set_min_flow(self, min_flow):
        self._min_flow = min_flow

    def del_min_flow(self):
        del self._min_flow
        if hasattr(self, "flow_rate"):
            self.flow_rate = (None, self.flow_rate[1], self.flow_rate[2])

    def get_max_flow(self):
        try:
            return self._max_flow
        except AttributeError:
            warnings.warn(
                "Please switch from `flow_rate` tuple to new `max_flow` attribute",
                DeprecationWarning,
            )
            return self.flow_rate[1]

    def set_max_flow(self, max_flow):
        self._max_flow = max_flow

    def del_max_flow(self):
        del self._max_flow
        if hasattr(self, "flow_rate"):
            self.flow_rate = (self.flow_rate[0], None, self.flow_rate[2])

    def get_design_flow(self):
        try:
            return self._design_flow
        except AttributeError:
            warnings.warn(
                "Please switch from `flow_rate` tuple to new `design_flow` attribute",
                DeprecationWarning,
            )
            return self.flow_rate[2]

    def set_design_flow(self, design_flow):
        self._design_flow = design_flow

    def del_design_flow(self):
        del self._design_flow
        if hasattr(self, "flow_rate"):
            self.flow_rate = (self.flow_rate[0], self.flow_rate[1], None)

    min_flow = property(get_min_flow, set_min_flow, del_min_flow)
    max_flow = property(get_max_flow, set_max_flow, del_max_flow)
    design_flow = property(get_design_flow, set_design_flow, del_design_flow)

    def set_contents(self, contents, attribute="input_contents"):
        """Set the input or output contents of a node

        Parameters
        ----------
        contents : ContentsType or list of ContentsType
            Single value or list of ContentsType entering/exiting the node.

        attribute : ["input_contents", "output_contents"]
            Attribute to set (either `input_contents` or `output_contents`)
        """
        if isinstance(contents, utils.ContentsType):
            setattr(self, attribute, [contents])
        elif isinstance(contents, list) or contents is None:
            setattr(self, attribute, contents)
        else:
            raise TypeError(
                "'contents' must be either ContentsType or list of ContentsType"
            )

    def get_efficiencies(self):
        """Gets a dictionary of efficiency-related attributes

        Returns
        -------
        dict
            Dictionary of attribute names and values
        """
        result = {}
        for attr in EFFICIENCY_ATTRS:
            try:
                result[attr] = getattr(self, attr)
            except AttributeError:
                pass
        return result

    def get_capacities(self):
        """Gets a dictionary of capacity-related attributes

        Returns
        -------
        dict
            Dictionary of attribute names and values
        """
        result = {}
        for attr in CAPACITY_ATTRS:
            try:
                result[attr] = getattr(self, attr)
            except AttributeError:
                pass
        return result

    def add_tag(self, tag):
        """Adds a tag to the node

        Parameters
        ----------
        tag : Tag
            Tag object to add to the node
        """
        if not tag.parent_id:
            tag.parent_id = self.id
        self.tags[tag.id] = tag

    def remove_tag(self, tag_name):
        """Removes a tag from the node

        Parameters
        ----------
        tag_name : str
            name of tag to remove
        """
        del self.tags[tag_name]

    def get_tag(self, tag_name, recurse=False):
        """Gets the Tag object associated with `tag_name`

        Parameters
        ----------
        tag_name : str

        recurse : bool
            Whether or not to get tags recursively.
            Default is False, meaning that only tags involving direct children
            (and this Node itself) will be returned.

        Returns
        ------
        Tag or VirtualTag
            pype_schema Tag object associated with the variable name.
            Returns None if the `tag_name` is not found
        """
        tag = None
        if tag_name in self.tags.keys():
            tag = self.tags[tag_name]
        else:
            if hasattr(self, "connections"):
                for connection in self.connections.values():
                    if tag_name in connection.tags.keys():
                        tag = connection.tags[tag_name]
            if hasattr(self, "nodes") and tag is None:
                for node in self.nodes.values():
                    if recurse:
                        tag = node.get_tag(tag_name, recurse=True)
                    elif tag_name in node.tags.keys():
                        tag = node.tags[tag_name]
                    if tag:
                        break

        return tag

    def get_all_tags(self, virtual=True, recurse=False):
        """Gets all Tag objects associated with this Node

        Parameters
        ----------
        virtual : bool
            Whether to include VirtualTag objects or just regular Tag.
            True by default.

        recurse : bool
            Whether or not to get tags recursively.
            Default is False, meaning that only tags involving direct children
            (and this Node itself) will be returned.

        Returns
        ------
        list of Tag and VirtualTag
            Tag objects inside this Node.
            If `recurse` is True, all children, grandchildren, etc. are returned.
            If False, only direct children are returned.
        """
        tags = list(self.tags.values())

        if hasattr(self, "connections"):
            for connection in self.connections.values():
                tags = tags + list(connection.tags.values())

        if hasattr(self, "nodes"):
            for node in self.nodes.values():
                tags = tags + list(node.tags.values())
                if recurse:
                    tags = tags + node.get_all_tags(recurse=recurse)

        # remove duplicates from grabbing top level and next level
        tags = list(set(tags))

        if not virtual:
            tags = [tag for tag in tags if isinstance(tag, Tag)]

        return tags

    def get_node(self, node_name, recurse=False):
        """Get a node from the network

        Parameters
        ----------
        node_name : str
            name of node to retrieve

        recurse : bool
            Whether or not to get nodes recursively.
            Default is False, meaning that only direct children will be returned.

        Returns
        -------
        Node or None
            Node object if node is found. None otherwise
        """
        result = None
        if hasattr(self, "nodes"):
            try:
                return self.nodes[node_name]
            except KeyError:
                if recurse:
                    for node in self.nodes.values():
                        result = node.get_node(node_name, recurse=True)
                        if result:
                            break

        return result

    def get_all_nodes(self, recurse=False):
        """Gets all Node objects associated with this Node

        Parameters
        ----------
        recurse : bool
            Whether or not to get nodes recursively.
            Default is False, meaning that only direct children will be returned.

        Returns
        ------
        list of Node
            Node objects inside this Node.
            If `recurse` is True, all children, grandchildren, etc. are returned.
            If False, only direct children are returned.
        """
        nodes = []
        if hasattr(self, "nodes"):
            nodes = list(self.nodes.values())
            if recurse:
                for node in self.nodes.values():
                    nodes = nodes + node.get_all_nodes(recurse=True)

        return nodes

    def get_connection(self, connection_name, recurse=False):
        """Get a connection from the network

        Parameters
        ----------
        connection_name : str
            name of connection to retrieve

        recurse : bool
            Whether or not to get connections recursively.
            Default is False, meaning that only direct children will be returned.

        Returns
        -------
        Connection or None
            Connection object if node is found. None otherwise
        """
        result = None
        if hasattr(self, "connections"):
            try:
                return self.connections[connection_name]
            except KeyError:
                if recurse:
                    for node in self.nodes.values():
                        result = node.get_connection(connection_name, recurse=True)
                        if result:
                            break

        return result

    def get_all_connections(self, recurse=False):
        """Gets all Connection objects associated with this Node

        Parameters
        ----------
        recurse : bool
            Whether or not to get connections recursively.
            Default is False, meaning that only direct children will be returned.

        Returns
        ------
        list of Connection
            Connection objects inside this Node.
            If `recurse` is True, all children, grandchildren, etc. are returned.
            If False, only direct children are returned.
        """
        connections = []
        if hasattr(self, "connections"):
            connections = list(self.connections.values())

        if recurse:
            if hasattr(self, "nodes"):
                for node in self.nodes.values():
                    connections = connections + node.get_all_connections(recurse=True)
        return connections

    def get_all_connections_to(self, node):
        """Gets all connections entering the specified Node, including those
        from a different level of the hierarchy with `entry_point` specified.

        Paremeters
        ----------
        node : Node
            pype_schema `Node` object for which we want to get connections

        Returns
        -------
        list of Connection
            List of `Connection` objects entering the specified `node`
        """
        if node is None:
            return []

        connections = self.get_all_connections(recurse=True)
        return [
            connection
            for connection in connections
            if connection.destination == node or connection.entry_point == node
        ]

    def get_all_connections_from(self, node):
        """Gets all connections leaving the specified Node, including those
        from a different level of the hierarchy with `exit_point` specified.

        Paremeters
        ----------
        node : Node
            pype_schema `Node` object for which we want to get connections

        Returns
        -------
        list of Connection
            List of `Connection` objects leaving the specified `node`
        """
        if node is None:
            return []

        connections = self.get_all_connections(recurse=True)
        return [
            connection
            for connection in connections
            if connection.source == node or connection.exit_point == node
        ]

    def get_node_or_connection(self, obj_id, recurse=False):
        """Gets the `Node` or `Connection` object with name `obj_id`

        Parameters
        ----------
        obj_id : str
            name of the object to query

        recurse : bool
            Whether or not to get connections or nodes recursively.
            Default is False, meaning that only direct children will be returned.

        Returns
        -------
        Node or Connection
            object with the name `obj_id`
        """
        obj = self.get_node(obj_id, recurse=recurse)
        if obj is None:
            obj = self.get_connection(obj_id, recurse=recurse)

        return obj

    def get_parent_from_tag(self, tag):
        """Gets the parent object of a `Tag` object, as long as both the tag and its
        parent object are children of `self`

        Parameters
        ----------
        tag : Tag or VirtualTag
            object for which we want the parent object

        Returns
        -------
        Node or Connection
            parent object of the Tag
        """
        if isinstance(tag, VirtualTag) and tag.parent_id is None:
            if tag.id in self.tags.keys():
                return self
            else:
                children = self.get_all_connections(recurse=True) + self.get_all_nodes(
                    recurse=True
                )
                for child in children:
                    if tag.id in child.tags.keys():
                        return child
        else:
            parent_obj = self.get_node_or_connection(tag.parent_id, recurse=True)

        return parent_obj

    def get_parent(self, child_obj):
        """Gets the parent object of a `Tag`, `Connection`, or `Node` object,
        as long as both `child_obj` and its parent object are children of `self`

        Parameters
        ----------
        child_obj : `Tag`, `VirtualTag`, `Connection`, or `Node`
            object for which we want the parent object

        Returns
        -------
        Node or Connection
            parent object of `child_obj`
        """
        if isinstance(child_obj, (Tag, VirtualTag)):
            return self.get_parent_from_tag(child_obj)
        elif (
            child_obj.id in self.connections.keys() or child_obj.id in self.nodes.keys()
        ):
            return self
        else:
            children = self.get_all_nodes(recurse=True)
            for child in children:
                if (
                    child_obj.id in child.connections.keys()
                    or child_obj.id in child.nodes.keys()
                ):
                    return child

    def select_tags(
        self,
        tag,
        source_id=None,
        dest_id=None,
        source_unit_id=None,
        dest_unit_id=None,
        exit_point_id=None,
        entry_point_id=None,
        source_node_type=None,
        dest_node_type=None,
        exit_point_type=None,
        entry_point_type=None,
        tag_type=None,
        recurse=False,
        virtual=False,
    ):
        """Helper function for selecting `Tag` objects from inside a `Node`.

        Parameters
        ----------
        tag : Tag
            Tag object to check against the search criteria

        source_id : str
            Optional id of the source node to filter by. None by default

        dest_id : str
            Optional id of the destination node to filter by. None by default

        source_unit_id : int, str
            Optional unit id of the source to filter by. None by default

        dest_unit_id : int, str
            Optional unit id of the destination to filter by. None by default

        exit_point_id : str
            Optional id of the `exit_point` node to filter by. None by default

        entry_point_id : str
            Optional id of the `entry_point` node to filter by. None by default

        source_node_type : class
            Optional source `Node` subclass to filter by. None by default

        dest_node_type : class
            Optional destination `Node` subclass to filter by. None by default

        exit_point_type : class
            Optional `exit_point` `Node` subclass to filter by. None by default

        entry_point_type : class
            Optional `entry_point` `Node` subclass to filter by. None by default

        tag_type : TagType
            Optional tag type to filter by. None by default

        recurse : bool
            Whether to search for objects within nodes. False by default

        virtual : bool
            True if `tag` is being queried as part of a `VirtualTag`. False by default

        Returns
        -------
        bool
            True if `tag` meets the filtering criteria
        """
        if tag.parent_id == self.id:
            parent_obj = self
        else:
            parent_obj = self.get_node_or_connection(tag.parent_id, recurse=True)
        bidirectional = False

        if isinstance(parent_obj, Node):
            obj_source_node = parent_obj
            obj_source_unit_id = tag.source_unit_id
            (
                obj_dest_unit_id,
                obj_dest_node,
                obj_entry_point,
                obj_exit_point,
            ) = (None, None, None, None)
        elif (
            parent_obj is not None
        ):  # the parent must be a Connection if it is not a Node
            obj_source_node = parent_obj.get_source_node()
            obj_source_unit_id = tag.source_unit_id
            obj_dest_node = parent_obj.get_dest_node()
            obj_dest_unit_id = tag.dest_unit_id
            obj_exit_point = parent_obj.get_exit_point()
            obj_entry_point = parent_obj.get_entry_point()

            if parent_obj.bidirectional:
                bidirectional = True
        # If the parent is None, then it's parent object is outside the network
        # and we can't filter by source/destination/entry/exit-point node and node type
        else:
            obj_source_node = None
            obj_source_unit_id = tag.source_unit_id
            obj_dest_node = None
            obj_dest_unit_id = tag.dest_unit_id
            obj_exit_point = None
            obj_entry_point = None

        if virtual:
            obj_source_unit_id = None
            obj_dest_unit_id = None

        if utils.select_objs_helper(
            tag,
            obj_source_node=obj_source_node,
            obj_dest_node=obj_dest_node,
            obj_source_unit_id=obj_source_unit_id,
            obj_dest_unit_id=obj_dest_unit_id,
            obj_exit_point=obj_exit_point,
            obj_entry_point=obj_entry_point,
            source_id=source_id,
            dest_id=dest_id,
            source_unit_id=source_unit_id,
            dest_unit_id=dest_unit_id,
            exit_point_id=exit_point_id,
            entry_point_id=entry_point_id,
            source_node_type=source_node_type,
            dest_node_type=dest_node_type,
            exit_point_type=exit_point_type,
            entry_point_type=entry_point_type,
            tag_type=tag_type,
            recurse=recurse,
        ):
            return True
        if bidirectional:
            return utils.select_objs_helper(
                tag,
                obj_source_node=obj_dest_node,
                obj_dest_node=obj_source_node,
                obj_source_unit_id=obj_dest_unit_id,
                obj_dest_unit_id=obj_source_unit_id,
                obj_exit_point=obj_entry_point,
                obj_entry_point=obj_exit_point,
                source_id=source_id,
                dest_id=dest_id,
                source_unit_id=source_unit_id,
                dest_unit_id=dest_unit_id,
                exit_point_id=exit_point_id,
                entry_point_id=entry_point_id,
                source_node_type=source_node_type,
                dest_node_type=dest_node_type,
                exit_point_type=exit_point_type,
                entry_point_type=entry_point_type,
                tag_type=tag_type,
                recurse=recurse,
            )
        else:
            return False

    def select_virtual_tags(
        self,
        virtual_tag,
        source_id=None,
        dest_id=None,
        source_unit_id=None,
        dest_unit_id=None,
        exit_point_id=None,
        entry_point_id=None,
        source_node_type=None,
        dest_node_type=None,
        exit_point_type=None,
        entry_point_type=None,
        tag_type=None,
        recurse=False,
    ):
        """Helper function for selecting `VirtualTag` objects from inside a `Node`.

        Parameters
        ----------
        virtual_tag : VirtualTag
            VirtualTag object to check against the search criteria

        source_id : str
            Optional id of the source node to filter by. None by default

        dest_id : str
            Optional id of the destination node to filter by. None by default

        source_unit_id : int, str
            Optional unit id of the source to filter by. None by default

        dest_unit_id : int, str
            Optional unit id of the destination to filter by. None by default

        exit_point_id : str
            Optional id of the `exit_point` node to filter by. None by default

        entry_point_id : str
            Optional id of the `entry_point` node to filter by. None by default

        source_node_type : class
            Optional source `Node` subclass to filter by. None by default

        dest_node_type : class
            Optional destination `Node` subclass to filter by. None by default

        exit_point_type : class
            Optional `exit_point` `Node` subclass to filter by. None by default

        entry_point_type : class
            Optional `entry_point` `Node` subclass to filter by. None by default

        contents_type : ContentsType
            Optional contents to filter by. None by default

        tag_type : TagType
            Optional tag type to filter by. None by default

        recurse : bool
            Whether to search for objects within nodes. False by default

        Returns
        -------
        bool
            True if `virtual_tag` meets the filtering criteria
        """
        if tag_type is None or virtual_tag.tag_type == tag_type:
            for subtag in virtual_tag.tags:
                if isinstance(subtag, VirtualTag):
                    if self.select_virtual_tags(
                        subtag,
                        source_id=source_id,
                        dest_id=dest_id,
                        source_unit_id=source_unit_id,
                        dest_unit_id=dest_unit_id,
                        exit_point_id=exit_point_id,
                        entry_point_id=entry_point_id,
                        source_node_type=source_node_type,
                        dest_node_type=dest_node_type,
                        exit_point_type=exit_point_type,
                        entry_point_type=entry_point_type,
                        tag_type=None,
                        recurse=recurse,
                    ):
                        return True
                else:
                    if self.select_tags(
                        subtag,
                        source_id=source_id,
                        dest_id=dest_id,
                        source_unit_id=source_unit_id,
                        dest_unit_id=dest_unit_id,
                        exit_point_id=exit_point_id,
                        entry_point_id=entry_point_id,
                        source_node_type=source_node_type,
                        dest_node_type=dest_node_type,
                        exit_point_type=exit_point_type,
                        entry_point_type=entry_point_type,
                        tag_type=None,
                        recurse=recurse,
                        virtual=True,
                    ):
                        return True

        return False

    def select_objs(
        self,
        source_id=None,
        dest_id=None,
        source_unit_id=None,
        dest_unit_id=None,
        exit_point_id=None,
        entry_point_id=None,
        source_node_type=None,
        dest_node_type=None,
        exit_point_type=None,
        entry_point_type=None,
        contents_type=None,
        tag_type=None,
        obj_type=None,
        recurse=False,
    ):
        """Selects from this Node all Node, Connection, or Tag objects
        which match source/destination node class, unit ID, and contents.
        (If none given, returns all objects in `self`)

        Parameters
        ----------
        source_id : str
            Optional id of the source node to filter by. None by default

        dest_id : str
            Optional id of the destination node to filter by. None by default

        source_unit_id : int, str
            Optional unit id of the source to filter by. None by default

        dest_unit_id : int, str
            Optional unit id of the destination to filter by. None by default

        exit_point_id : str
            Optional id of the `exit_point` node to filter by. None by default

        entry_point_id : str
            Optional id of the `entry_point` node to filter by. None by default

        source_node_type : class
            Optional source `Node` subclass to filter by. None by default

        dest_node_type : class
            Optional destination `Node` subclass to filter by. None by default

        exit_point_type : class
            Optional `exit_point` `Node` subclass to filter by. None by default

        entry_point_type : class
            Optional `entry_point` `Node` subclass to filter by. None by default

        contents_type : ContentsType
            Optional contents to filter by. None by default

        tag_type : TagType
            Optional tag type to filter by. None by default

        obj_type : [Node, Connection, VirtualTag, Tag]
            The type of object to filter by. None by default

        recurse : bool
            Whether to search for objects within nodes. False by default

        Raises
        ------
        ValueError
            When a source/destination node type is provided to subset tags

        TypeError
            When the objects to select among are not of
            type {`pype_schema.Tag`, `pype_schema.Connection`, `pype_schema.Node`}

        Returns
        -------
        list
            List of `Tag`, `Connection`, or `Node` objects subset according to
            source/destination `id` and `contents_type`
        """
        selected_objs = []
        # Select according to source/destination node type/id
        for tag in self.get_all_tags(virtual=True, recurse=recurse):
            if isinstance(tag, VirtualTag):
                if self.select_virtual_tags(
                    tag,
                    source_id=source_id,
                    dest_id=dest_id,
                    source_unit_id=source_unit_id,
                    dest_unit_id=dest_unit_id,
                    exit_point_id=exit_point_id,
                    entry_point_id=entry_point_id,
                    source_node_type=source_node_type,
                    dest_node_type=dest_node_type,
                    exit_point_type=exit_point_type,
                    entry_point_type=entry_point_type,
                    tag_type=tag_type,
                    recurse=recurse,
                ):
                    selected_objs.append(tag)
            else:
                if self.select_tags(
                    tag,
                    source_id=source_id,
                    dest_id=dest_id,
                    source_unit_id=source_unit_id,
                    dest_unit_id=dest_unit_id,
                    exit_point_id=exit_point_id,
                    entry_point_id=entry_point_id,
                    source_node_type=source_node_type,
                    dest_node_type=dest_node_type,
                    exit_point_type=exit_point_type,
                    entry_point_type=entry_point_type,
                    tag_type=tag_type,
                    recurse=recurse,
                ):
                    selected_objs.append(tag)
        for conn in self.get_all_connections(recurse=recurse):
            if utils.select_objs_helper(
                conn,
                obj_source_node=conn.get_source_node(),
                obj_dest_node=conn.get_dest_node(),
                obj_exit_point=conn.get_exit_point(),
                obj_entry_point=conn.get_entry_point(),
                source_id=source_id,
                dest_id=dest_id,
                source_unit_id=source_unit_id,
                dest_unit_id=dest_unit_id,
                exit_point_id=exit_point_id,
                entry_point_id=entry_point_id,
                source_node_type=source_node_type,
                dest_node_type=dest_node_type,
                exit_point_type=exit_point_type,
                entry_point_type=entry_point_type,
                tag_type=tag_type,
                recurse=recurse,
            ):
                selected_objs.append(conn)
            if conn.bidirectional:
                if utils.select_objs_helper(
                    conn,
                    obj_source_node=conn.get_dest_node(),
                    obj_dest_node=conn.get_source_node(),
                    obj_exit_point=conn.get_entry_point(),
                    obj_entry_point=conn.get_exit_point(),
                    source_id=source_id,
                    dest_id=dest_id,
                    source_unit_id=source_unit_id,
                    dest_unit_id=dest_unit_id,
                    exit_point_id=exit_point_id,
                    entry_point_id=entry_point_id,
                    source_node_type=source_node_type,
                    dest_node_type=dest_node_type,
                    exit_point_type=exit_point_type,
                    entry_point_type=entry_point_type,
                    tag_type=tag_type,
                    recurse=recurse,
                ):
                    selected_objs.append(conn)
        for node in self.get_all_nodes(recurse=recurse):
            if utils.select_objs_helper(
                node,
                obj_source_node=node,
                source_id=source_id,
                dest_id=dest_id,
                source_unit_id=source_unit_id,
                dest_unit_id=dest_unit_id,
                exit_point_id=exit_point_id,
                entry_point_id=entry_point_id,
                source_node_type=source_node_type,
                dest_node_type=dest_node_type,
                exit_point_type=exit_point_type,
                entry_point_type=entry_point_type,
                tag_type=tag_type,
                recurse=recurse,
            ):
                selected_objs.append(node)

        # Select according to contents
        if contents_type is not None:
            selected_objs = [
                obj
                for obj in selected_objs
                if hasattr(obj, "contents") and obj.contents == contents_type
            ]

        # Select according to obj_type
        if obj_type is not None:
            selected_objs = [obj for obj in selected_objs if isinstance(obj, obj_type)]

        return selected_objs


class Network(Node):
    """A water utility represented as a set of connections and nodes

    Parameters
    ----------
    id : str
        Network ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the network.

    output_contents : ContentsType or list of ContentsType
        Contents leaving the network.

    tags : dict of Tag
        Data tags associated with this network

    nodes : dict of Node
        nodes in the network, e.g. pumps, tanks, or facilities

    connections : dict of Connections
        connections in the network, e.g. pipes

    num_units: int, default 1
        Number of units in the network

    Attributes
    ----------
    id : str
        Network ID

    input_contents : list of ContentsType
        Contents entering the network.

    output_contents : list of ContentsType
        Contents leaving the network.

    tags : dict of Tag
        Data tags associated with this network

    nodes : dict of Node
        nodes in the network, e.g. pumps, tanks, or facilities

    connections : dict of Connections
        connections in the network, e.g. pipes

    num_units : int
        Number of networks running in parallel
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        tags={},
        nodes={},
        connections={},
        num_units=1,
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.tags = tags
        self.nodes = nodes
        self.connections = connections
        self.num_units = num_units

    def __repr__(self):
        return (
            f"<pype_schema.node.Network id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} tags:{self.tags} "
            f"nodes:{self.nodes} connections:{self.connections}>\n"
            f"num_units:{self.num_units}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.tags == other.tags
            and self.nodes == other.nodes
            and self.connections == other.connections
            and self.num_units == other.num_units
        )

    def add_node(self, node):
        """Adds a node to the network

        Parameters
        ----------
        node : Node
            Node object to add to the network
        """
        self.nodes[node.id] = node

    def remove_node(self, node_name, recurse=False):
        """Removes a node from the network

        Parameters
        ----------
        node_name : str
            name of node to remove

        recurse : bool
            Whether or not to removed nodes recursively.
            Default is False, meaning that only direct children will be removed.

        Raises
        ------
        KeyError
            if `node_name` is not found
        """
        try:
            del self.nodes[node_name]
        except KeyError:
            if recurse:
                for node in self.nodes.values():
                    try:
                        node.remove_node(node_name, recurse=True)
                        return
                    except (AttributeError, KeyError):
                        continue
            raise KeyError("Node " + node_name + " not found in network")

    def add_connection(self, connection):
        """Adds a connection to the network

        Parameters
        ----------
        connection : Connection
            Connection object to add to the network
        """
        self.connections[connection.id] = connection

    def remove_connection(self, connection_name, recurse=False):
        """Removes a connection from the network
        Parameters
        ----------
        connection_name : str
            name of connection to remove

        recurse : bool


        Raises
        ------
        KeyError
            if `connection_name` is not found
        """
        try:
            del self.connections[connection_name]
        except KeyError:
            if recurse:
                for node in self.nodes.values():
                    try:
                        node.remove_connection(connection_name, recurse=True)
                        return
                    except (AttributeError, KeyError):
                        continue
            raise KeyError("Connection " + connection_name + " not found in network")

    def get_list_of_type(self, desired_type, recurse=False):
        """Searches the Facility and returns a list of all objects of `desired_type`

        Parameters
        ----------
        desired_type : Node or Connection subclass

        recurse : bool
            Whether or not to get objects recursively.
            Default is False, meaning that only direct children will be returned.

        Returns
        ------
        list of `desired_type`
            Objects of `desired_type` inside this Facility.
            If `recurse` is True, all children, grandchildren, etc. are returned.
            If False, only direct children are returned.
        """
        desired_objs = []
        if issubclass(desired_type, Node):
            objs = self.get_all_nodes(recurse=recurse)
        else:
            objs = self.get_all_connections(recurse=recurse)

        for obj in objs:
            if isinstance(obj, desired_type):
                desired_objs.append(obj)

        return desired_objs


class Facility(Network):
    """A class representing any industrial facility
    from wastewater treatment to desalination to solid waste management.

    Parameters
    ----------
    id : str
        Facility ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the network.

    output_contents : ContentsType or list of ContentsType
        Contents leaving the network.

    elevation : pint.Quantity or int
        Elevation of the facility

    min_flow : pint.Quantity or int
        Minimum flow rate through the facility

    max_flow : pint.Quantity or int
        Maximum flow rate through the facility

    design_flow : pint.Quantity or int
        Design flow rate through the facility

    tags : dict of Tag
        Data tags associated with this facility

    nodes : dict of Node
        nodes in the facility, e.g. pumps, tanks, or processes

    connections : dict of Connections
        connections in the facility, e.g. pipes

    Attributes
    ----------
    id : str
        Facility ID

    input_contents : list of ContentsType
        Contents entering the facility.

    output_contents : list of ContentsType
        Contents leaving the facility.

    elevation : pint.Quantity or int
        Elevation of the facility in meters above sea level

    tags : dict of Tag
        Data tags associated with this facility

    min_flow : pint.Quantity or int
        Minimum flow rate through the facility

    max_flow : pint.Quantity or int
        Maximum flow rate through the facility

    design_flow : pint.Quantity or int
        Design flow rate through the facility

    nodes : dict of Node
        nodes in the facility, e.g. pumps, tanks, or processes

    connections : dict of Connections
        connections in the facility, e.g. pipes
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        elevation,
        min_flow,
        max_flow,
        design_flow,
        tags={},
        nodes={},
        connections={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.elevation = elevation
        self.min_flow = min_flow
        self.max_flow = max_flow
        self.design_flow = design_flow
        self.nodes = nodes
        self.connections = connections
        self.tags = tags

    def __repr__(self):
        return (
            f"<pype_schema.node.Facility id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} elevation:{self.elevation} "
            f"min_flow:{self.min_flow} max_flow:{self.max_flow} "
            f"design_flow:{self.design_flow} tags:{self.tags} "
            f"nodes:{self.nodes} connections:{self.connections}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.elevation == other.elevation
            and self.nodes == other.nodes
            and self.connections == other.connections
            and self.tags == other.tags
            and self.min_flow == other.min_flow
            and self.max_flow == other.max_flow
            and self.design_flow == other.design_flow
        )


class Joint(Node):
    """A joint in the network, where multiple pipes meet.

    Parameters
    ----------
    id : str
        Joint ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the joint

    output_contents : ContentsType or list of ContentsType
        Contents leaving the joint

    inflow: Connection or list of Connection
        Connection object of list of connection objects that is the input of the joint

    outflow: Connection or list of Connection
        Connection object of list of connection objects that is the output of the joint

    tags : dict of Tag
        Data tags associated with this joint

    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        inflow=None,
        outflow=None,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.inflow = inflow
        self.outflow = outflow
        self.tags = tags
        # TODO: Add check for inflow and outflow to be of type Connection

    def __repr__(self):
        return (
            f"<pype_schema.node.Joint id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} "
            f"inflow:{self.inflow} "
            f"outflow:{self.outflow} "
            f"tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.inflow == other.inflow
            and self.outflow == other.outflow
            and self.tags == other.tags
        )


class Reducer(Joint):
    """A reducer in the network, where multiple pipes meet.

    Parameters
    ----------
    id : str
        Reducer ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the reducer

    output_contents : ContentsType or list of ContentsType
        Contents leaving the reducer

    inflow: Connection or list of Connection
        Connection object of list of connection objects that is
        the input of the reducer

    outflow: Connection or list of Connection
        Connection object of list of connection objects that is
        the output of the reducer

    tags : dict of Tag
        Data tags associated with this reducer

    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        inflow,
        outflow,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.inflow = inflow
        self.outflow = outflow
        self.tags = tags

    def __repr__(self):
        return (
            f"<pype_schema.node.Reducer id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} "
            f"inflow:{self.inflow} "
            f"outflow:{self.outflow} "
            f"tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.inflow == other.inflow
            and self.outflow == other.outflow
            and self.tags == other.tags
        )


class Splitter(Joint):
    """A splitter in the network, where a pipe splits into multiple pipes.

    Parameters
    ----------
    id : str
        Splitter ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the splitter

    output_contents : ContentsType or list of ContentsType
        Contents leaving the splitter

    inflow: Connection or list of Connection
        Connection object of list of connection objects that
        is the input of the splitter

    outflow: Connection or list of Connection
        Connection object of list of connection objects that
        is the output of the splitter

    tags : dict of Tag
        Data tags associated with this splitter

    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        inflow,
        outflow,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.inflow = inflow
        self.outflow = outflow
        self.tags = tags

    def __repr__(self):
        return (
            f"<pype_schema.node.Splitter id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} "
            f"inflow:{self.inflow} "
            f"outflow:{self.outflow} "
            f"tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.inflow == other.inflow
            and self.outflow == other.outflow
            and self.tags == other.tags
        )


class ModularUnit(Network):
    """Modular Unit in the network, such as a reverse osmosis skid.

    Parameters
    ----------
    id : str
        ModularUnit ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the ModularUnit.

    output_contents : ContentsType or list of ContentsType
        Contents leaving the ModularUnit.

    tags : dict of Tag
        Data tags associated with this ModularUnit

    nodes : dict of Node
        nodes in the ModularUnit, e.g. pumps, tanks, or filters

    connections : dict of Connections
        connections in the ModularUnit, e.g. pipes

    num_units: int
         Number of units running in parallel

    Attributes
    ----------
    id : str
        ModularUnit ID

    input_contents : list of ContentsType
        Contents entering the ModularUnit.

    output_contents : list of ContentsType
        Contents leaving the ModularUnit.

    tags : dict of Tag
        Data tags associated with this ModularUnit

    nodes : dict of Node
        nodes in the ModularUnit, e.g. pumps, tanks, or filters

    num_units: int
        Number of units running in parallel

    connections : dict of Connections
        connections in the ModularUnit, e.g. pipes
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        num_units,
        tags={},
        nodes={},
        connections={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.tags = tags
        self.nodes = nodes
        self.connections = connections
        self.num_units = num_units

    def __repr__(self):
        return (
            f"<pype_schema.node.Network id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} tags:{self.tags} "
            f"nodes:{self.nodes} connections:{self.connections}>\n"
            f"num_units:{self.num_units}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.tags == other.tags
            and self.nodes == other.nodes
            and self.connections == other.connections
        )


class Pump(Node):
    """Any kind of pump, such as constant speed, variable frequency drive (VFD),
    energy recovery device (ERD), and air blower.


    Parameters
    ----------
    id : str
        Pump ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the pump

    output_contents : ContentsType or list of ContentsType
        Contents leaving the pump

    elevation : pint.Quantity or int
        Elevation of the pump in meters above sea level

    power_rating : pint.Quantity or int
        Rated power of a single pump (in horsepower)

    num_units : int
        Number of pumps running in parallel

    min_flow : pint.Quantity or int
        Minimum flow rate supplied by the pump

    max_flow : pint.Quantity or int
        Maximum flow rate supplied by the pump

    design_flow : pint.Quantity or int
        Design flow rate supplied by the pump

    pump_type : PumpType
        Type of pump (either VFD, ERD, AirBlower or Constant)

    efficiency : float
        efficiency of the pump

    tags : dict of Tag
        Data tags associated with this pump

    Attributes
    ----------
    id : str
        Pump ID

    input_contents : list of ContentsType
        Contents entering the pump

    output_contents : list of ContentsType
        Contents leaving the pump

    elevation : pint.Quantity or int
        Elevation of the pump in meters above sea level

    power_rating : pint.Quantity or int
        Rated power of a single pump (in horsepower)

    num_units : int
        Number of pumps running in parallel

    min_flow : pint.Quantity or int
        Minimum flow rate supplied by the pump

    max_flow : pint.Quantity or int
        Maximum flow rate supplied by the pump

    design_flow : pint.Quantity or int
        Design flow rate supplied by the pump

    pump_type : PumpType
        Type of pump (either VFD, ERD, AirBlower or Constant)

    tags : dict of Tag
        Data tags associated with this pump

    pump_curve : function
        Function which takes in the current flow rate and returns the energy
        required to pump at that rate
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        elevation,
        min_flow,
        max_flow,
        design_flow,
        power_rating,
        num_units,
        pump_type=utils.PumpType.Constant,
        efficiency=None,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.elevation = elevation
        self.pump_type = pump_type
        self.power_rating = power_rating
        self.num_units = num_units
        self.efficiency = efficiency
        self.tags = tags
        self.min_flow = min_flow
        self.max_flow = max_flow
        self.design_flow = design_flow
        self.set_pump_curve(self.get_efficiency)

    def __repr__(self):
        return (
            f"<pype_schema.node.Pump id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} "
            f"min_flow:{self.min_flow} max_flow:{self.max_flow} "
            f"design_flow:{self.design_flow} elevation:{self.elevation} "
            f"power_rating:{self.power_rating} num_units:{self.num_units} "
            f"pump_type:{self.pump_type} efficiency:{self.efficiency}"
            f"tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        # TODO: add a way to compare pump_curve since it is a function
        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.elevation == other.elevation
            and self.pump_type == other.pump_type
            and self.power_rating == other.power_rating
            and self.num_units == other.num_units
            and self.tags == other.tags
            and self.min_flow == other.min_flow
            and self.max_flow == other.max_flow
            and self.design_flow == other.design_flow
            and self.efficiency == other.efficiency
        )

    def set_pump_curve(self, pump_curve):
        """Set the pump curve to the given function

        Parameters
        ----------
        pump_curve : function
            function which takes in the current flow rate and returns the energy
            required to pump at that rate
        """
        # TODO: type check that pump_curve is a function
        self.pump_curve = pump_curve

    def get_efficiency(self):
        try:
            return self._efficiency
        except AttributeError:
            warnings.warn("Please add `efficiency` attribute", DeprecationWarning)
            return None

    def set_efficiency(self, efficiency):
        self._efficiency = efficiency

    def del_efficiency(self):
        del self._efficiency

    def get_power_rating(self):
        try:
            return self._power_rating
        except AttributeError:
            warnings.warn(
                "Please switch from `horsepower` to new `power_rating` attribute",
                DeprecationWarning,
            )
            return self.horsepower

    def set_power_rating(self, power_rating):
        self._power_rating = power_rating

    def del_power_rating(self):
        del self._power_rating
        if hasattr(self, "horsepower"):
            warnings.warn(
                "Please switch from `horsepower` to new `power_rating` attribute",
                DeprecationWarning,
            )
            del self.horsepower

    efficiency = property(get_efficiency, set_efficiency, del_efficiency)
    power_rating = property(get_power_rating, set_power_rating, del_power_rating)


class Tank(Node):
    """A generic class to represent a storage tank.
    Any `input_contents` and `output_contents` can be provided
    and metadata such as `volume` and `elevation` can be specified.

    Parameters
    ----------
    id : str
        Tank ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the tank

    output_contents : ContentsType or list of ContentsType
        Contents leaving the tank

    elevation : pint.Quantity or int
        Elevation of the tank in meters above sea level

    volume : pint.Quantity or int
        Volume of the tank in cubic meters

    num_units : int
        Number of identical tanks in parallel

    tags : dict of Tag
        Data tags associated with this tank

    Attributes
    ----------
    id : str
        Tank ID

    input_contents : list of ContentsType
        Contents entering the tank.

    output_contents : list of ContentsType
        Contents leaving the tank.

    elevation : pint.Quantity or int
        Elevation of the tank in meters above sea level

    volume : pint.Quantity or int
        Volume of the tank in cubic meters

    num_units : int
        Number of identical tanks in parallel

    tags : dict of Tag
        Data tags associated with this tank
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        elevation,
        volume,
        num_units=1,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.elevation = elevation
        self.volume = volume
        self.num_units = num_units
        self.tags = tags

    def __repr__(self):
        return (
            f"<pype_schema.node.Tank id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} elevation:{self.elevation} "
            f"num_units:{self.num_units} "
            f"volume:{self.volume} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.elevation == other.elevation
            and self.volume == other.volume
            and self.num_units == other.num_units
            and self.tags == other.tags
        )

    def get_num_units(self):
        try:
            return self._num_units
        except AttributeError:
            warnings.warn(
                "Please add `num_units` attribute to `Tank`",
                DeprecationWarning,
            )
            return 1

    def set_num_units(self, num_units):
        self._num_units = num_units

    def del_num_units(self):
        del self._num_units

    num_units = property(get_num_units, set_num_units, del_num_units)


class Reactor(Node):
    """A reactor modeled as a basic tank with chemical dosing point(s).

    Parameters
    ----------
    id : str
        Reactor ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the reactor

    output_contents : ContentsType or list of ContentsType
        Contents leaving the reactor

    min_flow : pint.Quantity or int
        Minimum flow rate through the reactor

    max_flow : pint.Quantity or int
        Maximum flow rate through the reactor

    design_flow : pint.Quantity or int
        Design flow rate through the reactor

    num_units : int
        Number of reactor in parallel

    volume : pint.Quantity or int
        Volume of the reactor in cubic meters

    residence_time : pint.Quantity or float
        Residence time of the reactor

    dosing_rate : dict of DosingType:float
        Dosing information for the reactor (key: DosingType, value: rate)

    pH : float
        pH value for the reactor

    tags : dict of Tag
        Data tags associated with this reactor

    Attributes
    ----------
    id : str
        Reactor ID

    input_contents : list of ContentsType
        Contents entering the reactor

    output_contents : list of ContentsType
        Contents leaving the reactor

    min_flow : pint.Quantity or int
        Minimum flow rate through the reactor

    max_flow : pint.Quantity or int
        Maximum flow rate through the reactor

    design_flow : pint.Quantity or int
        Design flow rate through the reactor

    num_units : int
        Number of reactors

    volume : pint.Quantity or int
        Volume of the reactor in cubic meters

    residence_time : pint.Quantity or float
        Residence time of the reactor

    dosing_rate : dict of DosingType:float
        Dosing information for the reactor (key: DosingType, value: rate)

    pH : float
        pH value for the reactor

    num_units : int
        Number of reactors in parallel

    tags : dict of Tag
        Data tags associated with this reactor

    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        design_flow,
        num_units,
        volume,
        residence_time,
        dosing_rate={},
        pH=None,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.min_flow = min_flow
        self.max_flow = max_flow
        self.design_flow = design_flow
        self.num_units = num_units
        self.volume = volume
        self.set_dosing_rate(dosing_rate)
        self.pH = pH
        self.residence_time = residence_time
        self.tags = tags

    def __repr__(self):
        return (
            f"<pype_schema.node.Reactor id:{self.id} "
            f"input_contents:{self.input_contents} num_units:{self.num_units}"
            f"output_contents:{self.output_contents} "
            f"dosing_rate:{self.dosing_rate} pH:{self.pH} "
            f"residence_time:{self.residence_time} "
            f"volume:{self.volume} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.volume == other.volume
            and self.num_units == other.num_units
            and self.dosing_rate == other.dosing_rate
            and self.pH == other.pH
            and self.residence_time == other.residence_time
            and self.tags == other.tags
        )

    def get_dosing_rate(self):
        return self._dosing_rate

    def set_dosing_rate(self, dosing_rate):
        self.set_dosing(dosing_rate, mode="rate")

    def del_dosing_rate(self):
        del self._dosing_rate

    dosing_rate = property(get_dosing_rate, set_dosing_rate, del_dosing_rate)


class StaticMixer(Reactor):
    """A tank containing a static mixer,
    typically used for coagulation in water treatment.

    Parameters
    ----------
    id : str
        StaticMixer ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the mixer

    output_contents : ContentsType or list of ContentsType
        Contents leaving the mixer

    min_flow : pint.Quantity or int
        Minimum flow rate through the mixer

    max_flow : pint.Quantity or int
        Maximum flow rate through the mixer

    design_flow : pint.Quantity or int
        Design flow rate through the mixer

    num_units : int
        Number of mixers in parallel

    volume : pint.Quantity or int
        Volume of the mixer in cubic meters

    residence_time : pint.Quantity or float
        Residence time of the mixer

    dosing_rate : dict of DosingType:float
        Dosing information for the mixer (key: DosingType, value: rate)

    pH : float
        pH value for the mixer

    tags : dict of Tag
        Data tags associated with this mixer

    Attributes
    ----------
    id : str
        StaticMixer ID

    input_contents : list of ContentsType
        Contents entering the mixer

    output_contents : list of ContentsType
        Contents leaving the mixer

    min_flow : pint.Quantity or int
        Minimum flow rate through the mixer

    max_flow : pint.Quantity or int
        Maximum flow rate through the mixer

    design_flow : pint.Quantity or int
        Design flow rate through the mixer

    num_units : int
        Number of mixers in parallel

    volume : pint.Quantity or int
        Volume of the mixer in cubic meters

    residence_time : pint.Quantity or float
        Residence time of the mixer

    dosing_rate : dict of DosingType:float
        Dosing information for the mixer (key: DosingType, value: rate)

    pH : float
        pH value for the mixer

    tags : dict of Tag
        Data tags associated with this mixer

    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        design_flow,
        num_units,
        volume,
        residence_time,
        dosing_rate={},
        pH=None,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.min_flow = min_flow
        self.max_flow = max_flow
        self.design_flow = design_flow
        self.num_units = num_units
        self.volume = volume
        self.set_dosing_rate(dosing_rate)
        self.pH = pH
        self.residence_time = residence_time
        self.tags = tags

    def __repr__(self):
        return (
            f"<pype_schema.node.StaticMixer id:{self.id} "
            f"input_contents:{self.input_contents} num_units:{self.num_units}"
            f"output_contents:{self.output_contents} "
            f"dosing_rate:{self.dosing_rate} pH:{self.pH} "
            f"residence_time:{self.residence_time} "
            f"volume:{self.volume} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.volume == other.volume
            and self.num_units == other.num_units
            and self.dosing_rate == other.dosing_rate
            and self.pH == other.pH
            and self.residence_time == other.residence_time
            and self.tags == other.tags
        )


class Reservoir(Node):
    """A generic reservoir used to represent lakes and oceans in addition
    to manmade bodies of water.

    Parameters
    ----------
    id : str
        Reservoir ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the reservoir.

    output_contents : ContentsType or list of ContentsType
        Contents leaving the reservoir.

    elevation : pint.Quantity or int
        Elevation of the reservoir in meters above sea level

    volume : pint.Quantity or int
        Volume of the reservoir in cubic meters

    tags : dict of Tag
        Data tags associated with this reservoir

    Attributes
    ----------
    id : str
        Reservoir ID

    input_contents : list of ContentsType
        Contents entering the reservoir.

    output_contents : list of ContentsType
        Contents leaving the reservoir.

    elevation : pint.Quantity or int
        Elevation of the reservoir in meters above sea level

    volume : pint.Quantity or int
        Volume of the reservoir in cubic meters

    tags : dict of Tag
        Data tags associated with this reservoir
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        elevation,
        volume,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.elevation = elevation
        self.volume = volume
        self.tags = tags

    def __repr__(self):
        return (
            f"<pype_schema.node.Reservoir id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} elevation:{self.elevation} "
            f"volume:{self.volume} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.elevation == other.elevation
            and self.volume == other.volume
            and self.tags == other.tags
        )


class Battery(Node):
    """A generic battery with metadata such as roundtrip efficiency (RTE),
    energy capacity, and charge/discharge rates.

    Parameters
    ----------
    id : str
        Battery ID

    energy_capacity : int
        Energy storage capacity of the battery in kWh

    charge_rate : int
        Maximum charge rate of the battery in kW

    discharge_rate : int
        Maximum discharge rate of the battery in kW

    rte : float
        Round trip efficiency of the battery

    tags : dict of Tag
        Data tags associated with this battery

    Attributes
    ----------
    id : str
        Battery ID

    input_contents : list of ContentsType
        Contents entering the battery.

    output_contents : list of ContentsType
        Contents leaving the battery.

    energy_capacity : int
        Energy storage capacity of the battery in kWh

    charge_rate : int
        Maximum discharge rate of the battery in kW

    discharge_rate : int
        Maximum discharge rate of the battery in kW

    rte : float
        Round trip efficiency of the battery

    leakage : pint.Quantity
        Leakage of the battery as a Pint Quantity

    tags : dict of Tag
        Data tags associated with this battery
    """

    def __init__(
        self,
        id,
        energy_capacity,
        charge_rate,
        discharge_rate,
        rte,
        leakage,
        tags={},
    ):
        self.id = id
        self.input_contents = [utils.ContentsType.Electricity]
        self.output_contents = [utils.ContentsType.Electricity]
        self.energy_capacity = energy_capacity
        self.charge_rate = charge_rate
        self.discharge_rate = discharge_rate
        self.rte = rte
        self.leakage = leakage
        self.tags = tags

    def __repr__(self):
        return (
            f"<pype_schema.node.Battery id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} "
            f"energy_capacity:{self.energy_capacity} "
            f"charge_rate:{self.charge_rate} discharge_rate:{self.discharge_rate}"
            f"rte:{self.rte} leakage:{self.leakage} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.energy_capacity == other.energy_capacity
            and self.charge_rate == other.charge_rate
            and self.discharge_rate == other.discharge_rate
            and self.rte == other.rte
            and self.leakage == other.leakage
            and self.tags == other.tags
        )

    def get_rte(self):
        try:
            return self._rte
        except AttributeError:
            return None

    def set_rte(self, rte):
        self._rte = rte

    def del_rte(self):
        del self._rte

    def get_leakage(self):
        try:
            return self._leakage
        except AttributeError:
            return None

    def set_leakage(self, leakage):
        self._leakage = leakage

    def del_leakage(self):
        del self._leakage

    def get_energy_capacity(self):
        try:
            return self._energy_capacity
        except AttributeError:
            warnings.warn(
                "Please switch from `capacity` to new `energy_capacity` attribute",
                DeprecationWarning,
            )
            return self.capacity

    def set_energy_capacity(self, energy_capacity):
        self._energy_capacity = energy_capacity

    def del_energy_capacity(self):
        del self._energy_capacity
        if hasattr(self, "capacity"):
            warnings.warn(
                "Please switch from `capacity` to new `energy_capacity` attribute",
                DeprecationWarning,
            )
            del self.capacity

    def get_charge_rate(self):
        try:
            return self._charge_rate
        except AttributeError:
            warnings.warn(
                "Please add `charge_rate` in addition to `discharge_rate` attribute",
                DeprecationWarning,
            )
            return self.discharge_rate

    def set_charge_rate(self, charge_rate):
        self._charge_rate = charge_rate

    def del_charge_rate(self):
        del self._charge_rate

    leakage = property(get_leakage, set_leakage, del_leakage)
    rte = property(get_rte, set_rte, del_rte)
    charge_rate = property(get_charge_rate, set_charge_rate, del_charge_rate)
    energy_capacity = property(
        get_energy_capacity, set_energy_capacity, del_energy_capacity
    )


class Digestion(Node):
    """A class representing a sludge digester, either aerobic or anaerobic.

    Parameters
    ----------
    id : str
        Digester ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the digester (e.g. biogas or wastewater)

    output_contents : ContentsType or list of ContentsType
        Contents leaving the digester (e.g. biogas or wastewater)

    min_flow : pint.Quantity or int
        Minimum flow rate through the digester

    max_flow : pint.Quantity or int
        Maximum flow rate through the digester

    design_flow : pint.Quantity or int
        Design flow rate through the digester

    num_units : int
        Number of digesters running in parallel

    volume : pint.Quantity or int
        Volume of the digester in cubic meters

    digester_type : DigesterType
        Type of digestion (aerobic or anaerobic)

    tags : dict of Tag
        Data tags associated with this digester

    Attributes
    ----------
    id : str
        Digester ID

    input_contents : list of ContentsType
        Contents entering the digester (e.g. biogas or wastewater)

    output_contents : list of ContentsType
        Contents leaving the digester (e.g. biogas or wastewater)

    num_units : int
        Number of digesters running in parallel

    volume : pint.Quantity or int
        Volume of the digester in cubic meters

    min_flow : pint.Quantity or int
        Minimum flow rate through the digester

    max_flow : pint.Quantity or int
        Maximum flow rate through the digester

    design_flow : pint.Quantity or int
        Design flow rate through the digester

    digester_type : DigesterType
        Type of digestion (aerobic or anaerobic)

    tags : dict of Tag
        Data tags associated with this digester
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        design_flow,
        num_units,
        volume,
        digester_type,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.num_units = num_units
        self.volume = volume
        self.digester_type = digester_type
        self.tags = tags
        self.min_flow = min_flow
        self.max_flow = max_flow
        self.design_flow = design_flow

    def __repr__(self):
        return (
            f"<pype_schema.node.Digestion id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"volume:{self.volume} min_flow:{self.min_flow} "
            f"max_flow:{self.max_flow} design_flow:{self.design_flow} "
            f"digester_type:{self.digester_type} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.volume == other.volume
            and self.digester_type == other.digester_type
            and self.min_flow == other.min_flow
            and self.max_flow == other.max_flow
            and self.design_flow == other.design_flow
            and self.tags == other.tags
        )


class Cogeneration(Node):
    """A class representing a cogeneration engine that produces
    both heat and electricity through biogas and/or natural gas combustion.

    Parameters
    ----------
    id : str
        Cogenerator ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the cogenerator

    min_gen : int
        Minimum generation capacity of a single cogenerator

    max_gen : int
        Maximum generation capacity of a single cogenerator

    design_gen : int
        Design generation capacity of a single cogenerator

    num_units : int
        Number of cogenerator units running in parallel

    tags : dict of Tag
        Data tags associated with this cogenerator

    Attributes
    ----------
    id : str
        Cogenerator ID

    input_contents : list of ContentsType
        Contents entering the cogenerator
        (biogas, natural gas, or a blend of the two)

    output_contents : list of ContentsType
        Contents leaving the cogenerator (Electricity)

    min_gen : int
        Minimum generation capacity of a single cogenerator

    max_gen : int
        Maximum generation capacity of a single cogenerator

    design_gen : int
        Average generation capacity of a single cogenerator

    num_units : int
        Number of cogenerator units running in parallel

    tags : dict of Tag
        Data tags associated with this cogenerator

    electrical_efficiency : function
        Function which takes in the current kWh and returns
        the electrical efficiency as a fraction

    thermal_efficiency : function
        Function which takes in the current kWh and returns
        the thermal efficiency as a fraction
    """

    def __init__(
        self, id, input_contents, min_gen, max_gen, design_gen, num_units, tags={}
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.output_contents = [utils.ContentsType.Electricity, utils.ContentsType.Heat]
        self.num_units = num_units
        self.tags = tags
        self.min_gen = min_gen
        self.max_gen = max_gen
        self.design_gen = design_gen
        self.set_electrical_efficiency(None)
        self.set_thermal_efficiency(None)

    def __repr__(self):
        return (
            f"<pype_schema.node.Cogeneration id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} min_gen:{self.min_gen} "
            f"max_gen:{self.max_gen} design_gen:{self.design_gen} "
            f"num_units:{self.num_units} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.min_gen == other.min_gen
            and self.max_gen == other.max_gen
            and self.design_gen == other.design_gen
            and self.tags == other.tags
        )

    def set_gen_capacity(self, min, max, design):
        """Set the minimum, maximum, and average generation capacity

        Parameters
        ----------
        min : int
            Minimum generation by a single cogenerator

        max : int
            Maximum generation by a single cogenerator

        design : int
            Design generation by a single cogenerator
        """
        warnings.warn(
            "Please switch from `gen_capacity` tuple to new separate "
            + "`min_gen`, `max_gen` and `design_gen` attributes",
            DeprecationWarning,
        )
        self.gen_capacity = (min, max, design)
        self._min_gen = min
        self._max_gen = max
        self._design_gen = design

    def get_min_gen(self):
        try:
            return self._min_gen
        except AttributeError:
            warnings.warn(
                "Please switch from `gen_capacity` tuple to new `min_gen` attribute",
                DeprecationWarning,
            )
            return self.gen_capacity[0]

    def set_min_gen(self, min_gen):
        self._min_gen = min_gen

    def del_min_gen(self):
        del self._min_gen
        if hasattr(self, "gen_capacity"):
            self.gen_capacity = (None, self.gen_capacity[1], self.gen_capacity[2])

    def get_max_gen(self):
        try:
            return self._max_gen
        except AttributeError:
            warnings.warn(
                "Please switch from `gen_capacity` tuple to new `max_gen` attribute",
                DeprecationWarning,
            )
            return self.gen_capacity[1]

    def set_max_gen(self, max_gen):
        self._max_gen = max_gen

    def del_max_gen(self):
        del self._max_gen
        if hasattr(self, "gen_capacity"):
            self.gen_capacity = (self.gen_capacity[0], None, self.gen_capacity[2])

    def get_design_gen(self):
        try:
            return self._design_gen
        except AttributeError:
            warnings.warn(
                "Please switch from `gen_capacity` tuple to new `design_gen` attribute",
                DeprecationWarning,
            )
            return self.gen_capacity[2]

    def set_design_gen(self, design_gen):
        self._design_gen = design_gen

    def del_design_gen(self):
        del self._design_gen
        if hasattr(self, "gen_capacity"):
            self.gen_capacity = (self.gen_capacity[0], self.gen_capacity[1], None)

    min_gen = property(get_min_gen, set_min_gen, del_min_gen)
    max_gen = property(get_max_gen, set_max_gen, del_max_gen)
    design_gen = property(get_design_gen, set_design_gen, del_design_gen)

    def set_electrical_efficiency(self, efficiency_curve):
        """Set the cogeneration efficiency to the given function

        Parameters
        ----------
        efficiency_curve : function
            function takes in the current kWh and returns the fractional efficency
        """
        # TODO: type check that efficiency_curve is a function
        self.electrical_efficiency = efficiency_curve

    def set_thermal_efficiency(self, efficiency_curve):
        """Set the cogeneration efficiency to the given function

        Parameters
        ----------
        efficiency_curve : function
            function takes in the current kWh and returns the fractional efficency
        """
        # TODO: type check that efficiency_curve is a function
        self.thermal_efficiency = efficiency_curve


class Boiler(Node):
    """A class representing a boiler that produces heat through natural gas combustion.

    Parameters
    ----------
    id : str
        Boiler ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the boiler

    min_gen : int
        Minimum generation capacity of a single boiler

    max_gen : int
        Maximum generation capacity of a single boiler

    design_gen : int
        Design generation capacity of a single boiler

    num_units : int
        Number of boiler units running in parallel

    tags : dict of Tag
        Data tags associated with this boiler

    Attributes
    ----------
    id : str
        Boiler ID

    input_contents : list of ContentsType
        Contents entering the boiler
        (biogas, natural gas, or a blend of the two)

    output_contents : list of ContentsType
        Contents leaving the boiler (Electricity)

    min_gen : int
        Minimum generation capacity of a single boiler

    max_gen : int
        Maximum generation capacity of a single boiler

    design_gen : int
        Design generation capacity of a single boiler


    num_units : int
        Number of boiler units running in parallel

    tags : dict of Tag
        Data tags associated with this boiler

    thermal_efficiency : function
        Function which takes in the current kWh and returns
        the efficiency as a fraction
    """

    def __init__(
        self, id, input_contents, min_gen, max_gen, design_gen, num_units, tags={}
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.output_contents = [utils.ContentsType.Heat]
        self.num_units = num_units
        self.tags = tags
        self.min_gen = min_gen
        self.max_gen = max_gen
        self.design_gen = design_gen
        self.set_thermal_efficiency(None)

    def __repr__(self):
        return (
            f"<pype_schema.node.Boiler id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"min_gen:{self.min_gen} max_gen:{self.max_gen} "
            f"design_gen:{self.design_gen} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.min_gen == other.min_gen
            and self.max_gen == other.max_gen
            and self.design_gen == other.design_gen
            and self.tags == other.tags
        )

    def set_gen_capacity(self, min, max, design):
        """Set the minimum, maximum, and average generation capacity

        Parameters
        ----------
        min : int
            Minimum generation by a single cogenerator

        max : int
            Maximum generation by a single cogenerator

        design : int
            Design generation by a single cogenerator
        """
        warnings.warn(
            "Please switch from `gen_capacity` tuple to new separate "
            + "`min_gen`, `max_gen` and `design_gen` attributes",
            DeprecationWarning,
        )
        self.gen_capacity = (min, max, design)

    def get_min_gen(self):
        try:
            return self._min_gen
        except AttributeError:
            warnings.warn(
                "Please switch from `gen_capacity` tuple to new `min_gen` attribute",
                DeprecationWarning,
            )
            return self.gen_capacity[0]

    def set_min_gen(self, min_gen):
        self._min_gen = min_gen

    def del_min_gen(self):
        del self._min_gen
        if hasattr(self, "gen_capacity"):
            self.gen_capacity[0] = None

    def get_max_gen(self):
        try:
            return self._max_gen
        except AttributeError:
            warnings.warn(
                "Please switch from `gen_capacity` tuple to new `max_gen` attribute",
                DeprecationWarning,
            )
            return self.gen_capacity[1]

    def set_max_gen(self, max_gen):
        self._max_gen = max_gen

    def del_max_gen(self):
        del self._max_gen
        if hasattr(self, "gen_capacity"):
            self.gen_capacity[1] = None

    def get_design_gen(self):
        try:
            return self._design_gen
        except AttributeError:
            warnings.warn(
                "Please switch from `gen_capacity` tuple to new `design_gen` attribute",
                DeprecationWarning,
            )
            return self.gen_capacity[2]

    def set_design_gen(self, design_gen):
        self._design_gen = design_gen

    def del_design_gen(self):
        del self._design_gen
        if hasattr(self, "gen_capacity"):
            self.gen_capacity[2] = None

    min_gen = property(get_min_gen, set_min_gen, del_min_gen)
    max_gen = property(get_max_gen, set_max_gen, del_max_gen)
    design_gen = property(get_design_gen, set_design_gen, del_design_gen)

    def set_thermal_efficiency(self, efficiency_curve):
        """Set the cogeneration efficiency to the given function

        Parameters
        ----------
        efficiency_curve : function
            function takes in the current kWh and returns the fractional efficency
        """
        # TODO: type check that efficiency_curve is a function
        self.thermal_efficiency = efficiency_curve


class Clarification(Node):
    """A class representing a generic clarifier,
    sedimentation tank, or settling basin.

    Parameters
    ----------
    id : str
        Clarifier ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the clarifier

    output_contents : ContentsType or list of ContentsType
        Contents leaving the clarifier

    min_flow : pint.Quantity or int
        Minimum flow rate of a single clarifier

    max_flow : pint.Quantity or int
        Maximum flow rate of a single clarifier

    design_flow : pint.Quantity or int
        Design flow rate of a single clarifier

    num_units : int
        Number of clarifiers running in parallel

    volume : pint.Quantity or int
        Volume of the clarifier in cubic meters

    tags : dict of Tag
        Data tags associated with this clarifier

    Attributes
    ----------
    id : str
        Clarifier ID

    input_contents : list of ContentsType
        Contents entering the clarifier

    output_contents : list of ContentsType
        Contents leaving the clarifier

    num_units : int
        Number of clarifiers running in parallel

    volume : pint.Quantity or int
        Volume of a single clarifier in cubic meters

    min_flow : pint.Quantity or int
        Minimum flow rate of a single clarifier

    max_flow : pint.Quantity or int
        Maximum flow rate of a single clarifier

    design_flow : pint.Quantity or int
        Design flow rate of a single clarifier

    tags : dict of Tag
        Data tags associated with this clarifier
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        design_flow,
        num_units,
        volume,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.num_units = num_units
        self.volume = volume
        self.tags = tags
        self.min_flow = min_flow
        self.max_flow = max_flow
        self.design_flow = design_flow

    def __repr__(self):
        return (
            f"<pype_schema.node.Clarification id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"volume:{self.volume} min_flow:{self.min_flow} max_flow:{self.max_flow} "
            f"design_flow:{self.design_flow} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.volume == other.volume
            and self.min_flow == other.min_flow
            and self.max_flow == other.max_flow
            and self.design_flow == other.design_flow
            and self.tags == other.tags
        )


class Filtration(Node):
    """The parent class for a wide range of filtration methods,
    such as sand filters, trickling filters, or reverse osmosis membranes.

    Parameters
    ----------
    id : str
        Filter ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the filter

    output_contents : ContentsType or list of ContentsType
        Contents leaving the filter

    min_flow : pint.Quantity or int
        Minimum flow rate of a single filter

    max_flow : pint.Quantity or int
        Maximum flow rate of a single filter

    design_flow : pint.Quantity or int
        Design flow rate of a single filter

    num_units : int
        Number of filters running in parallel

    volume : pint.Quantity or int
        Volume of a single filter in cubic meters

    dosing_rate : dict of DosingType:float
        Dosing information for the filter (key: DosingType, value: rate)

    settling_time : float
        time it takes for the filter to reach the desired operation mode in seconds

    tags : dict of Tag
        Data tags associated with this filter

    Attributes
    ----------
    id : str
        Filter ID

    input_contents : list of ContentsType
        Contents entering the filter

    output_contents : list of ContentsType
        Contents leaving the filter

    num_units : int
        Number of filters running in parallel

    volume : pint.Quantity or int
        Volume of a single filter in cubic meters

    min_flow : pint.Quantity or int
        Minimum flow rate of a single filter

    max_flow : pint.Quantity or int
        Maximum flow rate of a single filter

    design_flow : pint.Quantity or int
        Design flow rate of a single filter

    dosing_rate : dict of DosingType:float
        Dosing information for the filter (key: DosingType, value: rate)

    settling_time : float
        time it takes for the filter to reach the desired operation mode

    tags : dict of Tag
        Data tags associated with this filter
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        design_flow,
        num_units,
        volume,
        dosing_rate={},
        settling_time=0.0,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.num_units = num_units
        self.volume = volume
        self.tags = tags
        self.min_flow = min_flow
        self.max_flow = max_flow
        self.design_flow = design_flow
        self.set_dosing_rate(dosing_rate)
        self.settling_time = settling_time

    def __repr__(self):
        return (
            f"<pype_schema.node.Filtration id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"volume:{self.volume} min_flow:{self.min_flow} max_flow:{self.max_flow} "
            f"design_flow:{self.design_flow} dosing_rate:{self.dosing_rate} "
            f"settling_time:{self.settling_time} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.volume == other.volume
            and self.min_flow == other.min_flow
            and self.max_flow == other.max_flow
            and self.design_flow == other.design_flow
            and self.dosing_rate == other.dosing_rate
            and self.settling_time == other.settling_time
            and self.tags == other.tags
        )

    def get_dosing_rate(self):
        try:
            return self._dosing_rate
        except AttributeError:
            warnings.warn("Please add `dosing_rate` attribute", DeprecationWarning)
            return defaultdict(float)

    def set_dosing_rate(self, dosing_rate):
        self.set_dosing(dosing_rate, mode="rate")

    def del_dosing_rate(self):
        del self._dosing_rate

    dosing_rate = property(get_dosing_rate, set_dosing_rate, del_dosing_rate)


class ROMembrane(Filtration):
    """A class for representing a reverse osmosis membrane process.

    Parameters
    ----------
    id : str
        ROMembrane ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the RO membrane

    output_contents : ContentsType or list of ContentsType
        Contents leaving the RO membrane

    min_flow : pint.Quantity or int
        Minimum flow rate of the RO membrane

    max_flow : pint.Quantity or int
        Maximum flow rate of the RO membrane

    design_flow : pint.Quantity or int
        Design flow rate of a single filter

    num_units : int
        Number of RO membranes running in parallel

    volume : pint.Quantity or int
        Volume of the RO membrane in cubic meters

    area : float
        Area of the RO membrane in square meters

    permeability : float
        Permeability of the RO membrane

    selectivity : float
        Selectivity of the RO membrane

    dosing_rate : dict of DosingType:float
        Dosing information for the RO membrane (key: DosingType, value: rate)

    settling_time : float
        time it takes for the filter to reach the desired operation mode

    tags : dict of Tag
        Data tags associated with the RO membrane

    Attributes
    ----------
    id : str
        ROMembrane ID

    input_contents : list of ContentsType
        Contents entering the RO membrane

    output_contents : list of ContentsType
        Contents leaving the RO membrane

    num_units : int
        Number of RO membranes running in parallel

    volume : pint.Quantity or int
        Volume of a single filter in cubic meters

    min_flow : pint.Quantity or int
        Minimum flow rate of a single filter

    max_flow : pint.Quantity or int
        Maximum flow rate of a single filter

    design_flow : pint.Quantity or int
        Design flow rate of a single filter

    area : float
        Area of the RO membrane in square meters

    permeability : float
        Permeability of the RO membrane

    selectivity : float
        Selectivity of the RO membrane

    dosing_rate : dict of DosingType:float
        Dosing information for the RO membrane (key: DosingType, value: rate)

    settling_time : float
        time it takes for the filter to reach the desired operation mode

    tags : dict of Tag
        Data tags associated with the RO membrane
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        design_flow,
        num_units,
        volume,
        area,
        permeability,
        selectivity,
        dosing_rate={},
        settling_time=0.0,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.num_units = num_units
        self.volume = volume
        self.tags = tags
        self.min_flow = min_flow
        self.max_flow = max_flow
        self.design_flow = design_flow
        self.area = area
        self.permeability = permeability
        self.selectivity = selectivity
        self.set_dosing_rate(dosing_rate)
        self.settling_time = settling_time

    def __repr__(self):
        return (
            f"<pype_schema.node.Filtration.ROMembrane id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"volume:{self.volume} min_flow:{self.min_flow} max_flow:{self.max_flow} "
            f"design_flow:{self.design_flow} area:{self.area} "
            f"permeability:{self.permeability} selectivity:{self.selectivity} "
            f"dosing_rate:{self.dosing_rate} settling_time:{self.settling_time} "
            f"tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.volume == other.volume
            and self.min_flow == other.min_flow
            and self.max_flow == other.max_flow
            and self.design_flow == other.design_flow
            and self.area == other.area
            and self.permeability == other.permeability
            and self.selectivity == other.selectivity
            and self.dosing_rate == other.dosing_rate
            and self.settling_time == other.settling_time
            and self.tags == other.tags
        )


class Screening(Node):
    """A class representing the screening process for removing
    large solids from the intake of a facility, such as a bar screen.

    Parameters
    ----------
    id : str
        Screen ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the screen

    output_contents : ContentsType or list of ContentsType
        Contents leaving the screen

    min_flow : pint.Quantity or int
        Minimum flow rate of a single screen

    max_flow : pint.Quantity or int
        Maximum flow rate of a single screen

    design_flow : pint.Quantity or int
        Design flow rate of a single screen

    num_units : int
        Number of screens running in parallel

    tags : dict of Tag
        Data tags associated with this screen

    Attributes
    ----------
    id : str
        Screen ID

    input_contents : list of ContentsType
        Contents entering the screen

    output_contents : list of ContentsType
        Contents leaving the screen

    num_units : int
        Number of screens running in parallel

    min_flow : pint.Quantity or int
        Minimum flow rate of a single screen

    max_flow : pint.Quantity or int
        Maximum flow rate of a single screen

    design_flow : pint.Quantity or int
        Design flow rate of a single screen

    tags : dict of Tag
        Data tags associated with this screen
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        design_flow,
        num_units,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.num_units = num_units
        self.tags = tags
        self.min_flow = min_flow
        self.max_flow = max_flow
        self.design_flow = design_flow

    def __repr__(self):
        return (
            f"<pype_schema.node.Screening id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"min_flow:{self.min_flow} max_flow:{self.max_flow} "
            f"design_flow:{self.design_flow} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.min_flow == other.min_flow
            and self.max_flow == other.max_flow
            and self.design_flow == other.design_flow
            and self.tags == other.tags
        )


class Conditioning(Node):
    """A class for representing biogas conditioners.
    The conditioner prepares 'raw' biogas from the digester
    by removing impurities and readying it for combustion
    for `Cogeneration`.

    Parameters
    ----------
    id : str
        Conditioner ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the biogas conditioner

    output_contents : ContentsType or list of ContentsType
        Contents leaving the biogas conditioner

    min_flow : pint.Quantity or int
        Minimum flow rate of a single biogas conditioner

    max_flow : pint.Quantity or int
        Maximum flow rate of a single biogas conditioner

    design_flow : pint.Quantity or int
        Design flow rate of a single biogas conditioner

    num_units : int
        Number of biogas conditioners running in parallel

    tags : dict of Tag
        Data tags associated with this biogas conditioner

    Attributes
    ----------
    id : str
        Conditioner ID

    input_contents : list of ContentsType
        Contents entering the biogas conditioner

    output_contents : list of ContentsType
        Contents leaving the biogas conditioner

    num_units : int
        Number of biogas conditioners running in parallel

    min_flow : pint.Quantity or int
        Minimum flow rate of a single biogas conditioner

    max_flow : pint.Quantity or int
        Maximum flow rate of a single biogas conditioner

    design_flow : pint.Quantity or int
        Design flow rate of a single biogas conditioner

    tags : dict of Tag
        Data tags associated with this screen
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        design_flow,
        num_units,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.num_units = num_units
        self.tags = tags
        self.min_flow = min_flow
        self.max_flow = max_flow
        self.design_flow = design_flow

    def __repr__(self):
        return (
            f"<pype_schema.node.Conditioning id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"min_flow:{self.min_flow} max_flow:{self.max_flow} "
            f"design_flow:{self.design_flow} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.min_flow == other.min_flow
            and self.max_flow == other.max_flow
            and self.design_flow == other.design_flow
            and self.tags == other.tags
        )


class Thickening(Node):
    """A class to represent a general thickener,
    such as gravity belt, dissolved air float (DAF),
    or centrifugal thickening.

    Parameters
    ----------
    id : str
        Thickener ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the thickener

    output_contents : ContentsType or list of ContentsType
        Contents leaving the thickener

    min_flow : pint.Quantity or int
        Minimum flow rate of a single thickener

    max_flow : pint.Quantity or int
        Maximum flow rate of a single thickener

    design_flow : pint.Quantity or int
        Design flow rate of a single thickener

    num_units : int
        Number of thickeners running in parallel

    volume : pint.Quantity or int
        Volume of a single thickener in cubic meters

    tags : dict of Tag
        Data tags associated with this thickener

    Attributes
    ----------
    id : str
        Thickener ID

    input_contents : list of ContentsType
        Contents entering the thickener

    output_contents : list of ContentsType
        Contents leaving the thickener

    num_units : int
        Number of thickeners running in parallel

    volume : pint.Quantity or int
        Volume of a single thickener in cubic meters

    min_flow : pint.Quantity or int
        Minimum flow rate of a single thickener

    max_flow : pint.Quantity or int
        Maximum flow rate of a single thickener

    design_flow : pint.Quantity or int
        Design flow rate of a single thickener

    tags : dict of Tag
        Data tags associated with this thickener
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        design_flow,
        num_units,
        volume,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.num_units = num_units
        self.volume = volume
        self.tags = tags
        self.min_flow = min_flow
        self.max_flow = max_flow
        self.design_flow = design_flow

    def __repr__(self):
        return (
            f"<pype_schema.node.Thickening id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"volume:{self.volume} min_flow:{self.min_flow} "
            f"max_flow:{self.max_flow} design_flow:{self.design_flow} "
            f"tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.volume == other.volume
            and self.min_flow == other.min_flow
            and self.max_flow == other.max_flow
            and self.design_flow == other.design_flow
            and self.tags == other.tags
        )


class Aeration(Node):
    """A generic class for an aeration basin.

    Parameters
    ----------
    id : str
        Aerator ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the aeration basin

    output_contents : ContentsType or list of ContentsType
        Contents leaving the aeration basin

    min_flow : pint.Quantity or int
        Minimum flow rate of a single aeration basin

    max_flow : pint.Quantity or int
        Maximum flow rate of a single aeration basin

    design_flow : pint.Quantity or int
        Design flow rate of a single aeration basin

    num_units : int
        Number of aeration basins running in parallel

    volume : pint.Quantity or int
        Volume of a single aeration basin in cubic meters

    tags : dict of Tag
        Data tags associated with this aerator

    Attributes
    ----------
    id : str
        Aerator ID

    input_contents : list of ContentsType
        Contents entering the aeration basin

    output_contents : list of ContentsType
        Contents leaving the aeration basin

    num_units : int
        Number of aeration basins running in parallel

    volume : pint.Quantity or int
        Volume of a single aeration basin in cubic meters

    min_flow : pint.Quantity or int
        Minimum flow rate of a single aeration basin

    max_flow : pint.Quantity or int
        Maximum flow rate of a single aeration basin

    design_flow : pint.Quantity or int
        Design flow rate of a single aeration basin

    tags : dict of Tag
        Data tags associated with this aerator
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        design_flow,
        num_units,
        volume,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.num_units = num_units
        self.volume = volume
        self.tags = tags
        self.min_flow = min_flow
        self.max_flow = max_flow
        self.design_flow = design_flow

    def __repr__(self):
        return (
            f"<pype_schema.node.Aeration id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"volume:{self.volume} min_flow:{self.min_flow} "
            f"max_flow:{self.max_flow} design_flow:{self.design_flow} "
            f"tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.volume == other.volume
            and self.min_flow == other.min_flow
            and self.max_flow == other.max_flow
            and self.design_flow == other.design_flow
            and self.tags == other.tags
        )


class Disinfection(Node):
    """A generic class for a disinfection process,
    such as chlorination, ozone, or UV light.

    Parameters
    ----------
    id : str
        Disinfector ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the disinfector

    output_contents : ContentsType or list of ContentsType
        Contents leaving the disinfector

    min_flow : pint.Quantity or int
        Minimum flow rate of a single disinfector

    max_flow : pint.Quantity or int
        Maximum flow rate of a single disinfector

    design_flow : pint.Quantity or int
        Design flow rate of a single disinfector

    num_units : int
        Number of disinfectors running in parallel

    volume : pint.Quantity or int
        Volume of a single disinfectors in cubic meters

    dosing_rate : dict of DosingType:float
        Dosing information for the disinfector (key: DosingType, value: rate)

    residence_time : pint.Quantity or float
        Residence time of the disinfector

    tags : dict of Tag
        Data tags associated with this disinfector

    Attributes
    ----------
    id : str
        Disinfector ID

    input_contents : list of ContentsType
        Contents entering the disinfector

    output_contents : list of ContentsType
        Contents leaving the disinfector

    num_units : int
        Number of disinfector running in parallel

    volume : pint.Quantity or int
        Volume of a single disinfector in cubic meters

    min_flow : pint.Quantity or int
        Minimum flow rate of a single disinfector

    max_flow : pint.Quantity or int
        Maximum flow rate of a single disinfector

    design_flow : pint.Quantity or int
        Design flow rate of a single disinfector

    dosing_rate : dict of DosingType:float
        Dosing information for the disinfector (key: DosingType, value: rate)

    residence_time : pint.Quantity or float
        Residence time of the disinfector

    tags : dict of Tag
        Data tags associated with this disinfector
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        design_flow,
        num_units,
        volume,
        dosing_rate={},
        residence_time=None,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.num_units = num_units
        self.volume = volume
        self.tags = tags
        self.min_flow = min_flow
        self.max_flow = max_flow
        self.design_flow = design_flow
        self.set_dosing_rate(dosing_rate)
        self.residence_time = residence_time

    def __repr__(self):
        return (
            f"<pype_schema.node.Disinfection id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"volume:{self.volume} min_flow:{self.min_flow} "
            f"max_flow:{self.max_flow} design_flow:{self.design_flow} "
            f"dosing_rate:{self.dosing_rate} residence_time:{self.residence_time} "
            f"tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.volume == other.volume
            and self.min_flow == other.min_flow
            and self.max_flow == other.max_flow
            and self.design_flow == other.design_flow
            and self.dosing_rate == other.dosing_rate
            and self.residence_time == other.residence_time
            and self.tags == other.tags
        )

    def get_residence_time(self):
        try:
            return self._res_time
        except AttributeError:
            warnings.warn("Please add `residence_time` attribute", DeprecationWarning)
            return None

    def set_residence_time(self, residence_time):
        self._res_time = residence_time

    def del_residence_time(self):
        del self._res_time

    def get_dosing_rate(self):
        try:
            return self._dosing_rate
        except AttributeError:
            warnings.warn("Please add `dosing_rate` attribute", DeprecationWarning)
            return defaultdict(float)

    def set_dosing_rate(self, dosing_rate):
        self.set_dosing(dosing_rate, mode="rate")

    def del_dosing_rate(self):
        del self._dosing_rate

    residence_time = property(
        get_residence_time, set_residence_time, del_residence_time
    )
    dosing_rate = property(get_dosing_rate, set_dosing_rate, del_dosing_rate)


class Chlorination(Disinfection):
    """A class for a chlorination basin.

    Parameters
    ----------
    id : str
        Chlorinator ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the chlorinator

    output_contents : ContentsType or list of ContentsType
        Contents leaving the chlorinator

    min_flow : pint.Quantity or int
        Minimum flow rate of a single chlorinator

    max_flow : pint.Quantity or int
        Maximum flow rate of a single chlorinator

    design_flow : pint.Quantity or int
        Design flow rate of a single chlorinator

    num_units : int
        Number of chlorinators running in parallel

    volume : pint.Quantity or int
        Volume of a single chlorinator in cubic meters

    dosing_rate : dict of DosingType:float
        Dosing information for the chlorinator (key: DosingType, value: rate)

    residence_time : pint.Quantity or float
        Residence time of the chlorinator

    tags : dict of Tag
        Data tags associated with this chlorinator

    Attributes
    ----------
    id : str
        Chlorinator ID

    input_contents : list of ContentsType
        Contents entering the chlorinator

    output_contents : list of ContentsType
        Contents leaving the chlorinator

    num_units : int
        Number of chlorinators running in parallel

    volume : pint.Quantity or int
        Volume of a single chlorinator in cubic meters

    min_flow : pint.Quantity or int
        Minimum flow rate of a single chlorinator

    max_flow : pint.Quantity or int
        Maximum flow rate of a single chlorinator

    design_flow : pint.Quantity or int
        Design flow rate of a single chlorinator

    dosing_rate : dict of DosingType:float
        Dosing information for the chlorinator (key: DosingType, value: rate)

    residence_time : pint.Quantity or float
        Residence time of the chlorinator

    tags : dict of Tag
        Data tags associated with this chlorinator
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        design_flow,
        num_units,
        volume,
        dosing_rate={},
        residence_time=None,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.num_units = num_units
        self.volume = volume
        self.tags = tags
        self.min_flow = min_flow
        self.max_flow = max_flow
        self.design_flow = design_flow
        self.set_dosing_rate(dosing_rate)
        self.residence_time = residence_time

    def __repr__(self):
        return (
            f"<pype_schema.node.Chlorination id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"volume:{self.volume} min_flow:{self.min_flow} "
            f"max_flow:{self.max_flow} design_flow:{self.design_flow} "
            f"dosing_rate:{self.dosing_rate} residence_time:{self.residence_time} "
            f"tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.volume == other.volume
            and self.min_flow == other.min_flow
            and self.max_flow == other.max_flow
            and self.design_flow == other.design_flow
            and self.dosing_rate == other.dosing_rate
            and self.residence_time == other.residence_time
            and self.tags == other.tags
        )


class UVSystem(Disinfection):
    """
    Parameters
    ----------
    id : str
        UV System ID

    input_contents : list of ContentsType
        Contents entering the UV system

    output_contents : list of ContentsType
        Contents leaving the UV system

    num_units : int
        Number of UV systems running in parallel

    residence_time : pint.Quantity or float
        Time in seconds that the water is exposed to UV light

    intensity : pint.Quantity or float
        Intensity of the UV light in W/m^2

    area : pint.Quantity or float
        Application area of the UV light in m^2

    tags : dict of Tag
        Data tags associated with this chlorinator

    Attributes
    ----------
    id : str
        UVSystem ID

    num_units : int
        Number of chlorinators running in parallel

    residence_time : pint.Quantity or float
        Time in seconds that the water is exposed to UV light

    dosing_rate : dict of DosingType:float
        UV intensity in the UV system

    dosing_area : dict of DosingType:float
        Area of the UV system that is exposed to UV light

    tags : dict of Tag
        Data tags associated with this chlorinator
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        design_flow,
        num_units,
        volume,
        residence_time,
        intensity,
        area,
        tags={},
    ):
        self.id = id
        self.set_contents(input_contents, "input_contents")
        self.set_contents(output_contents, "output_contents")
        self.min_flow = min_flow
        self.max_flow = max_flow
        self.design_flow = design_flow
        self.num_units = num_units
        self.volume = volume
        self.residence_time = residence_time
        self.set_dosing_rate({"UVLight": intensity})
        self.set_dosing_area({"UVLight": area})
        self.tags = tags

    def __repr__(self):
        return (
            f"<pype_schema.node.UVSystem id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"volume:{self.volume} min_flow:{self.min_flow} "
            f"max_flow:{self.max_flow} design_flow:{self.design_flow} "
            f"residence_time:{self.residence_time} dosing_rate:{self.dosing_rate} "
            f"dosing_area:{self.dosing_area} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.volume == other.volume
            and self.residence_time == other.residence_time
            and self.dosing_rate == other.dosing_rate
            and self.dosing_area == other.dosing_area
            and self.tags == other.tags
        )

    def get_dosing_area(self):
        return self._dosing_area

    def set_dosing_area(self, dosing_area):
        self.set_dosing(dosing_area, mode="area")

    def del_dosing_area(self):
        del self._dosing_area

    dosing_area = property(get_dosing_area, set_dosing_area, del_dosing_area)


class Flaring(Node):
    """
    Parameters
    ----------
    id : str
        Flare ID

    num_units : int
        Number of flares running in parallel

    min_flow : pint.Quantity or int
        Minimum flow rate of a single flare

    max_flow : pint.Quantity or int
        Maximum flow rate of a single flare

    design_flow : pint.Quantity or int
        Design flow rate of a single flare

    tags : dict of Tag
        Data tags associated with this flare

    Attributes
    ----------
    id : str
        Flare ID

    input_contents : list of ContentsType
        Contents entering the flare

    num_units : int
        Number of flares running in parallel

    min_flow : pint.Quantity or int
        Minimum flow rate of a single flare

    max_flow : pint.Quantity or int
        Maximum flow rate of a single flare

    design_flow : pint.Quantity or int
        Design flow rate of a single flare

    tags : dict of Tag
        Data tags associated with this flare
    """

    def __init__(self, id, num_units, min_flow, max_flow, design_flow, tags={}):
        self.id = id
        self.input_contents = [utils.ContentsType.Biogas]
        self.num_units = num_units
        self.tags = tags
        self.min_flow = min_flow
        self.max_flow = max_flow
        self.design_flow = design_flow

    def __repr__(self):
        return (
            f"<pype_schema.node.Flaring id:{self.id} "
            f"input_contents:{self.input_contents} num_units:{self.num_units} "
            f"min_flow:{self.min_flow} max_flow:{self.max_flow}"
            f"design_flow:{self.design_flow} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.num_units == other.num_units
            and self.min_flow == other.min_flow
            and self.max_flow == other.max_flow
            and self.design_flow == other.design_flow
            and self.tags == other.tags
        )
