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


from intercom.tx import SocketTransmit
from intercom.rx import SocketReceive

from threading import Thread


class Intercom:
    def __init__(
        self, host, port, call_back=None, on_system=None,
        on_update=None, on_get=None, should_print=False
    ):
        self.should_print = should_print

        if call_back is None:
            if on_system is not None:
                self.on_system = on_system
            if on_update is not None:
                self.on_update = on_update
            if on_get is not None:
                self.on_get = on_get
        else:
            self._callback = call_back

        self.transmit = SocketTransmit(
            identifier='radio_tx',
            should_print=should_print
        )
        self.receive = SocketReceive(
            host=host,
            port=port,
            identifier='radio_rx',
            should_print=should_print
        )
        self._t = Thread(
            target=self.receive.callback_reader,
            args=(self._callback,)
        )

    def _callback(self, message):
        unique_id = message[0]
        sender = message[1]
        update_type = message[2]
        payload = message[3]
        if update_type == 'update':
            self.on_update(unique_id, sender, payload)

        elif update_type == 'system':
            self.on_system(unique_id, sender, payload)

        elif update_type == 'get':
            self.on_get(unique_id, sender, payload)

    def _log(self, log_message):
        message = "-- Radio: {}".format(log_message)
        if self.should_print:
            print(message)

    def on_update(self, unique_id, sender, payload):
        log_message = "Sender: {}, {}, Payload: {}".format(unique_id, sender, payload)
        self._log(log_message)

    def on_system(self, unique_id, sender, payload):
        log_message = "Sender: {}, {}, Payload: {}".format(unique_id, sender, payload)
        self._log(log_message)

    def on_get(self, unique_id, sender, payload):
        log_message = "Sender: {}, {}, Payload: {}".format(unique_id, sender, payload)
        self._log(log_message)

    def start(self):
        if self.receive.callback_running:
            return
        self._t.start()
        self.receive.callback_running = True

    def stop(self):
        if not self.receive.callback_running:
            return
        self.receive.callback_running = False
