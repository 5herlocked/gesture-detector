import pickle
import struct
import time
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from threading import Thread

from Frame import Frame, RadarFrameHeader, FrameError
from Listener import Listener
from Recorder import DataRecorder
from SerialInterface import SerialInterface

"""
rtl ltr utd dtu 
[
    0, 0, 0
    0, 0, 0
    0, 0, 0
    ] x 1 sec - 100 samples
    
    Dict(): key: [3x3xn]
    
    dict.value()
    dict.keys()
    fit (dict.values(), dict.keys())
"""

"""
Intuition:
interactive recording script that lets me label data as I record it
put data + label into Random Forest
once all the data is put in the Forest
Pickle Forest

Use this for structure
https://stackoverflow.com/questions/62520952/how-to-record-audio-each-time-user-presses-a-key
"""


def run_trainer():
    keys = []
    converted_data = []

    done_recording = 'y'

    while done_recording.lower() == 'y':
        data_class = input('What do you want the gesture to be called?: ')
        data_recorder = DataRecorder(interface)
        ui_manager = Listener(data_recorder)

        ui_manager.start()
        ui_manager.join()
        keys.append(data_class)
        converted_data.append(data_recorder.frames)
        done_recording = input('Do you want to train more gestures? [Y/n]: ')

    classifier.fit(converted_data, keys)

    with open('random_forest.pkl', 'rb+') as file:
        pickle.dump(classifier, file)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run mmWave record of the data received')
    parser.add_help = True
    parser.add_argument('--control_port', help='COM port for configuration, control')
    parser.add_argument('--data_port', help='COM port for radar data transfer')
    parser.add_argument('--retrain', help='Deletes existing model if found', action='store_true')

    args = parser.parse_args()

    # Program Globals
    interface = SerialInterface(args.control_port, args.data_port, frame_type=RadarFrameHeader)

    stop_recording = False
    classifier = RandomForestClassifier()
    run_trainer()
