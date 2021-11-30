import signal
import struct
import time
from collections import deque

import numpy as np

from datetime import datetime
from multiprocessing import Queue
from pynput.mouse import Button, Controller
from threading import Thread

from Frame import Frame, RadarFrameHeader, FrameError
from SerialInterface import SerialInterface


def kill_all():
    global compute_thread
    if compute_thread is not None:
        compute_thread.join()

    print("Shutting down...")
    interface.send_item(interface.control_tx_queue, 'sensorStop\n')
    time.sleep(2)
    interface.stop()


def interrupt_handler(sig, frame):
    global kill, interface
    kill = True
    kill_all()
    pass


def run_interface():
    global compute_thread, kill

    mouse = Controller()
    radar_data_queue = deque(maxlen=150)

    compute_thread = Thread(target=process_frames, args=[radar_data_queue])
    compute_thread.start()

    pass


def process_frames(data_queue=None):
    global interface

    interface.start()

    while not kill:
        serial_frame = interface.recv_item(interface.data_rx_queue)
        if serial_frame:
            try:
                frame = Frame(serial_frame, frame_type=interface.frame_type)

    pass


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run the gesture detection application')
    parser.add_help = True
    parser.add_argument('--control_port', help='COM port for configuration, control')
    parser.add_argument('--data_port', help='COM port for radar data transfer')
    args = parser.parse_args()

    # Program Globals
    interface = SerialInterface(args.control_port, args.data_port, frame_type=RadarFrameHeader)

    signal.signal(signal.SIGINT, interrupt_handler)
    kill = False
    compute_thread = Thread()
    run_interface()
