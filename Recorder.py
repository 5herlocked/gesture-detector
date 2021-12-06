import struct
import time
from threading import Thread

from Frame import Frame, FrameError


class DataRecorder:
    def __init__(self, serial_interface):
        self.frames = list()
        self.recording = False
        self.serial_interface = serial_interface
        self.recorder_thread = Thread(target=self.record)

    def record(self):
        while self.recording:
            serial_frame = self.serial_interface.recv_item(self.serial_interface.data_rx_queue)
            if serial_frame:
                try:
                    new_frame = Frame(serial_frame, self.serial_interface.frame_type)
                    self.frames.append(new_frame)

                except (KeyError, struct.error, IndexError, FrameError, OverflowError) as e:
                    # Some data got in the wrong place, just skip the frame
                    print('Exception occurred: ', e)
                    print("Skipping frame due to error...")

            time.sleep(0.001)

    def start(self):
        if not self.recording:
            self.recording = True

            self.serial_interface.start()

            with open('profile.cfg') as f:
                print("Sending Configuration...")
                for line in f.readlines():
                    if line.startswith('%'):
                        # ignore comments
                        continue
                    else:
                        print(line)
                        self.serial_interface.send_item(self.serial_interface.control_tx_queue, line)
            self.recorder_thread.start()

    def stop(self):
        if self.recording:
            self.recording = False

            self.recorder_thread.join()
            self.serial_interface.stop()
