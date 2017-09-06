#!/usr/bin/python3
# encoding=UTF-8
from crc8dallas import crc8
import tqdm  # progressbar
import serial
import time
import sys


class LinbootFlasher(serial.Serial):
    cmd_opcodes = {"version": b'\x01', "write_page": b'\x02', "init_cipher": b'\x03'}
    ans_opcodes = {"cipher_initialized": b'\x01'}
    version_string_maxlen = 64
    answer_header_len = 3
    command_header_len = 3

    def __init__(self, *args, framesize=144):
        super().__init__(*args, timeout=1)
        self.framesize = framesize
        self.lin_address = None
        pass

    def set_lin_address(self, lin_address):
        if lin_address <= 0 or lin_address > 255:
            raise ValueError("Specified LIN-address {0} incorrect. ".format(lin_address) +
                             "Must be less than 256 and grater than 0")
        self.lin_address = bytes([lin_address])

    def flash(self, fw_binfile):
        with open(fw_binfile, "rb") as fw:
            fw_image = fw.readall()
        if (len(fw_image) - 4) % self.framesize != 0:
            raise ValueError("Incorrect length of firmware binary file")
        self.__send_message(self.cmd_opcodes["init_cipher"])
        ans = self.read(4)
        if len(ans < 4) or ans[2] != self.ans_opcodes["cipher_initialized"] or ans[3] != crc8(ans[:-1]):
            sys.stderr.write("[ERROR  ] No ACK after cipher initialization {0}\n")
            return False
        for frame, frame_no in (fw_image[i*self.framesize:(i+1)*self.framesize], i
                                for i in range(len(fw_image)//self.framesize)):
            self.__send_message(self.cmd_opcodes["write_page"], frame)
            ans = self.read(2)
            if len(ans) < 2:
                sys.stderr.write("[ERROR  ] No ACK while flashing frame no. {0}\n".format(frame_no))

    def version(self):
        self.__send_message(self.cmd_opcodes["version"])
        ans = self.read(self.version_string_maxlen)
        datalen = ans[0]
        if len(ans) < 4 or crc8(version_string[:-1]) != version_string[-1]:
            sys.stderr.write("[ERROR  ] No answer on version string request")
            return ""
        if crc8
        return version_string.decode("utf-8", "ignore")

    def __send_message(self, opcode, data=b''):
        assert isinstance(self.lin_address, bytes) and len(self.lin_address) == 1
        assert isinstance(data, bytes) and len(data) < 256
        assert isinstance(opcode, bytes) and len(opcode) == 1
        message_header = self.lin_address + bytes([len(data)]) + opcode
        message = message_header + data
        message += bytes([crc8(message)])
        self.write(message)
        # self.read(len(message))  # skip echoed bytes (bytes echo because-of LIN)

    def __receive_answer(self, opcode, expected_datalen=0):
        bytes_to_receive = self.command_header_len + self.expected_datalen + 1
        answer = self.read(bytes_to_receive)
        if len(answer) < bytes_to_receive:
            sys.stderr.write("[ERROR  ] Received less than expected\n")
            return None
        if bytes([crc8(answer[:-1])]) != answer[-1]:
            sys.stderr.write("[ERROR  ] CRC check failed\n")
            return None
        return answer[self.command_header_len:self.command_header_len+]

