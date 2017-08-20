from tkinter import *
from tkinter import filedialog


class FileSelector(Frame):
    FONT = ('Courier', 12, 'normal')

    def __init__(self, parent=None, io='r', text='File:', path='', **configs):
        Frame.__init__(self, parent, bd=1, relief=SUNKEN, **configs)
        assert io in {'r', 'w'}
        assert isinstance(text, str)
        Button(self, text='Открыть...', command=self.select_file, font=self.FONT).pack(side=RIGHT, padx=3, pady=3)
        self.path = StringVar()
        self.path.set(path)
        Entry(self, textvariable=self.path).pack(side=RIGHT, padx=3, pady=3, fill=X, expand=YES)
        Label(self, text=text, anchor=E, font=self.FONT).pack(side=LEFT, padx=3, pady=3)
        self.io = io

    def select_file(self):
        if self.io == 'r':
            self.path.set(filedialog.askopenfile())
        else:
            self.path.set(filedialog.asksaveasfilename())

if __name__ == '__main__':
    widget = FileSelector()
    widget.pack()
    widget.mainloop()