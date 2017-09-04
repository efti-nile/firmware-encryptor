from file_selector import *
from tkinter import *


class FirmwareEncryptorApp(Tk):
    LABELS_MAXLEN = len('Вектор инициализации CBC:')
    FONT = ('Courier', 12, 'normal')

    def __init__(self, parent=None, **configs):
        Tk.__init__(self, parent, **configs)
        self.title('Подготовка прошивки для LIN-загрузчика')

        Button(self, text='Зашифровать', font=self.FONT).pack(side=BOTTOM, anchor=E, padx=5, pady=5)
        self.input_file_selector = FileSelector(io='r', text='Файл прошивки:'.rjust(self.LABELS_MAXLEN))
        self.key_file_selector = FileSelector(io='r', text='Ключ шифрования:'.rjust(self.LABELS_MAXLEN))
        self.ivc_file_selector = FileSelector(io='r', text='Вектор инициализации CBC:'.rjust(self.LABELS_MAXLEN))
        self.output_file_selector = FileSelector(io='w', text='Имя выходного файла:'.rjust(self.LABELS_MAXLEN))
        self.input_file_selector.pack(expand=YES, fill=BOTH)
        self.key_file_selector.pack(expand=YES, fill=BOTH)
        self.ivc_file_selector.pack(expand=YES, fill=BOTH)
        self.output_file_selector.pack(expand=YES, fill=BOTH)




if __name__ == '__main__':
    App = FirmwareEncryptorApp()
    App.mainloop()
