import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import asyncio
import threading

import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(1) # Fixes blurry GUI

from logic_parser import Parser
from db_parser import ParserDB
from config import DEFAULT_CONFIG, RESULT_TEMPLATE


class ParserGUI:
    def __init__(self, root):
        root.tk.call('tk', 'scaling', 2.0)
        self.parser = Parser()
        self.root = root
        self.root.title("Chat Message Parser")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)

        db = ParserDB()
        self.config = db.get_all_config()
        db.close()
        
        # Sidebar (left)
        self.sidebar = tk.Frame(self.root, width=350, bg="#777777")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Grid behavior for sidebar
        self.sidebar.grid_rowconfigure(1, weight=1)
        self.sidebar.grid_columnconfigure(0, weight=1)

        # Stats title
        self.info_label = tk.Label(
            self.sidebar,
            text="Message Statistics",
            font=("Arial", 14, "bold"),
            bg="#777777", fg="white")
        self.info_label.grid(row=0, column=0, padx=15, pady=10)

        # Stats area (dynamically filled)
        self.stats_text = ScrolledText(
            self.sidebar,
            font=("Arial", 12),
            bg="#777777",
            fg="white",
            wrap=tk.CHAR,
            height=30,
            width=30,
            state=tk.DISABLED)
        self.stats_text.grid(row=1, column=0, padx=10, pady=10, sticky="ns")

        # Clear stats database
        self.clear_stats_button = tk.Button(
            self.sidebar,
            text="Clear Stats",
            command=self.clear_stats,
            bg="#bb2222",
            fg="white",
            width=15,)
        self.clear_stats_button.grid(row=2, column=0, padx=10, pady=10)

        # Main frame (right)
        self.main_frame = tk.Frame(self.root)
        self.main_frame.grid(row=0, column=1, sticky="nsew")

        # Grid behavior for main_frame
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Main title
        self.title_label = tk.Label(
            self.main_frame,
            text="CHAT MESSAGE PARSER",
            font=("Arial", 18, "bold"))
        self.title_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))

        # Json output area
        self.text_output = ScrolledText(
            self.main_frame,
            state=tk.DISABLED,
            font=("Arial", 12))
        self.text_output.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        # Input frame (bottom right (above config))
        self.input_frame = tk.Frame(self.main_frame)
        self.input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        # Grid behavior for input_frame
        self.input_frame.columnconfigure(0, weight=8, uniform="input")
        self.input_frame.columnconfigure(1, weight=2, uniform="input")

        # Message box title
        self.input_label = tk.Label(
            self.input_frame,
            text="Enter Message:")
        self.input_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 2))

        # Message box
        self.text_input = ScrolledText(
            self.input_frame,
            font=("Arial", 12),
            height=3)
        self.text_input.grid(row=1, column=0, sticky="ew", padx=(0, 5), pady=0)

        # Parse message on button click
        self.submit_button = tk.Button(
            self.input_frame,
            text="Parse",
            command=self.run_parser_thread)
        self.submit_button.grid(row=1, column=1, sticky="nsew", padx=(5, 0), pady=0)
        
        # Config frame (bottom right)
        self.config_frame = tk.LabelFrame(
            self.main_frame,
            text="Config Settings",
            font=("Arial", 10, "bold"))
        self.config_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))

        # Grid behavior for config_frame
        self.config_frame.columnconfigure(0, weight=1)
        self.config_frame.columnconfigure(1, weight=1)

        # Configuration settings (Dynamically added from config)
        self.config_fields = DEFAULT_CONFIG
        self.config_vars = {}
        for idx, field in enumerate(self.config_fields):
            tk.Label(self.config_frame, text=field["label"] + ":").grid(row=idx, column=0, sticky="w", padx=5, pady=2)
            value = int(self.config[field["key"]]) if field["type"] == int else str(self.config[field["key"]])
            if field["type"] == int:
                var = tk.IntVar(value=value)
            else:
                var = tk.StringVar(value=value)
            self.config_vars[field["key"]] = var
            tk.Entry(self.config_frame, textvariable=var, width=10).grid(row=idx, column=1, sticky="w", padx=5, pady=2)

        # Save config changes on button click
        self.apply_config_button = tk.Button(
            self.config_frame,
            text="Save",
            command=self.save_config)
        self.apply_config_button.grid(row=2, column=0, columnspan=2, pady=(5, 2))

        # Reset configs on button click
        self.reset_config_button = tk.Button(
            self.config_frame,
            text="Reset to Defaults",
            command=self.reset_to_defaults,
            bg="#555555", fg="white"
        )
        self.reset_config_button.grid(row=4, column=0, columnspan=2, pady=(0, 5))

        # Grid behavior for root (main window)
        self.root.grid_columnconfigure(0, weight=0, minsize=350) # Ensure sidebar doesnt shrink
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.buttons = [self.clear_stats_button, self.submit_button, self.apply_config_button]
        self.update_stats() # Show stats from database on startup


    def disable_buttons(self):
        for btn in self.buttons:
            btn.config(state=tk.DISABLED)

    def enable_buttons(self):
        for btn in self.buttons:
            btn.config(state=tk.NORMAL)


    # Dynamically shows stats
    def update_stats(self):
        self.disable_buttons()

        db = ParserDB()
        stats_text = ""
        list_categories = [k for k, v in RESULT_TEMPLATE.items() if isinstance(v, list) and k != "links"]

        for category in list_categories:
            top = db.get_top(category, limit=5)
            stats_text += f"{category.title()}:\n"
            if top:
                for value, count in top:
                    display_value = value if len(str(value)) <= 15 else str(value)[:15] + "..."
                    stats_text += f"  {display_value}: {count}\n"
            else:
                stats_text += "  (none)\n"
            stats_text += "\n"
        db.close()

        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete("1.0", tk.END)
        self.stats_text.insert(tk.END, stats_text)
        self.stats_text.config(state=tk.DISABLED)

        self.enable_buttons()


    def clear_stats(self):
        self.disable_buttons()
        db = ParserDB()
        db.conn.execute("DELETE FROM stats")
        db.conn.commit()
        db.close()
        self.update_stats()

    # Save user config inputs (resets to defualt values if type error)
    def save_config(self):
        self.disable_buttons()

        db = ParserDB()
        for field in self.config_fields:
            try:
                value = self.config_vars[field["key"]].get()
                value = field["type"](value)
            except Exception:
                value = field["default"]
                self.config_vars[field["key"]].set(value)
            db.set_config(field["key"], value)
        db.close()

        db = ParserDB()
        self.config = db.get_all_config()
        db.close()

        # Update parser variables
        for field in self.config_fields:
            setattr(self.parser, field["key"], field["type"](self.config[field["key"]]))
            
        self.enable_buttons()


    def reset_to_defaults(self):
        for field in self.config_fields:
            self.config_vars[field["key"]].set(field["default"])


    def run_parser_thread(self):
        message = self.text_input.get("1.0", tk.END).strip()
        if not message:
            return
        self.disable_buttons()
        thread = threading.Thread(target=self.run_async_parse, args=(message,))
        self.text_input.delete("1.0", tk.END)
        thread.start()


    def run_async_parse(self, message):
        result = asyncio.run(self.parser.parse(message))
        self.display_output(message, result)
        self.update_stats()


    def display_output(self, input_msg, result):
        self.text_output.config(state=tk.NORMAL)
        self.text_output.insert(tk.END, f"Input: \n{input_msg} \nJSON: \n")
        self.text_output.insert(tk.END, result)
        self.text_output.insert(tk.END, "\n\n" + "━"*20 + "\n\n")
        self.text_output.see(tk.END)
        self.text_output.config(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = ParserGUI(root)
    root.mainloop()