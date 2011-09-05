
import socket


_GET_REQUEST = """GET %(path)s HTTP/1.1
User-Agent: chirp.common.http
Host: %(host)s:%(port)d
Accept: */*
Connection: close

""".replace("\n", "\r\n")

_READ_SIZE = 4096


def get_with_timeout(host, port, path, timeout_s):
    """Perform an HTTP GET against the given host, port and path.

    Args:
      host: A string, the hostname to connect to.
      port: An integer, a port to connect to.
      path: A string, the path to connect to.
      timeout_s: The number of seconds to set as the timeout for the socket
        being used to connect to the remote host.

    Returns:
      The body of the HTTP response, or None if there is an error.
     """
    # Construct a socket.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_s)
    # Connect to the remote host.
    try:
        sock.connect((host, port))
    except socket.error, err:
        return None
    # Create and send an HTTP request.
    request_str = _GET_REQUEST % {
        "host": host, "port": port, "path": path,
        }
    try:
        sock.sendall(request_str)
    except socket.error, err:
        return None
    # Pull back the response.
    response_list = []
    while True:
        try:
            data = sock.recv(_READ_SIZE)
            if not data:
                break
            response_list.append(data)
        except socket.error, err:
            return None
    response = "".join(response_list)
    # Strip off headers.
    i = response.find("\r\n\r\n")
    if i != -1:
        response = response[i+4:]

    return response
        
        

    
