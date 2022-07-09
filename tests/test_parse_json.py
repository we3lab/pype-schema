from wwtp_configuration.parse_json import JSONParser

parser = JSONParser("data/svcw.json")
network = parser.initialize_network()
