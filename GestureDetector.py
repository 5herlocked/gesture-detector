import signal
import struct
import time
from collections import deque

import numpy as np

from datetime import datetime
from pynput.mouse import Button, Controller
from threading import Thread

from Frame import Frame, RadarFrameHeader, FrameError
from SerialInterface import SerialInterface

GESTURES = {
    -1: 'ambiguous',
    0: 'rtl',
    1: 'ltr',
    2: 'utd',
    3: 'dtu'
}


def kill_all():
    # global compute_thread
    # if compute_thread is not None:
    #     compute_thread.join()

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
    # 10fps, data queue is 15 seconds long
    radar_data_queue = deque(maxlen=150)

    compute_thread = Thread(target=process_frames, args=[radar_data_queue])
    compute_thread.start()

    pass


def process_frames():
    global interface

    interface.start()

    with open('profile.cfg') as f:
        print("Sending Configuration...")
        for line in f.readlines():
            if line.startswith('%'):
                # ignore comments
                continue
            else:
                print(line)
                interface.send_item(interface.control_tx_queue, line)
            time.sleep(0.2)

    while not kill:
        serial_frame = interface.recv_item(interface.data_rx_queue)
        if serial_frame:
            try:
                frame = Frame(serial_frame, frame_type=interface.frame_type)

                if len(frame.tlvs) > 0:
                    # has valid objects in it
                    # first approach is a manually created decision tree
                    # updated approach is planned to be a Random Forest Classifier
                    gestures = {}
                    for tlv in frame.tlvs:
                        for tracked_objs in tlv.objects:
                            # print(tracked_objs.vX)
                            # print(tracked_objs.vY)
                            # print(tracked_objs.vZ)
                            # print('==============================')
                            # object is moving left and has more horizontal inertia
                            if tracked_objs.vX > 0.1 and abs(tracked_objs.vX) > abs(tracked_objs.vZ) and abs(
                                    tracked_objs.aX) > abs(tracked_objs.aY) and abs(tracked_objs.aX) > abs(
                                    tracked_objs.aZ):
                                gestures[GESTURES[0]] = gestures.get(GESTURES[0], 0) + 1
                            # object is moving right and has more horizontal inertia than vertical
                            elif tracked_objs.vX < -0.1 and abs(tracked_objs.vX) > abs(tracked_objs.vZ) and abs(
                                    tracked_objs.aX) > abs(tracked_objs.aY) and abs(tracked_objs.aX) > abs(
                                    tracked_objs.aZ):
                                gestures[GESTURES[1]] = gestures.get(GESTURES[1], 0) + 1
                            # elif tracked_objs.vY > 0.1 and abs(tracked_objs.vY) > abs(tracked_objs.vX) and abs(
                            #         tracked_objs.aY) > abs(tracked_objs.aX) and abs(tracked_objs.aY) > abs(
                            #         tracked_objs.aZ):
                            #     gestures[GESTURES[2]] = gestures.get(GESTURES[2], 0) + 1
                            # elif tracked_objs.vY < -0.1 and abs(tracked_objs.vY) > abs(tracked_objs.vX) and abs(
                            #         tracked_objs.aY) > abs(tracked_objs.aX) and abs(tracked_objs.aY) > abs(
                            #         tracked_objs.aZ):
                            #     gestures[GESTURES[3]] = gestures.get(GESTURES[3], 0) + 1
                    if len(gestures) > 0:
                        prevalent_gesture = max(gestures)
                        if prevalent_gesture is not None:
                            print(prevalent_gesture)
                        else:
                            print('none')
            except FrameError as e:
                print(e)


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
    # compute_thread = None
    # run_interface()
    process_frames()
