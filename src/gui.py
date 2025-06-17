import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import asyncio
import threading
from datetime import datetime
import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(1) # Fixes blurry GUI

from src.logic import Parser
from src.db import ParserDB
from src.config import DEFAULT_CONFIG, RESULT_TEMPLATE


class Sidebar(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, width=350, bg="#777777")
        self.controller = controller
        self.grid_propagate(False)

        # Grid behavior for sidebar
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Stats title
        self.info_label = tk.Label(
            self, text="Message Statistics",
            font=("Arial", 14, "bold"),
            bg="#777777", fg="white")
        self.info_label.grid(row=0, column=0, padx=15, pady=10)

        # Stats area (dynamically filled)
        self.stats_text = ScrolledText(
            self, font=("Arial", 12),
            bg="#777777",
            fg="white",
            wrap=tk.CHAR,
            height=30,
            width=30,
            state=tk.DISABLED)
        self.stats_text.grid(row=1, column=0, padx=10, pady=10, sticky="ns")

        # Clear stats database
        self.clear_stats_button = tk.Button(
            self, text="Clear Stats",
            command=self.clear_stats,
            bg="#bb2222",
            fg="white",
            width=15,)
        self.clear_stats_button.grid(row=2, column=0, padx=10, pady=10)

    # Dynamically shows stats
    def update_stats(self):
        self.controller.disable_buttons()

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

        self.controller.enable_buttons()


    def clear_stats(self):
        self.controller.disable_buttons()
        db = ParserDB()
        db.conn.execute("DELETE FROM stats")
        db.conn.commit()
        db.conn.execute("VACUUM")
        db.close()
        self.update_stats()



class InputFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Grid behavior for input_frame
        self.columnconfigure(0, weight=1)

        # Message box title
        self.input_label = tk.Label(
            self, text="Enter Message:",
            font=("Arial", 11, "bold"))
        self.input_label.grid(row=0, column=0, sticky="w", pady=(0, 2))

        # Mode selection and radio buttons
        self.selected_option = tk.StringVar(value="Full_Sweep")

        self.mode_full_sweep = tk.Radiobutton(
            self, text="Full Sweep Mode",
            variable=self.selected_option,
            value="Full_Sweep"
        )
        self.mode_full_sweep.grid(row=0, column=1, sticky="nsew")

        self.mode_safe_scan = tk.Radiobutton(
            self, text="Safe Scan Mode",
            variable=self.selected_option,
            value="Safe_Scan"
        )
        self.mode_safe_scan.grid(row=0, column=2, sticky="nsew")

        # Message box
        self.text_input = ScrolledText(
            self, font=("Arial", 12),
            height=3)
        self.text_input.grid(row=1, column=0,  sticky="ew", padx=(0, 5), pady=0)

        # Parse message on button click
        self.submit_button = tk.Button(
            self, text="Parse",
            font=("Arial", 12),
            command=self.run_parser_thread)
        self.submit_button.grid(row=1, column=1, columnspan=2, sticky="nsew", padx=(5, 0), pady=0)

    # Run the parser logic in a separate thread (to avoid freezing the GUI)
    def run_parser_thread(self):
        message = self.text_input.get("1.0", tk.END).strip()
        if not message:
            return
        mode = self.selected_option.get()
        self.controller.disable_buttons()
        thread = threading.Thread(target=self.run_async_parse, args=(message, mode))
        self.text_input.delete("1.0", tk.END)
        thread.start()

    # Run async parser and update the GUI with the result
    def run_async_parse(self, message, mode):
        result = asyncio.run(self.controller.parser.parse(message, mode))
        self.controller.main_frame.display_output(message, result)
        self.controller.sidebar.update_stats()



class ConfigFrame(tk.LabelFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, text="Config Settings", font=("Arial", 10, "bold"))
        self.controller = controller

        db = ParserDB()
        self.config = db.get_all_config()
        db.close()

        # Grid behavior for config_frame
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)

        # Configuration settings (Dynamically added from config)
        self.config_fields = DEFAULT_CONFIG
        self.config_vars = {}
        for idx, field in enumerate(self.config_fields):
            tk.Label(self, text=field["label"] + ":").grid(row=idx, column=0, sticky="w", padx=5, pady=2)
            value = int(self.config[field["key"]]) if field["type"] == int else str(self.config[field["key"]])
            if field["type"] == int:
                var = tk.IntVar(value=value)
            else:
                var = tk.StringVar(value=value)
            self.config_vars[field["key"]] = var
            tk.Entry(self, textvariable=var, width=10).grid(row=idx, column=1, sticky="w", padx=5, pady=2)

        # Save config changes on button click
        self.save_config_button = tk.Button(
            self, text="Save",
            command=self.save_config)
        self.save_config_button.grid(row=0, column=2, columnspan=2, pady=(5, 2))

        # Reset configs on button click
        self.reset_config_button = tk.Button(
            self, text="Reset to Defaults",
            command=self.reset_to_defaults,
            bg="#555555", fg="white"
        )
        self.reset_config_button.grid(row=1, column=2, columnspan=2, pady=(0, 5))

    # Save user config inputs (resets to defualt values if type error)
    def save_config(self):
        self.controller.disable_buttons()

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
            setattr(self.controller.parser, field["key"], field["type"](self.config[field["key"]]))
            
        self.controller.enable_buttons()


    def reset_to_defaults(self):
        for field in self.config_fields:
            self.config_vars[field["key"]].set(field["default"])



class MainArea(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Grid behavior for main_frame
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Child frames
        self.input_frame = InputFrame(self, controller)
        self.input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        self.config_frame = ConfigFrame(self, controller)
        self.config_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))        

        # Main title
        self.title_label = tk.Label(
            self, text="CHAT MESSAGE PARSER",
            font=("Arial", 18, "bold"))
        self.title_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))

        # Output area
        self.text_output = ScrolledText(
            self, state=tk.DISABLED,
            font=("Arial", 12))
        self.text_output.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

    def display_output(self, message, result):
        self.text_output.config(state=tk.NORMAL)

        now = datetime.now()
        formatted_date_time = now.strftime("%I:%M:%S %p")

        self.text_output.insert(tk.END, f" Message - {formatted_date_time}  \n {'━'*20} \n {message} \n\n JSON Output: \n")
        self.text_output.insert(tk.END, result)
        self.text_output.insert(tk.END, "\n\n")
        self.text_output.see(tk.END)
        self.text_output.config(state=tk.DISABLED)



class ParserGUI:
    def __init__(self, root):
        root.tk.call('tk', 'scaling', 2.0)
        self.parser = Parser()
        self.root = root
        self.root.title("Chat Message Parser")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)

        # Grid behavior for root (main window)
        self.root.grid_columnconfigure(0, weight=0, minsize=350) # Sidebar
        self.root.grid_columnconfigure(1, weight=1) # Main Area
        self.root.grid_rowconfigure(0, weight=1)

        # Sidebar (left)
        self.sidebar = Sidebar(self.root, self)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Main Area (right)
        self.main_frame = MainArea(self.root, self)
        self.main_frame.grid(row=0, column=1, sticky="nsew")

        self.buttons = [self.sidebar.clear_stats_button, self.main_frame.input_frame.submit_button, self.main_frame.config_frame.save_config_button]
        self.sidebar.update_stats() # Show stats from database on startup

    def disable_buttons(self):
        for btn in self.buttons:
            btn.config(state=tk.DISABLED)

    def enable_buttons(self):
        for btn in self.buttons:
            btn.config(state=tk.NORMAL)