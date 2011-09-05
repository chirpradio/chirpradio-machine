"""
A FrameSplitter consumes a sequence of messages, and explodes BLOCKs
into sequences of FRAMES.
"""

from chirp.common import mp3_frame
from chirp.common import mp3_header
from chirp.stream import message


class FrameSplitter(message.MessageConsumer,
                    message.MessageSource):

    # TODO(trow): Don't hard-wire this parameter.
    sampling_rate_hz = 44100

    def __init__(self, src):
        message.MessageConsumer.__init__(self, src)
        message.MessageSource.__init__(self)
        self._expected_hdr = mp3_header.MP3Header(
            sampling_rate_hz=self.sampling_rate_hz)
        self._buffered = []
        # This is the starting ms timestamp of the first block that
        # goes through the splitter.
        self._start_timestamp_ms = None
        # This tracks the number of elapsed ms, based on the MP3 frames
        # that we observe passing through the splitter.
        self._elapsed_frame_ms = 0
        # Normally we expect that the elapsed wall-clock time and the
        # elapsed time based on counting up frame durations will be
        # approximately equal.  This is not always the case, though:
        # when we first connect to a Barix, it will occasionally
        # return up to ~1s of buffered audio almost immediately.  When
        # this happens, it can take 200-300ms before the system gets
        # back into equilibrium of 1 second of audio per second of
        # wall-clock time.  Since there is no time sync in the stream
        # returned by the Barix, we need to introduce a fudge factor
        # to avoid systematic bias when assigning our own start and end
        # times to the messages we produce by splitting the blocks.
        self._start_adjustment_ms = 0

    def _process_message(self, msg):
        if msg.message_type != message.BLOCK:
            # Clear the buffer and reset our various time-tracking
            # variables before passing the message through.
            self._buffered = []
            self._start_timestamp_ms = None
            self._elapsed_frame_ms = 0
            self._add_message(msg)
            return
        # If necessary, remember the start time of this message.
        if self._start_timestamp_ms is None:
            self._start_timestamp_ms = msg.start_timestamp_ms
        # Take the buffered data and split it into MP3 frames.
        self._buffered.append(msg.payload)
        frames = list(mp3_frame.split_blocks(
                iter(self._buffered), expected_hdr=self._expected_hdr))
        self._buffered = []
        # If any of the last frames appear to be junk, they might
        # contain a truncated frame.  If so, stick them back onto
        # the buffer.
        while frames:
            last_hdr, last_buffer = frames[-1]
            if last_hdr is not None:
                break
            self._buffered.insert(0, last_buffer)
            frames.pop()
        # Turn the frames into FRAME messages and add them to our
        # queue.
        start_ms = (self._start_timestamp_ms
                    + self._start_adjustment_ms
                    + self._elapsed_frame_ms)
        for hdr, data in frames:
            new_msg = message.Message()
            if hdr is None:
                new_msg.message_type = message.BLOCK
                duration_ms = 0
            else:
                new_msg.message_type = message.FRAME
                duration_ms = hdr.duration_ms
                self._elapsed_frame_ms += duration_ms
            new_msg.connection_id = msg.connection_id
            new_msg.connection_offset = msg.connection_offset
            new_msg.mp3_header = hdr
            new_msg.payload = data
            # Now set the start and end timestamps; these are our best
            # approximations, and might do alarming things like jump
            # backward in time.
            new_msg.start_timestamp_ms = int(start_ms)
            new_msg.end_timestamp_ms = int(start_ms + duration_ms)
            start_ms += duration_ms
            self._add_message(new_msg)
        # Now let's see if we need to modify our start-time adjustment.
        # First, compute the total wall-clock time so far.
        wall_clock_ms = msg.end_timestamp_ms - self._start_timestamp_ms
        # Now find the difference between the elaped wall-clock time
        # and the elapsed time implied by the frames.
        delta_ms = wall_clock_ms - self._elapsed_frame_ms
        # If the observed delta is negative (indicating that we've
        # seen more frames than would normally be possible given how
        # much time has passed), our new fudge factor will be the
        # average of the observed discepancy and the previous fudge
        # factor.
        if delta_ms < 0:
            self._start_adjustment_ms = (
                self._start_adjustment_ms + delta_ms)/2
