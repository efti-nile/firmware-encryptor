#!/usr/bin/python3
# encoding=UTF-8
from linboot_secret_generator import generate_secret
from linboot_encryptor import LinbootHexEncryptor
from linboot_flasher import LinbootFlasher
import argparse

__version__ = "1.0.0.A"
prog_name = "Linboot client v. {0:s}".format(__version__)


def cmd_generate_secret(cli_args):
    generate_secret(cli_args.output_filename)


def cmd_encrypt(cli_args):
    with open(cli_args.secret_filename) as secret_file:
        key = secret_file.read(256//8)
        ivc = secret_file.read(128//8)
    LinbootHexEncryptor(key, ivc).encrypt_hex(
        cli_args.input_filename,
        cli_args.output_filaname
    )


def cmd_flash(cli_args):
    LinbootFlasher(cli_args.serial_port, cli_args.baudrate).flash(cli_args.input_filename)

commands = {'generate_secret': cmd_generate_secret, 'encrypt': cmd_encrypt, 'flash': cmd_flash}

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

args = parser.parse_args()

commands[args.command[0]](args)
