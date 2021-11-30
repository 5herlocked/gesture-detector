"""
Borrowed from
https://forum.digikey.com/t/getting-started-with-the-ti-awr1642-mmwave-sensor/13445

Using this to connect to the Ti mmWave Module and retrieve the data
"""

import struct
import time
from multiprocessing import Queue
from threading import Thread

import serial

from Frame import Frame


class SerialInterface:
    def __init__(self, user_port, data_port, frame_type):
        self.control_uart = serial.Serial(user_port, 115200)
        self.data_uart = serial.Serial(data_port, 921600)
        self.frame_type = frame_type

        self.uarts_enable = False

        # Use Queues to transfer data between processes
        self.control_tx_queue = Queue()
        self.control_rx_queue = Queue()
        self.data_tx_queue = Queue()
        self.data_rx_queue = Queue()

        # Spawn processes to handle serial data transfer in the background
        self.control_process = Thread(target=self.process_control_uart)
        self.data_process = Thread(target=self.process_data_uart)

    def process_control_uart(self):
        while self.uarts_enable:
            self._read_serial_lines(self.control_uart, self.control_rx_queue)
            self._write_serial(self.control_uart, self.control_tx_queue)

            # Sleep briefly to allow other threads to run and data to arrive
            time.sleep(0.001)

    def process_data_uart(self):
        while self.uarts_enable:
            self._read_serial_frames(self.data_uart, self.data_rx_queue, self.frame_type)
            self._write_serial(self.data_uart, self.data_tx_queue)

            # Sleep briefly to allow other threads to run and data to arrive
            time.sleep(0.001)

    @staticmethod
    def _read_serial_lines(ser_inst, rx_q):
        # Read a byte at a time until a \n is reached
        byte_data = b''
        while ser_inst.in_waiting:
            byte = ser_inst.read(1)
            byte_data += byte
            if byte == '\n'.encode():
                break

        if byte_data:
            data = byte_data.decode()
            rx_q.put(data)

    @staticmethod
    def _read_serial_frames(ser_inst, rx_q, frame_type):
        data = b''
        bytes_read = 0
        sync = False
        while ser_inst.in_waiting:
            byte = ser_inst.read(1)
            data += byte

            if not sync and Frame.FRAME_START in data:
                # Start of frame found, discard extra data
                sync = True
                sync_data = data[data.find(Frame.FRAME_START):]
                bytes_read += len(Frame.FRAME_START)

                # Read bytes until the packet length is received
                length_data = ser_inst.read(frame_type.PACKET_LENGTH_END - len(Frame.FRAME_START))
                bytes_read += len(length_data)
                packet_length = struct.unpack('<I', length_data[-4:])[0]
                if packet_length > 5000:
                    print("Packet length is {} which seems too large.  Skipping...".format(packet_length))
                    break

                # Read remaining bytes specified by the header
                remaining_data = ser_inst.read(packet_length - bytes_read)

                full_frame = sync_data + length_data + remaining_data

                rx_q.put(full_frame)

    @staticmethod
    def _write_serial(ser_inst, tx_q):
        if not tx_q.empty():
            data = tx_q.get()
            data = data.encode()

            ser_inst.write(data)

    @staticmethod
    def send_item(tx_q, data):
        # Send one item (typically a line ending in '\n') to the tx buffer
        tx_q.put(data)

    @staticmethod
    def recv_item(rx_q):
        # Fetch one line or frame from the rx buffer
        return rx_q.get() if not rx_q.empty() else None

    def start(self):
        self.uarts_enable = True

        self.control_process.start()
        self.data_process.start()

    def stop(self):
        self.uarts_enable = False

        self.control_process.join()
        self.data_process.join()
