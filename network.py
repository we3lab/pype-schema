class Network:
    """A water utility represented as a set of connections and nodes

    Parameters
    ----------
    nodes : dict of Node
        nodes in the network, e.g. pumps, tanks, or facilities

    connections : dict of Connections
        connections

    Attributes
    ----------
    nodes : dict of Node
        nodes in the network, e.g. pumps, tanks, or facilities

    connections : dict of Connections
        connections in the network, e.g. pipes
    """
    def __init__(self, nodes={}, connections={}):
        self.nodes = nodes
        self.connections = connections

    def add_node(self, node):
        """Adds a node to the network

        Parameters
        ----------
        process : Node
            Node object to add to the network
        """
        self.nodes[node.id] = node

    def remove_node(self, node_name):
        """Removes a node from the network

        Parameters
        ----------
        node_name : str
            name of node to remove

        Raises
        ------
        KeyError
            if `node_name` is not found
        """
        del self.nodes[node_name]

    def add_connection(connection):
        """Adds a connection to the network

        Parameters
        ----------
        connection : Connection
            Connection object to add to the network
        """
        self.connections[connection.id] = connection

    def remove_connection(self, connection_name):
        """Removes a connection from the network

        Parameters
        ----------
        connection_name : str
            name of connection to remove

        Raises
        ------
        KeyError
            if `connection_name` is not found
        """
        del self.connections[connection_name]
