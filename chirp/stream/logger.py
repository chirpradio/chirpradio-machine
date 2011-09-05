
from chirp.common import timestamp
from chirp.stream import message

class Logger(message.MessageConsumer):

    def __init__(self, src):
        message.MessageConsumer.__init__(self, src)
        self._fh = open("/tmp/barix.log", "w", 0)  # Unbuffered

    def _process_message(self, msg):
        info = [msg.message_type]
        if msg.message_type == message.FRAME:
            info.append(str(msg.mp3_header))
        output = "%s: %s\n" % (
            timestamp.get_human_readable_ms(timestamp.now_ms()),
            " / ".join(info))
        if msg.message_type == message.BLOCK:
            output += "length = %d\n%r\n" % (len(msg.payload), msg.payload)
        elif msg.message_type == message.RESPONSE:
            output += "".join(["%s: %s\n" % x for x in msg.http_headers.items()])
        print output.strip()
        self._fh.write(output)
