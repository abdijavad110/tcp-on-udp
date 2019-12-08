import json
from collections import namedtuple


class Conf(object):
    SENDING_TIME = 30

    SERVER_CONf = json.loads(open('server_configuration.json', 'r').read(),
                             object_hook=lambda d: namedtuple('SERVER_CONf', d.keys())(*d.values()))
    CLIENT_CONF = json.loads(open('client_configuration.json', 'r').read(),
                             object_hook=lambda d: namedtuple('CLIENT_CONF', d.keys())(*d.values()))

    SRV_TCP = namedtuple('SRV_TCP', 'LISTEN SYN_RCVD ESTAB CLOSE_WAIT LAST_ACK CLOSED')(0, 1, 2, 3, 4, 5)
    CLT_TCP = namedtuple('SRV_TCP', 'CLOSED SYN_SENT ESTAB FIN_WAIT_1 FIN_WAIT_2 TIMED_WAIT')(0, 1, 2, 3, 4, 5)
