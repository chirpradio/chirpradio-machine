
import re
import time
from chirp.common import http


def _remove_tags(html_str):
    cleaned = re.sub("\<[^>]+\>", "", html_str)
    cleaned = cleaned.replace("&nbsp;", " ")
    cleaned = re.sub("\s{2,}", " ", cleaned)
    return cleaned.strip()


_CLIENT_RE = re.compile("(\d+\.\d+\.\d+\.\d+):src port (\d+) :dst port (\d+)")


class Barix(object):

    TIMEOUT_S = 1.0

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.base_url = "http://%s:%d" % (host, port)
        self.status_url = self.base_url + "/uistatusl.html"
        self.clients_url = self.base_url + "/clients.cgi"
        
        self.last_update_time = None
        self.last_update_time_str = "unknown"
        self.status = "unknown"
        self.left_level = "unknown"
        self.right_level = "unknown"
        self.clients = {}

    def ping(self):
        status_str = http.get_with_timeout(
            self.host, self.port, "/uistatusl.html", self.TIMEOUT_S)
        if status_str is None:
            return False
        status_str = _remove_tags(status_str).replace("-->", "")
        status_info = status_str.split()

        clients_str = http.get_with_timeout(
            self.host, self.port, "/clients.cgi", self.TIMEOUT_S)
        if clients_str is None:
            return False
        clients_str = _remove_tags(clients_str)
        clients_list = _CLIENT_RE.findall(clients_str)

        if len(status_info) == 3:
            self.status = status_info[0]
            self.left_level = status_info[1]
            self.right_level = status_info[2]
        else:
            self.status = "unknown"
            self.left_level = "unknown"
            self.right_level = "unknown"

        clients = {}
        for ip, near_port, far_port in clients_list:
            if near_port != "80":
                clients[near_port] = (ip, far_port)
        self.clients = clients

        self.last_update_time = time.time()
        self.last_update_time_str = time.ctime(self.last_update_time)
        return True
    
