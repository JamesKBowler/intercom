# The MIT License (MIT)
#
# Copyright (c) 2020 James K Bowler, Data Centauri Ltd
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from intercom.base import BaseInterprocessSocket

from collections import deque
from threading import Thread

import json
import time
import socket
import struct
import uuid
import random


class SocketReceive(BaseInterprocessSocket):
    """
    A class representing a none blocking SocketReceive.
    It contains an id for tracking with the ability
    to handle different types of streamed events.
    Parameters
    ----------
    port       : TCP port number
    host       : IP Address
    identifier : human-readable identifier

    Exposes
    -------
    read_buffer()
    clear_buffer()
    close_connection()

    """

    def __init__(
        self, port=None, host=None, identifier="rx", queue_len=10000, should_print=True
    ):
        # Facts
        self.id = "{}:{}".format(uuid.uuid4().hex, identifier)
        self.callback_running = False
        self.should_print = should_print
        # Queue/Buffer settings
        self.queue_len = queue_len
        self._buffer = deque(maxlen=self.queue_len)
        # Pre connection settings
        self._stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._stream.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Setup host and port information
        if host is None:
            host = 'localhost'
        if port is None:
            while port is None:
                _port = random.randint(55000, 60000)
                port = self._bind_socket(host, _port)
        else:
            self._bind_socket(host, port, raise_catch=True)
        self.host = host
        self.port = port
        # Post connection settings
        self._stream.listen(5)
        # Start the
        self.t = Thread(
            target=self.stream_to_buffer,
            args=(self.id, self._stream, self._buffer,)
        )
        self.t.daemon = True
        self.t.start()
        # Final call option
        self.on_open()

    @staticmethod
    def stream_to_buffer(sid, stream, buffer):
        """
        Stream reading.
        """

        def handle(hid, skt, callback):
            def recv_msg(rx):
                """
                Get the message
                """
                raw_msglen = recvall(rx, 4)
                if not raw_msglen:
                    return None
                msglen = struct.unpack('>I', raw_msglen)[0]
                return recvall(rx, msglen)

            def recvall(rx, n):
                """
                Piece large data
                """
                data = b''
                while len(data) < n:
                    packet = rx.recv(n - len(data))
                    if not packet:
                        return None
                    data += packet
                return data

            def container(res):
                """
                Container for payload
                """
                sm = json.loads(res.decode())
                if not isinstance(sm, list):
                    raise AttributeError("Loaded json must be a list")
                return sm

            result = recv_msg(skt)
            skt.send(b'ACK!')
            skt.close()

            if result:
                callback.append(container(result))
            else:
                raise EOFError(
                    "Unexpected End of Stream {}".format(hid)
                )

        while True:
            try:
                sock = stream.accept()[0]
            except OSError:
                print("Shutting down SocketReader")
                break
            handle(sid, sock, buffer)

    def __del__(self):
        self.close_session()
        self.clear_buffer()

    def _bind_socket(self, host, port, raise_catch=False):
        try:
            self._stream.bind((host, port))
            return port
        except OSError:
            if raise_catch:
                raise OSError("Port: {} in use".format(port))
            return None

    def __read_buffer(self, sleepy_time=0.001):
        if len(self._buffer) >= self.queue_len:
            raise BufferError("The message buffer limit has been reached")
        try:
            return self._buffer.popleft()
        except IndexError:
            return time.sleep(sleepy_time)

    def callback_reader(self, call_back):
        if not self.callback_running:
            log_message = "Notification: {}: {}, callback started".format(
                self.__class__.__name__, self.id
            )
            self._log(log_message)
            self.callback_running = True
            while self.callback_running:
                msg = self.__read_buffer()
                if not msg:
                    continue
                call_back(msg)
            self.callback_running = False
            log_message = "Notification: {}: {}, callback stopppe".format(
                self.__class__.__name__, self.id
            )
            self._log(log_message)

    def clear_buffer(self):
        self._buffer = deque(maxlen=self.queue_len)

    def close_session(self):
        try:
            self._stream.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        time.sleep(2)
        self._stream.close()
        self.on_close()


if __name__ == "__main__":

    def callback_print(msg):
        print(msg)

    stream_reader = SocketReceive(
        port=61113,
        host="0.0.0.0"
    )

    try:
        stream_reader.callback_reader(callback_print)

    except KeyboardInterrupt:
        stream_reader.close_session()
        stream_reader.clear_buffer()
