#!/usr/bin/python3
# encoding=UTF-8
from crc8dallas import crc8
from progbar import ProgBar
import serial
import sys


class LinbootFlasher(serial.Serial):
    cmd_opcodes = {"version": b'\x01', "init cipher": b'\x02', "write page": b'\x03'}
    message_header_len = 3
    message_max_len = 148

    def __init__(self, *args, framesize=144):
        try:
            super().__init__(*args, timeout=1)
        except serial.serialutil.SerialException:
            sys.stdout.write("Не удалось открыть указанный COM-порт\n")
            raise
        self.framesize = framesize
        self.lin_address = None

    def set_lin_address(self, lin_address):
        if lin_address <= 0 or lin_address > 255:
            sys.stdout.write("Указанный LIN-адрес {0} некорректен\n".format(hex(lin_address)) +
                             "Должен быть меньше 256 и больше 0\n")
            raise ValueError()
        self.lin_address = bytes([lin_address])

    def flash(self, fw_binfile):
        with open(fw_binfile, "rb") as fw:
            fw_image = fw.read()
        if len(fw_image) % self.framesize != 0:
            sys.stdout.write("[ERROR  ] Некооректный шифр-образ прошивки\n")
            raise RuntimeError()
        num_frames = len(fw_image) // self.framesize
        if self.__command(self.cmd_opcodes["init cipher"]) is None:
            sys.stdout.write("[ERROR  ] Нет подтверждения начала сеанса\n")
            raise RuntimeError()
        pb = ProgBar(' Загрузка {0} страниц флеш-памяти '.format(num_frames))
        for frame, frame_no in ((fw_image[i*self.framesize:(i+1)*self.framesize], i) for i in range(num_frames)):
            pb.update(frame_no / num_frames)
            if self.__command(self.cmd_opcodes["write page"], frame) is None:
                sys.stdout.write("[ERROR  ] Не получено подтверждение записи страницы №{0}\n".format(frame_no))
                raise RuntimeError()
        pb.close()
        sys.stdout.write("[INFO   ] Готово\n")

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
                sys.stdout.write("[NOTE   ] Пропуск эхо-байт отключен")
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
            sys.stdout.write("[ERROR  ] Заголовок пакета не получен\n")
            raise RuntimeError()
        datalen = answer[1]
        answer = answer[:self.message_header_len + datalen + 1]
        if crc8(answer[:-1]) != answer[-1]:
            sys.stdout.write("[ERROR  ] Проверка CRC провалена\n")
            raise RuntimeError()
        lin_add = answer[0]
        if lin_add != ord(self.lin_address):
            sys.stdout.write("[ERROR  ] Получен пакет с неожиданного LIN-адреса: {0}\n".format(lin_add))
            raise RuntimeError()
        if expected_datalen is not None and datalen != expected_datalen:
            sys.stdout.write("[ERROR  ] Получен пакет с неожиданной длинной: {0}\n".format(datalen))
            raise RuntimeError()
        opcode = answer[2]
        if opcode != ord(expected_opcode):
            sys.stdout.write("[ERROR  ] Получен пакет с неожиданным опкодом: {0}\n".format(opcode))
            raise RuntimeError()
        return answer[self.message_header_len:self.message_header_len + datalen].decode('utf-8', 'ignore')
