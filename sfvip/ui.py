import tkinter as tk
from tkinter import filedialog, messagebox


class UI:
    """barebone UI"""

    _root = None

    def __init__(self, title: str) -> None:
        self.title = title
        if UI._root is None:
            UI._root = tk.Tk()
            UI._root.withdraw()

    def showinfo(self, message: str) -> None:
        messagebox.showinfo(self.title, message=message)

    def find_file(self, name: str, pattern: str) -> None:
        title = f"{self.title}: Find {name}"
        return filedialog.askopenfilename(title=title, filetypes=[(name, pattern)])

    def askretry(self, message: str) -> None:
        return messagebox.askretrycancel(self.title, message=message)
