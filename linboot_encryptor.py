#!/usr/bin/python3
# encoding=UTF-8
from pyserpent import Serpent
from os import urandom
from binascii import crc32
from progbar import ProgBar  # progressbar
import sys  # stderr


class LinbootHexEncryptor(Serpent):
    """
    Encrypts intel hex-file with serpent in CBC mode.
    Initially developed for AVR firmware hex-files, with other MCU compatibility is unknown.
    Output binary file compatible with linboot-bootloader.
    """
    PAGE_SIZE = 128  # flash page size, must be multiple by cipher block size (!)
    FILLER = 0xFF  # value for padding unused flash
    FW_SIZE_ADD = 0xB6

    def __init__(self, key, ivc):
        """
        Initializes cipher
        :param key: 256-bit key
        :param ivc: 128-bit initial vector for CBC
        """
        Serpent.__init__(self, key)
        self.flash = {}
        self.ivc = ivc

    @staticmethod
    def block_xor(block1, block2):
        """ XORs two cipher block """
        assert len(block1) == Serpent.get_block_size() and len(block2) == len(block1)
        return bytes(block1[i] ^ block2[i] for i in range(Serpent.get_block_size()))

    @staticmethod
    def read_hexlines(input_stream, strict_check_sum=True):
        """
        Reads and parses all lines form hex file
        :param input_stream: hex-file
        :param strict_check_sum: is exception raised when line with incorrect check sum met
        :return: list of hexlines
        """
        hexlines = []
        while True:
            hexline = LinbootHexEncryptor.read_hexline(input_stream, strict_check_sum)
            if hexline is not None:
                hexlines.append(hexline)
            else:
                return hexlines

    @staticmethod
    def read_hexline(input_stream, strict_check_sum=True):
        """
        Reads and pareses line in intel hex format
        :param input_stream: hex-file
        :param strict_check_sum: is exception raised when line with incorrect check sum met
        :return: tokenized hex-record in dictionary or None if EOF met
        """
        line = input_stream.readline()
        if line:
            data_len = int(line[1:3], 16)
            address_msb, address_lsb = int(line[3:5], 16), int(line[5:7], 16)
            address = address_msb * 256 + address_lsb
            record_type = int(line[7:9], 16)
            data = bytes(int(line[9+i*2:11+i*2], 16) for i in range(data_len))
            check_sum = int(line[9+data_len*2:11+data_len*2], 16)
            check_sum_actual = (~((data_len+address_msb+address_lsb+record_type+sum(data)) & 0x00FF) + 1) & 0xFF
            if check_sum != check_sum_actual:
                if strict_check_sum:
                    sys.stdout.write("Неверная контрольная сумма в HEX-файле\nстрока: "
                                     "\"{0}\"\nпосчитанная контрольная сумма: {1}\n"
                                     "контрольная сумма в файле: {2}".format(line.strip(), check_sum_actual, check_sum))
                    raise ValueError()
                else:
                    sys.stdout.write("[WARNING] {0} "
                                     "Несоответсвие контрольной суммы!\n".format(hex(address)))
            return {"data_len": data_len, "address": address, "record_type": record_type, "data": data}
        else:
            return None  # EOF

    def flash_write(self, address, data):
        """
        Added bytes in flash buffer dealing with page structure
        :param address: absolute address
        :param data: bytes to write
        :return:
        """
        data_len = len(data)
        data = iter(data)
        begin_page_no = address // self.PAGE_SIZE
        end_page_no = (address + data_len - 1) // self.PAGE_SIZE
        for page_no in range(begin_page_no, end_page_no + 1):
            if page_no not in self.flash:
                self.flash[page_no] = bytearray(self.FILLER for _ in range(self.PAGE_SIZE))
            if page_no == begin_page_no:
                for offset in range(address % self.PAGE_SIZE,
                                    min((address + data_len - 1) % self.PAGE_SIZE + 1, self.PAGE_SIZE + 1)):
                    self.flash[page_no][offset] = next(data)
            elif page_no == end_page_no:
                for offset in range(0, (address + data_len) % self.PAGE_SIZE + 1):
                    self.flash[page_no][offset] = next(data)
            else:
                for offset in range(0, self.PAGE_SIZE + 1):
                    self.flash[page_no][offset] = next(data)

    def encrypt_hex(self, input_file_path, output_file_path):
        """
        Reads input hex-file and writes encrypted firmware in output binary file
        :param input_file_path: intel hex-file
        :param output_file_path: output binary file for encrypted firmware
        :return:
        """
        fw_size = 0;
        # read hex file
        with open(input_file_path, "r") as hexfile:
            for hexline in self.read_hexlines(hexfile):
                self.flash_write(hexline["address"], hexline["data"])
                if hexline["address"] + len(hexline["data"]) > fw_size:
                    fw_size = hexline["address"] + len(hexline["data"]) + 1
        if fw_size % 2 == 1:
            fw_size += 1
        # Программа ЦМСР по-своему определяет размер прошивки. Именно его и надо вбивать в исходный код приложения в
        # INFO-блок по адресу self.FW_SIZE_ADD. Поэтому строчка закомментирована.
        # self.flash_write(self.FW_SIZE_ADD, bytes([fw_size & 0xFF, fw_size >> 8 & 0xFF]))
        sys.stdout.write("[INFO   ] Размер прошивки в байтах: {0}\n".format(fw_size))
        # encrypt read pages and write them in binary file
        accum = self.ivc
        with open(output_file_path, "wb") as binfile:
            pb = ProgBar(" Шифрование {0} страниц флеш-памяти ".format(len(self.flash)))
            for page_no in self.flash:
                pb.update(page_no / len(self.flash))
                page_bytes = self.flash[page_no]
                blocks_per_page = self.PAGE_SIZE // self.get_block_size()
                assert self.PAGE_SIZE % self.get_block_size() == 0
                for block_no in range(0, blocks_per_page):
                    block = bytes(page_bytes[block_no*self.get_block_size():(block_no+1)*self.get_block_size()])
                    encrypted_block = self.encrypt(self.block_xor(block, accum))
                    accum = encrypted_block
                    binfile.write(encrypted_block)
                page_no_bytes = bytes(page_no >> 8 * i & 0xFF for i in range(2))
                crc32_bytes = bytes(crc32(page_bytes + page_no_bytes) >> 8 * i & 0xFF for i in range(4))
                block = page_no_bytes + crc32_bytes\
                    + urandom(self.get_block_size() - len(page_no_bytes) - len(crc32_bytes))
                encrypted_block = self.encrypt(self.block_xor(block, accum))
                accum = encrypted_block
                binfile.write(encrypted_block)
            pb.close()
        sys.stdout.write("[INFO   ] Готово\n")