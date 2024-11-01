'''Windows functions'''
# pylint: disable=import-outside-toplevel
# pylint: disable=line-too-long
# pep8: disable=line-too-long
# flake8: noqa

import os
import sys
import time
import threading
import ctypes
import subprocess
import msvcrt
import signal
import psutil

# The frequency to check the child process' `cwd` and update our own
CWD_UPDATE_INTERVAL = 1 / 4


def create_cwd_watcher(pid):
    '''
    Creates a daemon thread that checks the `cwd` of a process, then updates the
    `cwd` of the current process.

    Args:
        pid (int): PID of the process whose `cwd` is checked.
    '''
    def update_cwd():
        try:
            child_process = psutil.Process(pid)
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return

        while True:
            try:
                time.sleep(CWD_UPDATE_INTERVAL)
                os.chdir(child_process.cwd())
            except (OSError, psutil.AccessDenied, psutil.NoSuchProcess):
                break  # Exit loop if the process no longer exists

    threading.Thread(target=update_cwd, daemon=True).start()


def get_stdin():
    '''Returns stdin for compatibility.'''
    return sys.stdin


def run_program(program_args):
    '''
    Runs a program on Windows, setting up pipes for input/output.

    Args:
        program_args (list): A list of program arguments.
    '''
    # Use Popen for creating a bidirectional pipe
    process = subprocess.Popen(
        program_args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )

    # Handle terminal raw mode (similar to `tty.setraw`)
    if sys.stdin.isatty():
        # Equivalent to raw mode handling
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)

    def window_resize_handler(*_):
        '''Windows version of terminal resize handler.'''
        # Adjust the size of the console window if needed
        h = ctypes.windll.kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE
        csbi = ctypes.create_string_buffer(22)

        if ctypes.windll.kernel32.GetConsoleScreenBufferInfo(h, csbi):
            left, top, right, bottom = struct.unpack("hhhh", csbi.raw[10:18])
            columns, rows = right - left + 1, bottom - top + 1

            # This is where resizing would happen if needed
            # For example: ctypes.windll.kernel32.SetConsoleScreenBufferSize(...)

    # Set up a signal handler for resizing
    if sys.stdin.isatty():
        # signal.signal(signal.SIGWINCH, window_resize_handler)
        window_resize_handler()

    # Create cwd watcher
    create_cwd_watcher(process.pid)

    return process, process.stdin, process.stdout
