#!/usr/bin/python3
# encoding=UTF-8
from crc8dallas import crc8
import tqdm  # progressbar
import serial
import time
import sys


class LinbootFlasher(serial.Serial):
    cmd_opcodes = {"version": b'\x01', "init cypher": b'\x02', "write page": b'\x03'}
    message_header_len = 3

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
        if len(fw_image) % self.framesize != 0:
            sys.stderr.write("[ERROR  ] Invalid firmware binary file\n")
            return
        if self.__command(self.cmd_opcodes["init cipher"]) is None:
            sys.stderr.write("[ERROR  ] No cipher initialization ACK\n")
            return
        for frame, frame_no in tqdm((fw_image[i*self.framesize:(i+1)*self.framesize], i
                                     for i in range(len(fw_image)//self.framesize))):
            if self.__command(self.cmd_opcodes["write page"], frame):
                sys.stderr.write("[ERROR  ] No written flash page ACK. Page No. {0}\n".format(frame_no))
                return

    def version(self):
        return self.__command(self.cmd_opcodes["version"])

    def __command(self, opcode, data=b'', expected_answer_datalen=None):
        self.__send_message(opcode, data)
        return self.__receive_answer(opcode, expected_answer_datalen)

    def __send_message(self, opcode, data):
        assert isinstance(self.lin_address, bytes) and len(self.lin_address) == 1
        assert isinstance(data, bytes) and len(data) < 256
        assert isinstance(opcode, bytes) and len(opcode) == 1
        message_header = self.lin_address + bytes([len(data)]) + opcode
        message = message_header + data
        message += bytes([crc8(message)])
        self.write(message)
        self.read(len(message))  # skip echoed bytes (bytes echo because-of LIN)

    def __receive_answer(self, expected_opcode, expected_datalen=None):
        assert isinstance(expected_opcode, bytes) and len(opcode) == 1
        if expected_datalen is not None:
            bytes_to_receive = self.command_header_len + self.expected_datalen + 1
        else:
            bytes_to_receive = self.answer_maxlen
        answer = self.read(bytes_to_receive)
        if len(answer) < self.answer_header_len:
            sys.stderr.write("[ERROR  ] Header not received\n")
            return None
        datalen = ord(answer[0])
        answer = answer[:self.command_header_len + datalen]
        if crc8(answer[:-1]) != ord(answer[-1]):
            sys.stderr.write("[ERROR  ] CRC check failed\n")
            return None
        if expected_datalen is not None and datalen != expected_datalen:
            sys.stderr.write("[ERROR  ] Met not expected data length: {0}\n".format(datalen))
            return None
        opcode = answer[1]
        if opcode != expected_opcode:
            sys.stderr.write("[ERROR  ] Met not expected opcode: {0}\n".format(opcode))
            return None
        return answer[self.command_header_len:self.command_header_len + datalen]
