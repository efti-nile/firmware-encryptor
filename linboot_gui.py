#!/usr/bin/python3
# coding=UTF-8
from tkinter.messagebox import showerror
from tkinter import filedialog
from tkinter import *
from tkinter.ttk import *
from crc8dallas import crc8
import os.path
import codecs
import serial
import json
import re
import time
import subprocess


class StdoutRedirector(object):
    def __init__(self, text_widget):
        self.text_space = text_widget

    def write(self,string):
        self.text_space.insert('end', string)
        self.text_space.see('end')


class LinbootGui(Tk):
    SETTINGS_FILE = 'settings.json'
    DEFAULT_SERIAL_PORT = 'COM1'
    DEFAULT_LIN_ADDRESS = 0x02
    DEFAULT_BAUD_RATE = 9600

    LABEL_WIDTH = 15
    ENTRY_WIDTH = 40

    def __init__(self):
        """Creates GUI and reads default settings"""
        Tk.__init__(self)
        self.title('Загрузчик LINBOOT')
        # self.geometry('900x200')

        # Load default settings if exists
        if os.path.exists(self.SETTINGS_FILE):
            with open(self.SETTINGS_FILE, 'r') as f:
                self.settings = json.load(f)
        else:
            self.settings = {}

        # Create Notebook with control tabs
        nb = Notebook(self)

        # Create control tab for Flasher
        flasher = Frame(nb)
        nb.add(flasher, text='Загрузка прошивки')

        Label(flasher, text='Шифр-образ:', width=self.LABEL_WIDTH).grid(sticky='W')
        self.enbin_file = StringVar()
        self.enbin_file.set(self.settings['enbin_file'] if 'enbin_file' in self.settings else '')
        Entry(flasher, textvariable=self.enbin_file, width=self.ENTRY_WIDTH).grid(row=0, column=1, sticky='WE')
        Button(flasher, text='Открыть...', command=self.enbin_file_open).grid(row=0, column=2)

        Label(flasher, text='COM-порт:', width=self.LABEL_WIDTH).grid(row=1, column=0, sticky='W')
        self.serial_string = StringVar()
        self.serial_string.set(self.settings['serial_string'] if 'serial_string' in self.settings
                               else self.DEFAULT_SERIAL_PORT)
        Entry(flasher, textvariable=self.serial_string, width=(self.ENTRY_WIDTH // 2)).grid(row=1, column=1, sticky=W)

        Label(flasher, text='LIN-адрес:', width=self.LABEL_WIDTH).grid(row=2, column=0, sticky='W')
        self.lin_address = StringVar()
        self.lin_address.set(self.settings['LIN_address'] if 'LIN_address' in self.settings
                             else hex(self.DEFAULT_LIN_ADDRESS))
        Entry(flasher, textvariable=self.lin_address, width=(self.ENTRY_WIDTH // 2)).grid(row=2, column=1, sticky=W)
        Button(flasher, text='Загрузить', command=self.flash).grid(row=2, column=2, sticky=E)

        # Create control tab for Encryptor
        encryptor = Frame(nb)
        nb.add(encryptor, text='Шифрование прошивки')

        Label(encryptor, text='HEX-файл:', width=self.LABEL_WIDTH).grid()
        self.hex_file = StringVar()
        self.hex_file.set(self.settings['hex_file'] if 'hex_file' in self.settings
                             else '')
        Entry(encryptor, textvariable=self.hex_file, width=self.ENTRY_WIDTH).grid(row=0, column=1)
        Button(encryptor, text='Открыть...', command=self.hex_file_open).grid(row=0, column=2)

        Label(encryptor, text='Ключ:', width=self.LABEL_WIDTH).grid(row=1, column=0)
        self.secret_file = StringVar()
        self.secret_file.set(self.settings['secret_file'] if 'secret_file' in self.settings
                             else '')
        Entry(encryptor, textvariable=self.secret_file, width=self.ENTRY_WIDTH).grid(row=0, column=1)
        Button(encryptor, text='Открыть...', command=self.secret_file_open).grid(row=0, column=2)

        # Create control tab for Secret Generator
        secret_generator = Frame(nb)
        nb.add(secret_generator, text='Генерация ключа шифрования')
        Label(secret_generator, text='Имя ключа:', width=self.LABEL_WIDTH).grid(row=0, column=0, sticky='E')
        self.secret_name = StringVar()
        self.secret_name.set(self.settings['secret_name'] if 'secret_name' in self.settings
                             else 'secret')
        Entry(secret_generator, textvariable=self.secret_name, width=self.ENTRY_WIDTH).grid(row=0, column=1, columnspan=3, sticky='WE')

        Label(secret_generator, text='Папка:', width=self.LABEL_WIDTH).grid(row=1, column=0, sticky='E')
        self.secret_dir = StringVar()
        self.secret_dir.set(self.settings['secret_dir'] if 'secret_dir' in self.settings
                            else '.')
        Entry(secret_generator, textvariable=self.secret_dir, width=self.ENTRY_WIDTH).grid(row=1, column=1, columnspan=3, sticky='WE')
        Button(secret_generator, text='Выбрать...', command=self.secret_dir_choose).grid(row=1, column=4)

        Button(secret_generator, text='Генерировать', command=self.generate_secret).grid(row=2, column=1, sticky='W')

        nb.pack(fill=BOTH, expand=YES)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def enbin_file_open(self):
        enbin_file = filedialog.askopenfile(initialdir='.',
                                            title='Select file',
                                            filetypes=(("binary files","*.bin"),("all files","*.*"))).name
        self.enbin_file.set(enbin_file)
        self.settings['enbin_file'] = enbin_file

    def secret_file_open(self):
        pass

    def hex_file_open(self):
        pass

    def secret_dir_choose(self):
        secret_dir = filedialog.askdirectory()
        if secret_dir:
            self.secret_dir.set(secret_dir)
            self.settings['secret_dir'] = secret_dir

    def flash(self):
        cli_arg = 'python linboot.py -i {0} --serial {1} --lin {2} flash'.format(self.enbin_file.get(),
                                                                                 self.serial_string.get(),
                                                                                 self.lin_address.get())

    def generate_secret(self):
        command = 'python linboot.py -o {0} generate_secret'.format(
            os.path.join(self.secret_dir.get(), self.secret_name.get())
        )
        os.system(command)

    def on_closing(self):
        with open(self.SETTINGS_FILE, 'w') as file:
            json.dump(self.settings, file)
        self.destroy()

if __name__ == '__main__':
    top = LinbootGui()
    top.mainloop()
