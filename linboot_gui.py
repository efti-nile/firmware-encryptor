#!/usr/bin/python3
# coding=UTF-8
from tkinter.messagebox import showerror
from subprocess import Popen, PIPE
from threading import Thread
from queue import Queue
from tkinter import filedialog
from tkinter import *
from tkinter.ttk import *
import os.path
import json


ON_POSIX = 'posix' in sys.builtin_module_names


class AsyncUtf8FileReader(Thread):
    def __init__(self, fd, queue):
        assert isinstance(queue, Queue)
        assert callable(fd.readline)
        Thread.__init__(self)
        self._fd = fd
        self._queue = queue

    def run(self):
        buf = b''
        for chunk in iter(lambda: self._fd.read(1), b''):
            buf += chunk
            if len(buf) > 0:
                if buf[-1] < 0x80:
                    self._queue.put(buf)
                    buf = b''

    def eof(self):
        return not self.is_alive() and self._queue.empty()


class LinbootGui(Tk):
    SETTINGS_FILE = 'settings.json'
    LINBOOT_EXE_PATH = './linboot/linboot.exe'
    LINBOOT_PY_PATH = 'linboot.py'
    PYTHON_INTERPRETER = 'python'

    DEFAULT_SERIAL_PORT = 'COM1'
    DEFAULT_LIN_ADDRESS = 0x02
    DEFAULT_BAUD_RATE = 9600

    LABEL_WIDTH = 15
    ENTRY_WIDTH = 81

    TEMP_DIR = './temp'
    TEMP_ENC_BIN = './temp/enc_hex_temp.bin'

    subproc_run = False
    flash_schedule = False

    def __init__(self):
        """Creates GUI and reads default settings"""
        Tk.__init__(self)
        self.title('Загрузчик LINBOOT')
        self.resizable(0, 0)

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

        self.infile_type = StringVar()

        # Raw HEX selector
        raw_hex_selector = Frame(flasher, relief=RIDGE, padding=3)
        raw_hex_selector.grid(row=0, column=0, columnspan=4)

        self.raw_hex_radiobutton = Radiobutton(raw_hex_selector, text='Использовать ключ и HEX-файл',
                                               command=self.on_infile_type_select, variable=self.infile_type,
                                               value='raw_hex_selector')
        self.raw_hex_radiobutton.grid(columnspan=3, sticky=W)

        Label(raw_hex_selector, text='HEX-файл:', width=self.LABEL_WIDTH).grid(row=1, column=0, sticky='W')
        self.raw_hex_file = StringVar()
        self.raw_hex_file.set(self.settings['raw_hex_file'] if 'raw_hex_file' in self.settings else '')
        Entry(raw_hex_selector, textvariable=self.raw_hex_file, width=self.ENTRY_WIDTH).grid(row=1, column=1,
                                                                                             sticky='WE')
        Button(raw_hex_selector, text='Открыть...',
               command=(lambda: self.file_open(self.raw_hex_file, ('HEX-файл', '*.hex')))).grid(row=1, column=2)

        Label(raw_hex_selector, text='Ключ:', width=self.LABEL_WIDTH).grid(row=2, column=0, sticky='W')
        self.secret_file = StringVar()
        self.secret_file.set(self.settings['secret_file'] if 'secret_file' in self.settings else '')
        Entry(raw_hex_selector, textvariable=self.secret_file, width=self.ENTRY_WIDTH).grid(row=2, column=1, sticky='WE')
        Button(raw_hex_selector, text='Открыть...',
               command=(lambda: self.file_open(self.secret_file, ('ключ', '*.bin')))).grid(row=2, column=2)

        self.raw_hex_selector = raw_hex_selector

        # Encrypted HEX selector
        enc_hex_selector = Frame(flasher, relief=RIDGE, padding=3)
        enc_hex_selector.grid(row=1, column=0, columnspan=4)

        self.enc_hex_radiobutton = Radiobutton(enc_hex_selector, text='Использовать готовый шифр-образ',
                                               command=self.on_infile_type_select, variable=self.infile_type,
                                               value='enc_hex_selector')
        self.enc_hex_radiobutton.grid(columnspan=3, sticky=W)

        Label(enc_hex_selector, text='Шифр-образ:', width=self.LABEL_WIDTH).grid(sticky='W')
        self.enc_hex_file = StringVar()
        self.enc_hex_file.set(self.settings['enc_hex_file'] if 'enc_hex_file' in self.settings else '')
        Entry(enc_hex_selector, textvariable=self.enc_hex_file, width=self.ENTRY_WIDTH).grid(row=1, column=1,
                                                                                             sticky='WE')
        Button(enc_hex_selector, text='Открыть...',
               command=(lambda: self.file_open(self.enc_hex_file, ('шифр-образ', '*.bin')))).grid(row=1, column=2)

        self.enc_hex_selector = enc_hex_selector

        # Enable last active selector
        self.infile_type.set(self.settings['infile_type'] if 'infile_type' in self.settings else 'enc_hex_selector')
        self.on_infile_type_select()

        Label(flasher, text='COM-порт:', width=self.LABEL_WIDTH, padding=5).grid(row=2, column=0, sticky='E')
        self.serial_string = StringVar()
        self.serial_string.set(self.settings['serial_string'] if 'serial_string' in self.settings
                               else self.DEFAULT_SERIAL_PORT)
        Entry(flasher, textvariable=self.serial_string, width=(self.ENTRY_WIDTH // 4)).grid(row=2, column=1, sticky=W)

        Label(flasher, text='LIN-адрес:', width=self.LABEL_WIDTH, padding=3).grid(row=3, column=0, sticky='E')
        self.lin_address = StringVar()
        self.lin_address.set(self.settings['LIN_address'] if 'LIN_address' in self.settings
                             else hex(self.DEFAULT_LIN_ADDRESS))
        Entry(flasher, textvariable=self.lin_address, width=(self.ENTRY_WIDTH // 4)).grid(row=3, column=1, sticky=W)
        Button(flasher, text='Загрузить', command=self.flash).grid(row=3, column=3, sticky=E)

        # Create control tab for Encryptor
        encryptor = Frame(nb)
        nb.add(encryptor, text='Шифрование прошивки')

        Label(encryptor, text='HEX-файл:', width=self.LABEL_WIDTH).grid()
        self.hex_file = StringVar()
        self.hex_file.set(self.settings['hex_file'] if 'hex_file' in self.settings
                          else '')
        Entry(encryptor, textvariable=self.hex_file, width=self.ENTRY_WIDTH).grid(row=0, column=1)
        Button(encryptor, text='Открыть...',
               command=(lambda: self.file_open(self.hex_file, ('HEX-файл', '*.hex')))).grid(row=0, column=2)

        Label(encryptor, text='Ключ:', width=self.LABEL_WIDTH).grid(row=1, column=0)
        Entry(encryptor, textvariable=self.secret_file, width=self.ENTRY_WIDTH).grid(row=1, column=1)
        Button(encryptor, text='Открыть...',
               command=(lambda: self.file_open(self.secret_file, ('ключ', '*.bin')))).grid(row=1, column=2)

        Label(encryptor, text='Папка:', width=self.LABEL_WIDTH).grid(row=2, column=0)
        self.enc_hex_dir = StringVar()
        self.enc_hex_dir.set(self.settings['enc_hex_dir'] if 'enc_hex_dir' in self.settings
                             else '')
        Entry(encryptor, textvariable=self.enc_hex_dir, width=self.ENTRY_WIDTH).grid(row=2, column=1)
        Button(encryptor, text='Выбрать...',
               command=(lambda: self.dir_choose(self.enc_hex_dir))).grid(row=2, column=2)

        Button(encryptor, text='Шифровать', command=self.encrypt).grid(row=3, column=1, sticky='W')

        # Create control tab for Secret Generator
        secret_generator = Frame(nb)
        nb.add(secret_generator, text='Генерация ключа шифрования')
        Label(secret_generator, text='Имя ключа:', width=self.LABEL_WIDTH).grid(row=0, column=0, sticky='E')
        self.secret_name = StringVar()
        self.secret_name.set(self.settings['secret_name'] if 'secret_name' in self.settings
                             else 'secret')
        Entry(secret_generator, textvariable=self.secret_name, width=self.ENTRY_WIDTH).grid(row=0, column=1,
                                                                                            columnspan=3, sticky='WE')

        Label(secret_generator, text='Папка:', width=self.LABEL_WIDTH).grid(row=1, column=0, sticky='E')
        self.secret_dir = StringVar()
        self.secret_dir.set(self.settings['secret_dir'] if 'secret_dir' in self.settings
                            else '.')
        Entry(secret_generator, textvariable=self.secret_dir, width=self.ENTRY_WIDTH).grid(row=1, column=1,
                                                                                           columnspan=3, sticky='WE')
        Button(secret_generator, text='Выбрать...', command=(lambda: self.dir_choose(self.secret_dir))).grid(row=1,
                                                                                                             column=4)

        Button(secret_generator, text='Генерировать', command=self.generate_secret).grid(row=2, column=1, sticky='W')

        nb.pack(fill=BOTH)

        # Output
        self.scroll = Scrollbar(self)
        self.scroll.pack(side=RIGHT, fill=Y, expand=YES)

        self.output = Text(self, height=10, width=81)
        self.output.pack(fill=BOTH, expand=YES)

        self.scroll.config(command=self.output.yview)
        self.output.config(yscrollcommand=self.scroll.set)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    @staticmethod
    def file_open(var, filetype):
        file = filedialog.askopenfile(filetypes=(filetype, ('все файлы', '*.*'))).name
        if file:
            var.set(file)

    @staticmethod
    def dir_choose(var):
        directory = filedialog.askdirectory()
        if directory:
            var.set(directory)

    def on_infile_type_select(self):
        self.set_children_state(self.raw_hex_selector, DISABLED)
        self.set_children_state(self.enc_hex_selector, DISABLED)
        self.set_children_state(getattr(self, self.infile_type.get()), NORMAL)
        self.raw_hex_radiobutton.config(state=NORMAL)
        self.enc_hex_radiobutton.config(state=NORMAL)

    @staticmethod
    def set_children_state(parent, state):
        for child in parent.winfo_children():
            child.config(state=state)

    def start_subprocess(self, cli_args, **kwargs):
        if os.path.isfile(self.LINBOOT_PY_PATH):
            cli_line = [self.PYTHON_INTERPRETER, self.LINBOOT_PY_PATH] + cli_args
        elif os.path.isfile(self.LINBOOT_EXE_PATH):
            cli_line = [self.LINBOOT_EXE_PATH] + cli_args
        else:
            showerror(title='Ошибка', message='linboot не найден')
            return
        self.subproc_run = True
        self.subproc = Popen(cli_line, **kwargs)
        self.queue = Queue()
        self.reader = AsyncUtf8FileReader(self.subproc.stdout, self.queue)
        self.reader.start()
        self.output_updater()

    def flash(self):
        if self.infile_type.get() == 'enc_hex_selector' or self.flash_schedule:
            if not self.flash_schedule and not os.path.isfile(self.enc_hex_file.get()):
                showerror(title='Ошибка', message='Файл {0} не существует'.format(self.enc_hex_file.get()))
                return

            if not self.flash_schedule:
                self.output.delete('1.0', END)

            self.flash_schedule = False

            self.start_subprocess(['-i', self.enc_hex_file.get() if not self.flash_schedule else self.TEMP_ENC_BIN,
                                   '--serial', self.serial_string.get(),
                                   '--lin', self.lin_address.get(),
                                   'flash'],
                                  stdout=PIPE, stderr=PIPE, stdin=PIPE,
                                  bufsize=1, close_fds=ON_POSIX)

            if not self.flash_schedule:
                self.settings['enc_hex_file'] = self.enc_hex_file.get()
            self.settings['serial_string'] = self.serial_string.get()
            self.settings['lin_address'] = self.lin_address.get()
        elif self.infile_type.get() == 'raw_hex_selector':
            if not os.path.isfile(self.raw_hex_file.get()):
                showerror(title='Ошибка', message='Файл {0} не существует'.format(self.raw_hex_file.get()))
                return
            if not os.path.isfile(self.secret_file.get()):
                showerror(title='Ошибка', message='Файл {0} не существует'.format(self.secret_file.get()))
                return

            if not os.path.isdir(self.TEMP_DIR):
                os.mkdir(self.TEMP_DIR)

            self.start_subprocess([self.LINBOOT_EXE_PATH,
                                   '-i', self.raw_hex_file.get(),
                                   '-o', self.TEMP_ENC_BIN,
                                   '-s', self.secret_file.get(),
                                   'encrypt'],
                                  stdout=PIPE, stderr=PIPE, stdin=PIPE,
                                  bufsize=1, close_fds=ON_POSIX)

            self.settings['raw_hex_file'] = self.raw_hex_file.get()
            self.settings['secret_file'] = self.secret_file.get()

            self.flash_schedule = True

    def encrypt(self):
        if not os.path.isfile(self.hex_file.get()):
            showerror(title='Ошибка', message='Файл {0} не существует'.format(self.hex_file.get()))
            return
        if not os.path.isfile(self.secret_file.get()):
            showerror(title='Ошибка', message='Файл {0} не существует'.format(self.secret_file.get()))
            return
        if not os.path.isdir(self.enc_hex_dir.get()):
            showerror(title='Ошибка', message='Папка {0} не существует'.format(self.enc_hex_dir.get()))
            return

        self.output.delete('1.0', END)

        self.start_subprocess(['-i', self.hex_file.get(),
                               '-o', self.enc_hex_dir.get() + '/' + os.path.split(self.hex_file.get())[1] + '.bin',
                               '-s', self.secret_file.get(),
                               'encrypt'],
                              stdout=PIPE, stderr=PIPE, stdin=PIPE,
                              bufsize=1, close_fds=ON_POSIX)

        self.settings['hex_file'] = self.hex_file.get()
        self.settings['secret_file'] = self.secret_file.get()
        self.settings['enc_hex_dir'] = self.enc_hex_dir.get()

    def generate_secret(self):
        if not os.path.isdir(self.secret_dir.get()):
            showerror(title='Ошибка', message='Папка {0} не существует'.format(self.secret_dir.get()))
            return

        self.output.delete('1.0', END)

        self.start_subprocess(['-o', os.path.join(self.secret_dir.get() + '/', self.secret_name.get()),
                               'generate_secret'],
                              stdout=PIPE, stderr=PIPE, stdin=PIPE,
                              bufsize=1, close_fds=ON_POSIX)

    def output_updater(self):
        while not self.queue.empty():
            chunk = self.queue.get()
            self.output.insert(END, chunk.decode('utf-8', 'ignore'))
        if not self.reader.eof() and self.subproc.poll is not None:
            self.after(500, self.output_updater)
        else:
            self.subproc_run = False
            if self.flash_schedule:
                self.after(2000, self.flash)

    def on_closing(self):
        with open(self.SETTINGS_FILE, 'w') as file:
            json.dump(self.settings, file)
        self.destroy()

if __name__ == '__main__':
    top = LinbootGui()
    top.mainloop()
