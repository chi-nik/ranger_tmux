# -*- coding: utf-8 -*-
"""Performs the drop-down action in tmux.

Intended to be triggered by a keyboard-shortcut in tmux.
"""
import signal
import sys
import time

import psutil
import ranger
from ranger.container.settings import Settings
from ranger.core.fm import FM
from ranger.core.main import parse_arguments
from ranger.core.shared import FileManagerAware, SettingsAware

from ranger_tmux import util


def animated_resize(pane_id, target_perc, duration=200):
    """Animates the resizing a tmux pane."""
    pane_height = int(util.tmux("display", "-t", "{top}", "-p", "#{pane_height}"))
    window_height = int(util.tmux("display", "-p", "#{window_height}"))
    target_height = int(target_perc / 100 * window_height)
    direction = pane_height < target_height
    lines = int(duration < 500) + 1
    frames = max(1, abs(pane_height - target_height) // lines - 1)
    timeout = duration / 1000 / frames
    for _ in range(frames):
        util.tmux("resize-pane", "-D" if direction else "-U", "-t", pane_id, lines)
        time.sleep(timeout)
    util.tmux("resize-pane", "-t", pane_id, "-y", f"{target_perc}%")

def jumpt_to_ranger():
    #print(sys.path)
    # Get Ranger panel,window Intended

    this_pane_id = util.tmux( "display", "-p", "#{pane_id}")
    # TODO: ranger_tmux_pane should be set by ranger on startup
    ranger_pane_id = util.tmux( "show", "-v", "@ranger_tmux_pane")
    last_pane_id = util.tmux( "show", "-v", "@ranger_tmux_last_pane")
    # We are in ranger
    if ranger_pane_id == this_pane_id:
        if last_pane_id:
            util.tmux("send-keys", "-t", this_pane_id, ':')
            util.tmux("send-keys", "-t", this_pane_id, 'tmux_cwd_jump')
            util.tmux("send-keys", "-t", this_pane_id, 'Enter')
            pane_id = util.tmux(
                "select-window", "-t", last_pane_id)
            pane_id = util.tmux(
                "select-pane", "-t", last_pane_id)
    # we are outside
    else:
        pane_dir = util.tmux(
            "display-message", "-p", "#{pane_current_path}")
        util.tmux("set","@ranger_tmux_last_pane", this_pane_id)
        pane_id = util.tmux("select-window", "-t",ranger_pane_id)
        pane_id = util.tmux("select-pane", "-t",ranger_pane_id)
        util.tmux("send-keys", ':')
        util.tmux("send-keys", 'cd {}'.format(pane_dir))
        util.tmux("send-keys", "Enter")




    ## switch back to tmux
    #pane_id = util.tmux(
    #    "last-window",
    #)


    # opt: no
    # opt:
def main():
    """Launches ranger in a new pane, optionally driving pane animation."""
    ranger_script_path = util.get_ranger_script()

    # Initiate ranger just enough to allow us to access the settings
    ranger.args = parse_arguments()
    fm = FM()
    SettingsAware.settings_set(Settings())
    FileManagerAware.fm_set(fm)
    ranger.core.main.load_settings(fm, clean=False)

    # Check we're actually in tmux
    if not util.check_tmux(fm):
        sys.exit()

    # Check if we need to animate the drop
    animate = fm.settings.get("tmux_dropdown_animate")
    duration = fm.settings.get("tmux_dropdown_duration")

    pane_id, command, pid = util.tmux(
        "display", "-t", "{top}", "-p", "#{pane_id}|#{pane_start_command}|#{pane_pid}"
    ).split("|")

    # Ranger is open - we will close it
    if command == f"{sys.executable} {ranger_script_path} -- .":
        # Animate close if wanted
        if animate:
            animated_resize(pane_id, 0, duration)
        # Get a handel on ranger
        process = psutil.Process(int(pid))
        # Send interupt to ranger to cancel any unfinished command entry
        process.send_signal(signal.SIGINT)
        # Ask ranger to quit nicely
        util.tmux("send-keys", "-t", pane_id, "Q")
        # Give range half a second to quit before vicously killing it
        dead, alive = psutil.wait_procs([process], timeout=0.5)
        for p in alive:
            p.kill()

    # Ranger is not open - we will open it
    else:
        # Load ranger pane height from ranger settings
        percent = fm.settings.get("tmux_dropdown_percent")
        # Make initial size smaller if we're going to animate
        initial_size = "1" if animate else f"{percent}%"
        # Get other pane folder
        pane_dir = util.tmux(
            "display-message", "-p", "-t", pane_id, "#{pane_current_path}"
        )
        # Create a new ranger pane
        pane_id = util.tmux(
            "split-window",
            "-bfv",
            "-F",
            "#{pane_id}",
            "-c",
            pane_dir,
            "-t",
            "{top}",
            "-l",
            initial_size,
            sys.executable,
            ranger_script_path,
            "--",
            ".",
        )
        # Animate open if wanted
        if animate:
            animated_resize(pane_id, percent, duration)


if __name__ == "__main__":
    #main()
    jumpt_to_ranger()
