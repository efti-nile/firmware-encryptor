#!/usr/bin/python3
# encoding=UTF-8
from crc8dallas import crc8
from progbar import ProgBar
import serial
import sys


class LinbootFlasher(serial.Serial):
    cmd_opcodes = {"version": b'\x01', "init cipher": b'\x02', "write page": b'\x03', "keep alive": b'\x06',
                   "commit flash": b'\x07'}
    message_header_len = 3
    message_max_len = 148
    mask_header_error = False

    def __init__(self, *args, framesize=144):
        try:
            self.lin_rx_timeout = 0.7
            super().__init__(*args, timeout=self.lin_rx_timeout)
        except serial.serialutil.SerialException:
            sys.stdout.write("Specified COM not found\n")
            raise
        self.framesize = framesize
        self.lin_address = None

    def set_lin_address(self, lin_address):
        if lin_address <= 0 or lin_address > 255:
            sys.stdout.write("Specified LIN-address {0} incorrect\n".format(hex(lin_address)) +
                             "Must be less than 256 and grater than 0\n")
            raise ValueError()
        self.lin_address = bytes([lin_address])

    def catch_linboot(self, timeout=60):
        self.mask_header_error = True
        pb = ProgBar(' Waiting bootloader ')
        for t in range(round(timeout / self.lin_rx_timeout)):
            try:
                if self.__command(self.cmd_opcodes["keep alive"]) is not None:
                    pb.close()
                    sys.stdout.write("[INFO   ] Bootloader connected\n")
                    self.mask_header_error = False
                    return True
            except RuntimeError:
                pass
            pb.update(t / (timeout / self.lin_rx_timeout))
        pb.close()
        self.mask_header_error = False
        sys.stdout.write("[ERROR  ] Timeout elapsed\n")
        return False

    def flash(self, fw_binfile):
        with open(fw_binfile, "rb") as fw:
            fw_image = fw.read()
        if len(fw_image) % self.framesize != 0:
            sys.stdout.write("[ERROR  ] Incorrect encrypted hex\n")
            raise RuntimeError()
        num_frames = len(fw_image) // self.framesize
        if not self.catch_linboot():
            return
        if self.__command(self.cmd_opcodes["init cipher"]) is None:
            sys.stdout.write("[ERROR  ] Cypher not initialized\n")
            raise RuntimeError()
        pb = ProgBar(' Loading {0} flash pages '.format(num_frames))
        for frame, frame_no in ((fw_image[i*self.framesize:(i+1)*self.framesize], i) for i in range(num_frames)):
            pb.update(frame_no / num_frames)
            if self.__command(self.cmd_opcodes["write page"], frame) is None:
                sys.stdout.write("[ERROR  ] Writing page #{0}: ACK not got\n".format(frame_no))
                raise RuntimeError()
        pb.close()
        pb = ProgBar(' Waiting firmware acknowledgment ')
        self.mask_header_error = True
        timeout = 10
        for t in range(round(timeout / self.lin_rx_timeout)):
            try:
                if self.__command(self.cmd_opcodes["commit flash"]) is not None:
                    pb.close()
                    sys.stdout.write("[INFO   ] Firmware is correct\n")
                    self.mask_header_error = False
                    return True
            except RuntimeError:
                pass
            pb.update(t / (timeout / self.lin_rx_timeout))
        pb.close()
        self.mask_header_error = False
        sys.stdout.write("[ERROR  ] No acknowledgment\n".format(frame_no))

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
        if False:
            if not hasattr(self, 'once'):
                sys.stdout.write("[NOTE   ] Echo-bytes skipping is disabled")
                self.once = True
        else:
            self.read(len(message))  # skip echoed bytes (bytes echo because-of LIN)

    def __receive_answer(self, expected_opcode, expected_datalen=None):
        assert isinstance(expected_opcode, bytes) and len(expected_opcode) == 1
        if expected_datalen is not None:
            assert isinstance(expected_datalen, int)
            bytes_to_receive = self.message_header_len + self.expected_datalen + 1  # + 1 byte CRC8
        else:
            bytes_to_receive = self.message_max_len
        answer = self.read(bytes_to_receive)
        if len(answer) < self.message_header_len:
            if not self.mask_header_error:  # mask error if we only need to probe the bootloader, not to communicate
                sys.stdout.write("[ERROR  ] Message header not got\n")
            raise RuntimeError()
        datalen = answer[1]
        answer = answer[:self.message_header_len + datalen + 1]
        if crc8(answer[:-1]) != answer[-1]:
            sys.stdout.write("[ERROR  ] Incorrect message CRC\n")
            raise RuntimeError()
        lin_add = answer[0]
        if lin_add != ord(self.lin_address):
            sys.stdout.write("[ERROR  ] Unexpected LIN-address: {0}\n".format(lin_add))
            raise RuntimeError()
        if expected_datalen is not None and datalen != expected_datalen:
            sys.stdout.write("[ERROR  ] Unexpected message length: {0}\n".format(datalen))
            raise RuntimeError()
        opcode = answer[2]
        if opcode != ord(expected_opcode):
            if not self.mask_header_error:  # mask error if we only need to probe the bootloader, not to communicate
                sys.stdout.write("[ERROR  ] Unexpected opcode: {0}\n".format(opcode))
            raise RuntimeError()
        return answer[self.message_header_len:self.message_header_len + datalen].decode('utf-8', 'ignore')
