
from __future__ import annotations

import csv
import random
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Any


# Settings (constants are written in CAPITAL_LETTERS and never change)

LED_ON_BELOW = 450
LED_OFF_ABOVE = 550
MAX_READING = 1023
START_READING = 800  # slider position when the program opens (bright)

SIMULATION_MIN_MS = 1000  # shortest wait between automatic readings
SIMULATION_MAX_MS = 2000  # longest wait between automatic readings

# Ranges used to create "dark", "transition" and "bright" readings
DARK_RANGE = (0, 400)
TRANSITION_RANGE = (450, 550)
BRIGHT_RANGE = (600, MAX_READING)
ZONE_NAMES = ("Dark", "Transition", "Bright")

MAX_RECORDS = 1000      # oldest readings are dropped after this many
MAX_TABLE_ROWS = 100    # rows kept in the history table
GRAPH_POINTS = 25       # readings shown on the line graph

# Graph sizes in pixels
LINE_GRAPH_WIDTH = 430
LINE_GRAPH_HEIGHT = 150
GRAPH_MARGIN = 18
BAR_GRAPH_WIDTH = 430
BAR_GRAPH_HEIGHT = 100
BAR_LABEL_WIDTH = 90
BAR_MAX_LENGTH = 280

# Fonts and colours
FONT = "Helvetica"
COLOR_BACKGROUND = "#f1f5f9"
COLOR_CARD = "#ffffff"
COLOR_TEXT = "#0f172a"
COLOR_MUTED = "#64748b"
COLOR_LED_ON = "#16a34a"
COLOR_LED_OFF = "#475569"
COLOR_START = "#2563eb"
COLOR_STOP = "#dc2626"
COLOR_BANNER = "#fef3c7"
COLOR_ROW_ON = "#dcfce7"
COLOR_ROW_OFF = "#e2e8f0"
ZONE_COLORS = {"Dark": "#334155", "Transition": "#f59e0b", "Bright": "#38bdf8"}

# A "record" is one stored reading: a dictionary with the keys
# number, time, reading, zone, led_on, switched and source.
Record = dict[str, Any]

# ---------------------------------------------------------------------------
# Program memory
# ---------------------------------------------------------------------------
state: dict[str, Any] = {
    "led_is_on": False,        # previous LED state (needed for hysteresis)
    "simulation_running": False,
    "next_step_id": None,      # id of the scheduled next simulation step
    "records": [],             # list of Record dictionaries
    "total_recorded": 0,       # readings recorded since the last reset
}

# All Tkinter widgets that functions need to update are stored here.
ui: dict[str, Any] = {}

#  LOGIC
# ===========================================================================
def decide_led_state(reading: int, previous_led_is_on: bool) -> tuple[bool, str]:
    #Return (led_is_on, explanation) for one light reading.
    if reading < LED_ON_BELOW:
        return True, 
    if reading > LED_OFF_ABOVE:
        return False,
    return previous_led_is_on, 


def classify_zone(reading: int) -> str:
    #Name the light zone of a reading (used for labels and graphs only)."""
    if reading < LED_ON_BELOW:
        return "Dark"
    if reading > LED_OFF_ABOVE:
        return "Bright"
    return "Transition"


def make_simulated_reading() -> int:
    #Pick dark, transition or bright at random and return a reading in it.
    zone = random.choice(ZONE_NAMES)
    if zone == "Dark":
        return random.randint(*DARK_RANGE)
    if zone == "Transition":
        return random.randint(*TRANSITION_RANGE)
    return random.randint(*BRIGHT_RANGE)


def create_record(number: int, reading: int, led_on: bool,
                  switched: bool, source: str) -> Record:
    #Bundle everything known about one reading into a dictionary."""
    return {
        "number": number,
        "time": datetime.now().strftime("%H:%M:%S"),
        "reading": reading,
        "zone": classify_zone(reading),
        "led_on": led_on,
        "switched": switched,
        "source": source,
    }


def calculate_statistics(records: list[Record]) -> dict[str, Any] | None:
    #Summarise a list of records. Returns None when the list is empty."""
    if not records:
        return None

    readings = [record["reading"] for record in records]
    zone_counts = {zone: 0 for zone in ZONE_NAMES}
    for record in records:
        zone_counts[record["zone"]] += 1

    led_on_total = sum(1 for record in records if record["led_on"])
    return {
        "count": len(records),
        "latest": readings[-1],
        "average": round(sum(readings) / len(readings)),
        "minimum": min(readings),
        "maximum": max(readings),
        "led_on_percent": round(led_on_total / len(records) * 100),
        "switches": sum(1 for record in records if record["switched"]),
        "zones": zone_counts,
    }


def led_text(led_on: bool) -> str:
    #Return 'ON' or 'OFF' for display."""
    return "ON" if led_on else "OFF"


def export_history_csv(records: list[Record], path: str) -> None:
    #Write the records to a CSV file that Excel can open."""
    with open(path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["No.", "Time", "Reading", "Zone", "LED",
                         "LED switched", "Source"])
        for record in records:
            writer.writerow([
                record["number"], record["time"], record["reading"],
                record["zone"], led_text(record["led_on"]),
                "Yes" if record["switched"] else "No", record["source"],
            ])



#  SCREEN UPDATES
# ===========================================================================
def apply_reading(reading: int) -> None:
    #Run the control logic for one reading and refresh the LED display."""
    led_is_on, explanation = decide_led_state(reading, state["led_is_on"])
    state["led_is_on"] = led_is_on

    ui["reading_label"].config(text=str(reading))
    ui["explanation_label"].config(text=explanation)
    if led_is_on:
        ui["status_label"].config(text="LED ON", bg=COLOR_LED_ON)
    else:
        ui["status_label"].config(text="LED OFF", bg=COLOR_LED_OFF)


def on_slider_moved(value_text: str) -> None:
    #Tkinter calls this whenever the slider changes (value arrives as text)."""
    apply_reading(int(float(value_text)))


def reading_to_y(reading: int) -> float:
    #Convert a reading (0-1023) to a vertical pixel position on the line graph."""
    usable_height = LINE_GRAPH_HEIGHT - 2 * GRAPH_MARGIN
    return LINE_GRAPH_HEIGHT - GRAPH_MARGIN - reading / MAX_READING * usable_height


def draw_line_graph(records: list[Record]) -> None:
    #Draw the most recent readings as dots joined by a line."""
    canvas = ui["line_canvas"]
    canvas.delete("all")

    for threshold in (LED_ON_BELOW, LED_OFF_ABOVE):
        y = reading_to_y(threshold)
        canvas.create_line(0, y, LINE_GRAPH_WIDTH, y, fill=COLOR_MUTED, dash=(4, 3))
        canvas.create_text(LINE_GRAPH_WIDTH - 4, y - 7, text=str(threshold),
                           anchor="e", fill=COLOR_MUTED, font=(FONT, 8))

    spacing = (LINE_GRAPH_WIDTH - 2 * GRAPH_MARGIN) / (GRAPH_POINTS - 1)
    previous_point = None
    for position, record in enumerate(records):
        x = GRAPH_MARGIN + position * spacing
        y = reading_to_y(record["reading"])
        if previous_point is not None:
            canvas.create_line(*previous_point, x, y, fill=COLOR_START, width=2)
        dot_color = COLOR_LED_ON if record["led_on"] else COLOR_LED_OFF
        canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=dot_color, outline="white")
        previous_point = (x, y)


def draw_zone_bars(zone_counts: dict[str, int]) -> None:
    #Draw one horizontal bar per light zone (how often each occurred)."""
    canvas = ui["bar_canvas"]
    canvas.delete("all")

    largest = max(zone_counts.values()) or 1  # avoid dividing by zero
    for row, zone in enumerate(ZONE_NAMES):
        top = 8 + row * 30
        length = zone_counts[zone] / largest * BAR_MAX_LENGTH
        canvas.create_text(6, top + 10, text=zone, anchor="w",
                           fill=COLOR_TEXT, font=(FONT, 10))
        canvas.create_rectangle(BAR_LABEL_WIDTH, top, BAR_LABEL_WIDTH + length,
                                top + 20, fill=ZONE_COLORS[zone], outline="")
        canvas.create_text(BAR_LABEL_WIDTH + length + 6, top + 10,
                           text=str(zone_counts[zone]), anchor="w",
                           fill=COLOR_TEXT, font=(FONT, 10, "bold"))


def refresh_statistics() -> None:
    #Recalculate the statistics and redraw the tiles and both graphs."""
    stats = calculate_statistics(state["records"])
    ui["counter_label"].config(text=str(state["total_recorded"]))

    if stats is None:
        values = {key: "-" for key in
                  ("latest", "average", "minimum", "maximum", "led_on", "switches")}
        zone_counts = {zone: 0 for zone in ZONE_NAMES}
    else:
        values = {
            "latest": str(stats["latest"]),
            "average": str(stats["average"]),
            "minimum": str(stats["minimum"]),
            "maximum": str(stats["maximum"]),
            "led_on": f"{stats['led_on_percent']}%",
            "switches": str(stats["switches"]),
        }
        zone_counts = stats["zones"]

    for key, text in values.items():
        ui[f"{key}_value"].config(text=text)
    draw_line_graph(state["records"][-GRAPH_POINTS:])
    draw_zone_bars(zone_counts)


def add_history_row(record: Record) -> None:
    """Insert a record at the top of the history table."""
    tree = ui["history_table"]
    tag = "on" if record["led_on"] else "off"
    tree.insert("", 0, tags=(tag,), values=(
        record["number"], record["time"], record["reading"], record["zone"],
        led_text(record["led_on"]), record["source"]))

    rows = tree.get_children()
    if len(rows) > MAX_TABLE_ROWS:
        tree.delete(rows[-1])  # remove the oldest row (bottom of the table)


# PART 3 - ACTIONS (what happens when buttons are pressed)
# ===========================================================================
def record_reading(reading: int, source: str) -> None:
    #Show a reading, store it in the history and update the statistics."""
    led_before = state["led_is_on"]
    # slider.set() triggers on_slider_moved(), which runs the control logic.
    ui["slider"].set(reading)
    led_after = state["led_is_on"]

    state["total_recorded"] += 1
    record = create_record(state["total_recorded"], reading, led_after,
                           led_after != led_before, source)
    state["records"].append(record)
    if len(state["records"]) > MAX_RECORDS:
        del state["records"][0]

    add_history_row(record)
    refresh_statistics()


def run_simulation_step() -> None:
    #Create one reading, record it, then schedule the next step."""
    record_reading(make_simulated_reading(), "Auto")

    # root.after() asks Tkinter to call this function again later. There is
    # no sleep() or loop, so the window never freezes.
    delay = random.randint(SIMULATION_MIN_MS, SIMULATION_MAX_MS)
    state["next_step_id"] = ui["root"].after(delay, run_simulation_step)


def stop_simulation() -> None:
    #Cancel the waiting simulation step and update the button."""
    state["simulation_running"] = False
    if state["next_step_id"] is not None:
        ui["root"].after_cancel(state["next_step_id"])
        state["next_step_id"] = None
    ui["toggle_button"].config(text="Start Simulation", bg=COLOR_START)
    ui["simulation_label"].config(text="Simulation stopped")


def toggle_simulation() -> None:
    #Start or stop the automatic simulation (one button does both)."""
    if state["simulation_running"]:
        stop_simulation()
        return

    state["simulation_running"] = True
    ui["toggle_button"].config(text="Stop Simulation", bg=COLOR_STOP)
    ui["simulation_label"].config(text="Running: new reading every 1-2 seconds")
    run_simulation_step()


def reset_history() -> None:
    #Clear the stored readings, the table, the statistics and the graphs."""
    state["records"].clear()
    state["total_recorded"] = 0
    tree = ui["history_table"]
    tree.delete(*tree.get_children())
    refresh_statistics()


def export_history() -> None:
    #Ask where to save, then write the history to a CSV file."""
    if not state["records"]:
        messagebox.showinfo("Export history", "There are no readings to export yet.")
        return

    path = filedialog.asksaveasfilename(
        title="Save history as CSV", defaultextension=".csv",
        initialfile="light_history.csv", filetypes=[("CSV files", "*.csv")])
    if not path:  # the user pressed Cancel
        return

    try:
        export_history_csv(state["records"], path)
    except OSError as error:
        messagebox.showerror("Export failed", f"Could not save the file:\n{error}")
        return
    messagebox.showinfo("Export history", f"Saved {len(state['records'])} readings.")


def on_close() -> None:
    #Stop the simulation cleanly, then close the window."""
    stop_simulation()
    ui["root"].destroy()


# PART 4 - BUILDING THE WINDOW
# ===========================================================================
def make_card(parent: tk.Misc, title: str) -> tk.Frame:
    #Create a white box with a small heading and return it."""
    card = tk.Frame(parent, bg=COLOR_CARD, padx=16, pady=10)
    card.pack(fill="x", pady=5)
    tk.Label(card, text=title, font=(FONT, 10, "bold"),
             bg=COLOR_CARD, fg=COLOR_MUTED).pack(anchor="w")
    return card


def make_stat_tile(parent: tk.Misc, key: str, title: str, row: int, column: int) -> None:
    tile = tk.Frame(parent, bg=COLOR_BACKGROUND, padx=10, pady=4)
    tile.grid(row=row, column=column, padx=4, pady=4, sticky="nsew")
    tk.Label(tile, text=title, font=(FONT, 9),
             bg=COLOR_BACKGROUND, fg=COLOR_MUTED).pack()
    value_label = tk.Label(tile, text="-", font=(FONT, 16, "bold"),
                           bg=COLOR_BACKGROUND, fg=COLOR_TEXT)
    value_label.pack()
    ui[f"{key}_value"] = value_label


def build_header(root: tk.Tk) -> None:
    #Title, subtitle and the 'this is a simulation' notice."""
    tk.Label(root, text="Smart Light Monitor", font=(FONT, 22, "bold"),
             bg=COLOR_BACKGROUND, fg=COLOR_TEXT).pack()
    tk.Label(root, text="Arduino automatic light detection - demonstration",
             font=(FONT, 11), bg=COLOR_BACKGROUND, fg=COLOR_MUTED).pack()
    tk.Label(root, text="SIMULATION: all readings are simulated locally in Python. "
                        "",
             font=(FONT, 10, "bold"), bg=COLOR_BANNER, fg=COLOR_TEXT,
             padx=10, pady=6).pack(fill="x", pady=(8, 4))


def build_light_card(parent: tk.Misc) -> None:
    #Slider, current reading and the quick-test buttons."""
    card = make_card(parent, "LIGHT LEVEL (simulated analogRead(A0), 0-1023)")
    ui["reading_label"] = tk.Label(card, text="0", font=(FONT, 40, "bold"),
                                   bg=COLOR_CARD, fg=COLOR_TEXT)
    ui["reading_label"].pack()
    ui["slider"] = tk.Scale(card, from_=0, to=MAX_READING, orient="horizontal",
                            length=400, showvalue=False, bg=COLOR_CARD,
                            highlightthickness=0, command=on_slider_moved)
    ui["slider"].pack()
    tk.Label(card, text="Dark (0)  <----  drag the slider  ---->  Bright (1023)",
             font=(FONT, 9), bg=COLOR_CARD, fg=COLOR_MUTED).pack()

    quick_row = tk.Frame(card, bg=COLOR_CARD)
    quick_row.pack(pady=(8, 0))
    tk.Label(quick_row, text="Quick test (saved to history):", font=(FONT, 9),
             bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="left", padx=(0, 6))
    for test_value in (250, 400, 500, 600, 800):
        tk.Button(quick_row, text=str(test_value), width=4,
                  command=lambda value=test_value: record_reading(value, "Test")
                  ).pack(side="left", padx=2)


def build_status_card(parent: tk.Misc) -> None:
    #Big LED ON / LED OFF box and the explanation line."""
    card = make_card(parent, "LIGHTING STATUS")
    ui["status_label"] = tk.Label(card, text="LED OFF", font=(FONT, 28, "bold"),
                                  bg=COLOR_LED_OFF, fg="white", pady=10)
    ui["status_label"].pack(fill="x", pady=(4, 6))
    ui["explanation_label"] = tk.Label(card, text="", font=(FONT, 10),
                                       bg=COLOR_CARD, fg=COLOR_TEXT)
    ui["explanation_label"].pack()


def build_rules_card(parent: tk.Misc) -> None:
    #The three control rules."""
    card = make_card(parent, "CONTROL RULES (thresholds)")
    rules = (("Below 450   :  LED ON", COLOR_LED_ON),
             ("450 - 550    :  Maintain previous state", COLOR_MUTED),
             ("Above 550   :  LED OFF", COLOR_LED_OFF))
    for text, color in rules:
        tk.Label(card, text=text, font=(FONT, 11), bg=COLOR_CARD,
                 fg=color).pack(anchor="w")


def build_simulation_card(parent: tk.Misc) -> None:
    #Start/Stop button, status text and the readings counter."""
    card = make_card(parent, "AUTOMATIC SIMULATION")
    row = tk.Frame(card, bg=COLOR_CARD)
    row.pack(fill="x", pady=(4, 0))
    ui["toggle_button"] = tk.Button(
        row, text="Start Simulation", font=(FONT, 12, "bold"), bg=COLOR_START,
        fg="white", activebackground=COLOR_START, activeforeground="white",
        relief="flat", padx=16, pady=6, command=toggle_simulation)
    ui["toggle_button"].pack(side="left")

    info = tk.Frame(row, bg=COLOR_CARD)
    info.pack(side="left", padx=14)
    ui["simulation_label"] = tk.Label(info, text="Simulation stopped",
                                      font=(FONT, 10), bg=COLOR_CARD, fg=COLOR_MUTED)
    ui["simulation_label"].pack(anchor="w")
    counter_row = tk.Frame(info, bg=COLOR_CARD)
    counter_row.pack(anchor="w")
    tk.Label(counter_row, text="Readings recorded:", font=(FONT, 10),
             bg=COLOR_CARD, fg=COLOR_TEXT).pack(side="left")
    ui["counter_label"] = tk.Label(counter_row, text="0", font=(FONT, 12, "bold"),
                                   bg=COLOR_CARD, fg=COLOR_TEXT)
    ui["counter_label"].pack(side="left", padx=4)


def build_statistics_card(parent: tk.Misc) -> None:
    #Six live statistic tiles."""
    card = make_card(parent, "LIVE STATISTICS")
    tiles = tk.Frame(card, bg=COLOR_CARD)
    tiles.pack(fill="x")
    for column in range(3):
        tiles.columnconfigure(column, weight=1)
    make_stat_tile(tiles, "latest", "Latest reading", 0, 0)
    make_stat_tile(tiles, "average", "Average", 0, 1)
    make_stat_tile(tiles, "led_on", "LED ON time", 0, 2)
    make_stat_tile(tiles, "minimum", "Minimum", 1, 0)
    make_stat_tile(tiles, "maximum", "Maximum", 1, 1)
    make_stat_tile(tiles, "switches", "LED switches", 1, 2)


def build_graphs_tab(tab: tk.Frame) -> None:
    #Line graph of recent readings and a bar graph of light zones."""
    tk.Label(tab, text="Recent readings (green dot = LED ON, grey dot = LED OFF)",
             font=(FONT, 9), bg=COLOR_CARD, fg=COLOR_MUTED).pack(pady=(6, 2))
    ui["line_canvas"] = tk.Canvas(tab, width=LINE_GRAPH_WIDTH,
                                  height=LINE_GRAPH_HEIGHT,
                                  bg=COLOR_BACKGROUND, highlightthickness=0)
    ui["line_canvas"].pack()
    tk.Label(tab, text="How often each light zone occurred",
             font=(FONT, 9), bg=COLOR_CARD, fg=COLOR_MUTED).pack(pady=(8, 2))
    ui["bar_canvas"] = tk.Canvas(tab, width=BAR_GRAPH_WIDTH, height=BAR_GRAPH_HEIGHT,
                                 bg=COLOR_BACKGROUND, highlightthickness=0)
    ui["bar_canvas"].pack(pady=(0, 6))


def build_history_tab(tab: tk.Frame) -> None:
    #Scrollable table of every recorded reading (newest first)."""
    columns = (("no", "No.", 45), ("time", "Time", 75), ("reading", "Reading", 70),
               ("zone", "Zone", 90), ("led", "LED", 60), ("source", "Source", 65))
    table = ttk.Treeview(tab, columns=[name for name, _, _ in columns],
                         show="headings", height=11)
    for name, heading, width in columns:
        table.heading(name, text=heading)
        table.column(name, width=width, anchor="center")
    table.tag_configure("on", background=COLOR_ROW_ON)
    table.tag_configure("off", background=COLOR_ROW_OFF)

    scrollbar = ttk.Scrollbar(tab, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=scrollbar.set)
    table.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
    scrollbar.pack(side="left", fill="y", pady=6, padx=(0, 6))
    ui["history_table"] = table


def build_tabs(parent: tk.Misc) -> None:
    #Notebook with a Graphs tab and a History tab, plus the action buttons."""
    notebook = ttk.Notebook(parent)
    notebook.pack(fill="x", pady=5)
    graphs_tab = tk.Frame(notebook, bg=COLOR_CARD)
    history_tab = tk.Frame(notebook, bg=COLOR_CARD)
    notebook.add(graphs_tab, text="  Graphs  ")
    notebook.add(history_tab, text="  History  ")
    build_graphs_tab(graphs_tab)
    build_history_tab(history_tab)

    buttons = tk.Frame(parent, bg=COLOR_BACKGROUND)
    buttons.pack(fill="x")
    tk.Button(buttons, text="Export History (CSV)",
              command=export_history).pack(side="left")
    tk.Button(buttons, text="Reset History",
              command=reset_history).pack(side="left", padx=6)


def main() -> None:
    #Create the window, show the starting state and start Tkinter.
    root = tk.Tk()
    ui["root"] = root
    root.title("Smart Light Monitor")
    root.configure(bg=COLOR_BACKGROUND, padx=20, pady=14)
    root.resizable(False, False)
    root.protocol("WM_DELETE_WINDOW", on_close)

    build_header(root)
    left_column = tk.Frame(root, bg=COLOR_BACKGROUND)
    left_column.pack(side="left", anchor="n", padx=(0, 12))
    right_column = tk.Frame(root, bg=COLOR_BACKGROUND)
    right_column.pack(side="left", anchor="n")

    build_light_card(left_column)
    build_status_card(left_column)
    build_rules_card(left_column)
    build_simulation_card(right_column)
    build_statistics_card(right_column)
    build_tabs(right_column)

    refresh_statistics()            # draw the empty graphs
    ui["slider"].set(START_READING)  # show the starting reading
    root.mainloop()


if __name__ == "__main__":
    main()