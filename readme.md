# Smart Light Monitor

A simple Python Tkinter dashboard demonstrating an Arduino-based automatic light detection system using simulated sensor readings.

**Note:** All readings are simulated locally in Python. The dashboard does not connect to an Arduino or Tinkercad.

## Features
- Manual light-level control (0–1023)
- Automatic sensor reading simulation
- LED ON/OFF status
- Live statistics and reading history
- Graphs and CSV export

## LED Control Logic

| Light Reading | LED Status |
|---|---|
| Below 450 | ON |
| 450–550 | Maintain previous state |
| Above 550 | OFF |

Hysteresis helps prevent rapid LED switching.

## Requirements
- Python 3
- Tkinter

### Linux (Ubuntu/Debian)
If Tkinter is missing, install it via terminal:

sudo apt update
sudo apt install python3-tk


### Windows
Tkinter is normally bundled with the standard Python installer. If it is missing, run the Python installer again, choose **Modify**, and make sure **tcl/tk and IDLE** is checked.

## Run

python monitor.py
