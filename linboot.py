#!/usr/bin/python3
# encoding=UTF-8
from linboot_secret_generator import generate_secret
from linboot_encryptor import LinbootHexEncryptor
from linboot_flasher import LinbootFlasher
import argparse
import sys

# CLI arguments example
# -i linboot.hex -o linboot-encr.bin -s secret_test.bin encrypt
# -i linboot-encr.bin --serial COM8 --lin 0x02 flash


__version__ = "1.0.0.A"
prog_name = "Linboot client v. {0:s}".format(__version__)


def cmd_generate_secret(cli_args):
    generate_secret(cli_args.output_filename)


def cmd_encrypt(cli_args):
    with open(cli_args.secret_filename, "rb") as secret_file:
        key = secret_file.read(256//8)
        ivc = secret_file.read(128//8)
    LinbootHexEncryptor(key, ivc).encrypt_hex(
        cli_args.input_filename,
        cli_args.output_filename
    )


def cmd_flash(cli_args):
    flasher = LinbootFlasher(cli_args.serial_port, cli_args.baudrate)
    flasher.set_lin_address(int(cli_args.lin_address, 16))
    flasher.flash(cli_args.input_filename)


def cmd_bootloader_version(cli_args):
    flasher = LinbootFlasher(cli_args.serial_port, cli_args.baudrate)
    flasher.set_lin_address(int(cli_args.lin_address, 16))
    sys.stdout.write(flasher.version())

commands = {'generate_secret': cmd_generate_secret,
            'encrypt': cmd_encrypt,
            'flash': cmd_flash,
            'bootloader_version': cmd_bootloader_version}

parser = argparse.ArgumentParser(description='Linboot client for linboot-bootloader')
parser.add_argument('command', nargs=1, help='what to do', choices=commands.keys())
parser.add_argument('-i', nargs='?', help='input file', metavar='INPUT_FILENAME', dest='input_filename')
parser.add_argument('-o', nargs='?', help='output file', metavar='OUTPUT_FILENAME', dest='output_filename')
parser.add_argument('-s', nargs='?', help='secret file *.bin with key and IVC for Serpent cipher',
                    metavar='SECRET_FILENAME', dest='secret_filename')
parser.add_argument('--serial', nargs='?', help='serial port (e.g. COM2 or /dev/ttyUSB0)',
                    metavar='PORT', dest='serial_port')
parser.add_argument('--baud', nargs='?', help='baud rate (e.g. COM2 or /dev/ttyUSB0)',
                    metavar='RATE', dest='baudrate', type=int, default=9600)
parser.add_argument('--lin', nargs='?', help='LIN device address in hex (e.g. 0x02)',
                    metavar='ADDR', dest='lin_address', default=0x02)

args = parser.parse_args()

commands[args.command[0]](args)
