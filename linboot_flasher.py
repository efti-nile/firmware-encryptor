#!/usr/bin/python3
# encoding=UTF-8
from crc8dallas import crc8
import tqdm  # progressbar
import serial
import time
import sys


class LinbootFlasher(serial.Serial):
    opcodes = {"version": 0x01, "write_page": 0x02, "init_cipher": 0x03}
    version_string_maxlen = 16

    def __init__(self, *kwargs, framesize=272):
        super().__init__()
        self.framesize = framesize
        pass

    def flash(self, fw_binfile):
        frame_cnt = 0
        with open(fw_binfile, "rb") as fw:
            while True:
                frame = fw.read(self.framesize)
                if frame:
                    frame_cnt += 1
                    self.__send_message(self.opcodes["write_page"] + frame)
                    ans = self.read(2)  # try receive acknowledgment
                    if crc8(ans[0]) != ans[1]:
                        sys.stderr.write("[ERROR  ] No ACK while flashing frame no. {0}".format(frame_cnt))
                        return False
                else:
                    break
        return True

    def version(self):
        self.__send_message(self.opcodes["version"])
        time.sleep(0.1)
        version_string = self.read(self.version_string_maxlen)
        if crc8(version_string[:-1]) != version_string[-1]:
            sys.stderr.write("[ERROR  ] No answer on version string request")
            return None
        return version_string.decode("utf-8", "ignore")

    def __send_message(self, message):
        message += crc8(message)
        self.write(message)
        self.read(len(message))  # skip echoed bytes (bytes echo because-of LIN)
