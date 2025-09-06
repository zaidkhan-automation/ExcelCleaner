import tkinter as tk

root = tk.Tk()
root.title("TEST WINDOW")
root.geometry("250x100")
tk.Label(root, text="If you see this, tkinter works!").pack()
root.mainloop()