import struct
from enum import Enum


class MessageType(Enum):
    STOP = 0x04
    GET_DEVICE_ID = 0x08
    GET_EXPOSURE_MODE = 0x0B
    GET_RANGE = 0x0F
    GET_DATA = 0x33


class ExposureMode(Enum):
    MANUAL = 0x00
    AUTOMATIC = 0x01


class ExposureStatus(Enum):
    NORMAL = 0x00
    OVER = 0x01
    UNDER = 0x02


def decode_spectrum(encoded_spectrum, encoded_exponent, exposure_time, sn, ex_info):
    exposure_time_bytes = struct.pack("<f", exposure_time)
    exposure_time = int.from_bytes(exposure_time_bytes, "little")

    common = int.from_bytes(exposure_time_bytes, "big") ^ ex_info >> 16
    key_a = (common ^ (exposure_time ^ sn) >> 16 ^ sn ^ ex_info) & 0xFFFF
    key_b = (common >> 16 ^ exposure_time ^ sn) & 0xFFFF

    exponent = struct.unpack(">H", struct.pack("<H", encoded_exponent))[0] ^ 8848
    scale = pow(10, exponent)

    midpoint = len(encoded_spectrum) // 2

    return [
        (item ^ (key_a if index < midpoint else key_b)) / scale
        for index, item in enumerate(encoded_spectrum)
    ]


def calculate_checksum(message):
    return sum(message) & 0xFF


def build_message(message_type, data):
    message = b"\xCC\x01"
    message += int.to_bytes(9 + len(data), 3, "little")
    message += int.to_bytes(message_type.value, 1, "little")
    message += data
    message += int.to_bytes(calculate_checksum(message), 1, "little")
    message += b"\x0D\x0A"

    return message


def parse_message(message_type, data):
    message = {"message_type": message_type}

    match message_type:
        case MessageType.GET_DEVICE_ID:
            message["device_id"] = data.decode("ascii")

        case MessageType.GET_EXPOSURE_MODE:
            message["exposure_mode"] = ExposureMode(data[0])

        case MessageType.GET_RANGE:
            message["start_wavelength"], message["end_wavelength"] = struct.unpack(
                "<HH", data
            )

        case MessageType.GET_DATA:
            (
                exposure_status_code,
                exposure_time_microseconds,
                encoded_exponent,
                sn,
                ex_info,
            ) = struct.unpack_from("<BIHIQ", data)

            encoded_spectrum = [item[0] for item in struct.iter_unpack("<H", data[19:])]

            message["exposure_status"] = ExposureStatus(exposure_status_code)
            message["exposure_time"] = exposure_time_microseconds / 1000
            message["spectrum"] = decode_spectrum(
                encoded_spectrum,
                encoded_exponent,
                message["exposure_time"],
                sn,
                ex_info,
            )

    return message


def parse_messages(data):
    messages = []

    while len(data) >= 5:
        if not data.startswith(b"\xCC\x81"):
            raise ValueError("Invalid start bytes")

        length = int.from_bytes(data[2:5], "little")

        if len(data) < length:
            break

        if calculate_checksum(data[: length - 3]) != data[length - 3]:
            raise ValueError("Invalid checksum")

        if data[length - 2 : length] != b"\x0D\x0A":
            raise ValueError("Invalid end bytes")

        messages.append(parse_message(MessageType(data[5]), data[6 : 6 + length - 9]))
        data = data[length:]

    return (data, messages)
