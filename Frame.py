"""
Borrowed from
https://forum.digikey.com/t/getting-started-with-the-ti-awr1642-mmwave-sensor/13445

Using this to establish the general structure of the Packets received from the mmWave radar chip
"""
import struct


class FrameError(Exception):
    def __init__(self, value):
        self.value = value


class TLVData:
    def __init__(self, serial_tlv):
        pass

    @staticmethod
    def preparsing(serial_tlv):
        # Extra data frame outside regular objects
        return None, serial_tlv

    def __str__(self):
        result = ''
        for key in self.__dict__.keys():
            result += '{}: {}\n'.format(key, self.__dict__[key])

        return result


class TargetObjects(TLVData):
    NAME = 'TARGET_OBJECTS'
    SIZE_BYTES = 40

    def __init__(self, serial_tlv):
        super(TargetObjects, self).__init__(serial_tlv)

        # unpack as defined by https://docs.python.org/3/library/struct.html
        elements = struct.unpack('<Ifffffffff', serial_tlv)
        self.id = elements[0]
        self.x = elements[1]
        self.y = elements[2]
        self.vX = elements[3]
        self.vY = elements[4]
        self.aX = elements[5]
        self.aY = elements[6]
        self.z = elements[7]
        self.vZ = elements[8]
        self.aZ = elements[9]


class TLVHeader:
    SIZE_BYTES = 8

    def __init__(self, serial_tlv_header):
        elements = struct.unpack('<II', serial_tlv_header)
        self.type = elements[0]
        self.length = elements[1]

    def __str__(self):
        result = 'TLV Header'
        for key in self.__dict__.keys():
            result += '{}: {}'.format(key, self.__dict__[key])

        return result


# My code doesn't really use these so we can drop them
class PointCloudSpherical:
    NAME = 'POINT_CLOUD_SPHERICAL'
    pass


class TargetIndices:
    NAME = 'TARGET_OBJECT_INDICES'
    pass


class PointCloudSide:
    NAME = 'SIDE_INFO_FOR_POINT_CLOUD'
    pass


# As enumerated in Ti's recommended documentation
# https://dev.ti.com/tirex/explore/node?node=AJ6ZexoDiZnBLQ84ClQ-Tg__VLyFKFf__LATEST&resourceClasses=example
TLV_TYPES = {
    6: PointCloudSpherical,
    7: TargetObjects,
    8: TargetIndices,
    9: PointCloudSide
}


class TLV:
    def __init__(self, serial_tlv):
        self.header = TLVHeader(serial_tlv[0:TLVHeader.SIZE_BYTES])

        self.obj_class = TLV_TYPES[self.header.type]
        self.name = self.obj_class.NAME
        self.obj_size = self.obj_class.SIZE_BYTES
        tlv_sans_header = serial_tlv[TLVHeader.SIZE_BYTES:]
        self.descriptor, processed_tlv = self.obj_class.preparsing(tlv_sans_header)

        try:
            self.objects = self.parse_objects(processed_tlv)
        except struct.error as e:
            print('Exception while parsing TLV objects: ', e)
            self.objects = []

    def parse_objects(self, processed_tlv):
        objects = []
        num_objects = int(self.header.length / self.obj_size)
        for i in range(0, num_objects):
            new = self.obj_class(processed_tlv[0:self.obj_size])
            objects.append(new)
            processed_tlv = processed_tlv[self.obj_size:]

        return objects


class FrameHeader:
    def __init__(self, serial_header):
        self.full_header = serial_header

    def __str__(self):
        result = 'Frame Header:\n'
        for key in self.__dict__.keys():
            result += '{}: {}\n'.format(key, self.__dict__[key])

        return result

    def verify_checksum(self):
        pass


class RadarFrameHeader(FrameHeader):
    SIZE_BYTES = 52
    PACKET_LENGTH_END = 24

    def __init__(self, serial_header):
        super(RadarFrameHeader, self).__init__(serial_header)
        self.sync = serial_header[0:8]
        self.version = serial_header[8:12]
        self.platform = serial_header[12:16]
        self.numDetectedObj = struct.unpack('<I', serial_header[16:20])[0]
        self.packetLen = struct.unpack('<I', serial_header[20:24])[0]

        values = struct.unpack('<6I', serial_header[24:48])
        self.frameNum = values[0]
        self.subFrameNum = values[1]
        self.chirpMargin = values[2]
        self.frameMargin = values[3]
        self.trackTime = values[4]
        self.uartTime = values[5]

        self.numTLVs = struct.unpack('<H', serial_header[48:50])[0]
        self.checksum = struct.unpack('<H', serial_header[50:52])[0]


class Frame:
    FRAME_START = b'\x02\x01\x04\x03\x06\x05\x08\x07'

    def __init__(self, serial_frame, frame_type):
        # Parse serial data into header and TLVs
        # Note that frames are LITTLE ENDIAN

        # Length should be > header_size
        frame_length = len(serial_frame)
        if frame_length < frame_type.SIZE_BYTES:
            raise FrameError('Frame is smaller than required header size. '
                             'Expected length {}. Measured length {}.'.format(frame_type.SIZE_BYTES, frame_length))

        # Initialize the header
        self.header = frame_type(serial_frame[0:frame_type.SIZE_BYTES])

        # Second sanity check
        if frame_length < self.header.packetLen:
            raise FrameError('Frame is too small. Expected {} bytes, '
                             'receieved {} bytes.'.format(self.header.packetLength, frame_length))

        # Convert remaining data into TLVs
        full_tlv_data = serial_frame[frame_type.SIZE_BYTES:]
        tlv_data = full_tlv_data
        self.tlvs = []
        for i in range(self.header.numTLVs):
            # Check header to get length of each TLV
            length = TLVHeader.SIZE_BYTES + TLVHeader(tlv_data[0:TLVHeader.SIZE_BYTES]).length
            # Create a 'length' bytes TLV instance
            new_tlv = TLV(tlv_data[0:length])
            self.tlvs.append(new_tlv)

            # Slice off the consumed TLV data
            tlv_data = tlv_data[length:]

    def __str__(self):
        # Print header followed by TLVs
        result = ""
        result += str(self.header)
        result += 'TLVs: {\n'
        for each in self.tlvs:
            result += str(each)
        result += '}\n'
        return result
