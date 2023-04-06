import tkinter as tk
from tkinter import ANCHOR, ttk
import configparser
import os
from antsim import start_sim
import threading
import psutil
import ctypes
import time

# Conversion
kb = float(1024)
mb = float(kb ** 2)
gb = float(kb ** 3)

USABLE_CPUS = len(psutil.Process().cpu_affinity())
memTotal = int(psutil.virtual_memory()[0]/gb)
memFree = int(psutil.virtual_memory()[1]/gb)
memPercent = int(psutil.virtual_memory()[2])
memUsed = int(psutil.virtual_memory()[3]/gb)
print(f'{memUsed}/{memTotal}GB, free:{memFree}GB ({memPercent}%)')

for i, percentage in enumerate(psutil.cpu_percent(percpu=True, interval=0)):
    print(f"Core {i}: {percentage}%")
# ctypes SetProcessDPIAware required for correct resolution (tkinter winfo_screenwidth is not aware of scaling)
user32 = ctypes.windll.user32
user32.SetProcessDPIAware()
[SCREEN_W, SCREEN_H] = [user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)]

# load the settings from the config file if it exists
config = configparser.ConfigParser()
if os.path.exists("settings.ini"):
    config.read('settings.ini')
    WINDOW_HEIGHT = int(config.get('UI-Window', 'WINDOW_HEIGHT'))
    WINDOW_WIDTH = int(config.get('UI-Window', 'WINDOW_WIDTH'))
    
def update_core_usage(bar, core):
    while True:
        bar['value'] = psutil.cpu_percent(percpu=True, interval=1)[core]
        bar.label['text'] = f'#{core} ({psutil.cpu_percent(percpu=True, interval=1)[core]}%)'
        time.sleep(0.3)
        
def print_thread_status():
    while True:
        for thread in threading.enumerate():
            print(f"{thread.name}: {thread.is_alive()}")
        time.sleep(0.3)
                
class MyUI:
    def __init__(self):
        # Init
        self.root = tk.Tk()
        self.root.title("PySim - Simulations")
        self.root.geometry(f'{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{round(SCREEN_W/2-WINDOW_WIDTH/2)}+{round(SCREEN_H/2-WINDOW_HEIGHT/2)}')
        self.root.resizable(False, False)

        # Create a Notebook
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill=tk.BOTH,expand=True)

        # FRAME-TAB: General
        frame_general = ttk.Frame(self.nb)
        frame_general.pack(fill=tk.BOTH)

        label1 = tk.Label(frame_general, text="Setting 1:", bg="green")
        label1.pack(fill=tk.BOTH, expand=True)

        # create the save button
        save_button = ttk.Button(frame_general, text="Save", command=self.save_settings)

        # Add Frames to Notebook
        self.nb.add(frame_general, text="General")

        # Create a Status-Bar
        self.sb = ttk.Frame(self.root)
        self.sb.pack(fill=tk.X)

        # create the start button
        start_button = ttk.Button(self.sb, text="Start", command=self.start_antsim)
        start_button.grid(row=0, pady=5, padx=5, sticky=tk.E, columnspan=24)

        self.bars = {}
        j = 0
        for i in range(USABLE_CPUS):
            self.bars[i] = ttk.Progressbar(
                self.sb,
                orient='horizontal',
                mode='determinate',
                value=20,
                length=round(WINDOW_WIDTH/(USABLE_CPUS/2)-4))
            if i >= USABLE_CPUS/2:
                self.bars[i].row = 2
                self.bars[i].col = j
                j += 1
            else:
                self.bars[i].row = 1
                self.bars[i].col = i

            self.bars[i].label = tk.Label(
                self.sb,
                font=("Arial", 6),
                text=f'#{i} (0.0%)')

            self.bars[i].label.grid(row=self.bars[i].row, column=self.bars[i].col, sticky=tk.E)
            self.bars[i].grid(row=self.bars[i].row, column=self.bars[i].col, padx=2, pady=2)
            print(self.bars[i].row, self.bars[i].col)
            
        self.start_threads()

    def start_threads(self):
        # start a new thread for each core
        core_threads = {}
        for i in self.bars:
            core_threads[i] = threading.Thread(target=update_core_usage, args=(self.bars[i],i,), name=f'Core{i}-Thread')
            core_threads[i].daemon = True
            core_threads[i].start()
            
        # Start a new thread for thread-status
        status_thread = threading.Thread(target=print_thread_status, name='Status-Thread')
        status_thread.daemon = True
        #status_thread.start()
        
        #thread = threading.Thread(target=start_pygame, name="start_pygame")
        #thread.start()
        
    def start_antsim(self):
        antsim_thread = threading.Thread(target=start_sim, name="Antsim-THread")
        antsim_thread.start()
        
    def save_settings(self):
        # save the settings to the config file
        config = configparser.ConfigParser()
        config["Settings"] = {"setting1": self.entry1.get(), "setting2": self.entry2.get()}
        with open("settings.ini", "w") as config_file:
            config.write(config_file)
    
    def run(self):
        self.root.mainloop()
    
ui = MyUI()
ui.run()
