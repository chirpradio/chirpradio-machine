import contextlib


class CustomPrint(object):
    """
    This class defines a callable object that works similarly to the print()
    function. However, it provides a context manager that allows you to specify
    a different write function that can be used to send messages to somewhere
    other than standard output (for example, a web interface).

    """

    def __init__(self):
        self.write = self.default_write

    def __call__(self, message=None, **kwargs):
        self.write(message, **kwargs)

    def default_write(self, message=None, **kwargs):
        if message is None:
            # If there were no arguments at all, print a newline to stdout.
            if len(kwargs) == 0:
                print
        else:
            if not isinstance(message, basestring):
                message = unicode(message)
            if not isinstance(message, str):
                # This is a Unicode object so we should encode it as a byte
                # string before writing it to the console.
                message = message.encode('utf-8')
            print(message)

    @contextlib.contextmanager
    def use_write_function(self, func):
        self.write = func
        yield
        self.write = self.default_write


cprint = CustomPrint()
