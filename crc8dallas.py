# coding=UTF-8
def crc8(_bytes):
    if not isinstance(_bytes, (bytes, bytearray)):
        raise TypeError("object supporting the buffer API required")
    crc = 0
    for b in _bytes:
        if b < 0:
            b += 256
        for i in range(8):
            odd = ((b ^ crc) & 1) == 1
            crc >>= 1
            b >>= 1
            if odd:
                crc ^= 0x8C
    return crc
