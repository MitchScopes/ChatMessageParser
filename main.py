import tkinter as tk
from src.gui import ParserGUI

if __name__ == "__main__":
    root = tk.Tk()
    app = ParserGUI(root)
    root.mainloop()