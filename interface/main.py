import colour
import sys
from protocol import *
from serial import Serial


port = Serial(sys.argv[1], 115200, timeout=0.1)
buffer = b""


def send_message(type, data=b""):
    port.write(build_message(type, data))


def read_message(message_type=None):
    global buffer

    while True:
        (buffer, messages) = parse_messages(buffer + port.read())

        if messages:
            message = messages[0]

            if message_type and message["message_type"] != message_type:
                raise ValueError("Unexpected message type")

            return message


send_message(MessageType.GET_DEVICE_ID, b"\x18")
response = read_message(MessageType.GET_DEVICE_ID)
print("Device ID: " + response["device_id"])

send_message(MessageType.GET_RANGE)
response = read_message(MessageType.GET_RANGE)
start_wavelength = response["start_wavelength"]
print("Start wavelength: " + str(start_wavelength) + " nm")
print("End wavelength: " + str(response["end_wavelength"]) + " nm")

send_message(MessageType.GET_EXPOSURE_MODE)
response = read_message(MessageType.GET_EXPOSURE_MODE)
print("Exposure mode: " + response["exposure_mode"].name)

send_message(MessageType.GET_DATA)

while True:
    response = read_message()

    if response["exposure_status"] == ExposureStatus.NORMAL:
        print("Exposure time: " + str(response["exposure_time"]) + " ms")
        break

send_message(MessageType.STOP)

while read_message()["message_type"] != MessageType.STOP:
    pass

spectral_distribution = colour.SpectralDistribution(
    {
        start_wavelength + index: value
        for index, value in enumerate(response["spectrum"])
    }
)

colour.plotting.plot_single_sd(spectral_distribution)
