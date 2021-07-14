#!/usr/bin/env python3

import argparse
import ctypes
import dbus
import dbus.mainloop.glib
import gi.repository.GLib
import sys
import time


libcec = ctypes.CDLL("libcec.so.6")

def set_tv(state):
    class cec_configuration(ctypes.Structure):
        _fields_ = [
            ("clientVersion", ctypes.c_uint32),
            ("strDeviceName", ctypes.c_char * 15),
            ("deviceTypes", ctypes.c_int * 5),
            ("padding", ctypes.c_uint8 * 1024),
        ]

    class cec_adapter_descriptor(ctypes.Structure):
        _fields_ = [
        ]

    config = cec_configuration()
    libcec.libcec_clear_configuration(ctypes.byref(config))
    config.strDeviceName = b"tv_power.py"
    config.deviceTypes[0] = 4  # CEC_DEVICE_TYPE_PLAYBACK_DEVICE
    libcec.libcec_initialise.restype = ctypes.c_void_p
    conn = libcec.libcec_initialise(ctypes.byref(config))


    print(type(conn))
    # lib = cec.ICECAdapter.Create(config)
    # adapters = lib.DetectAdapters(ctypes.c_char_p(), True)
    # for adapter in adapters:
    #     print(adapter.strComPath)


class ScreenSaverListener:
    def __init__(self, debug=False):
        dbus_loop = dbus.mainloop.glib.DBusGMainLoop()
        self._debug = debug
        self._dbus = dbus.SessionBus(mainloop=dbus_loop)
        self._loop = gi.repository.GLib.MainLoop()
        self._dbus.add_signal_receiver(
            handler_function=self._signal_callback,
            signal_name=None,
            dbus_interface='org.gnome.ScreenSaver',
            bus_name=None,
            path='/org/gnome/ScreenSaver',
            member_keyword='member')

        self.blanked = None

    def _signal_callback(self, *args, member=None):
        if member == 'WakeUpScreen':
            self.blanked = False
        elif member == 'ActiveChanged':
            self.blanked = bool(args[0])
        if self._debug:
            blanked = "BLANKED" if self.blanked else "NONBLANK"
            print(f'=== ScreenSaver {active}:', member, args, file=sys.stderr)
        self._loop.quit()

    def wait_for_signal(self):
        if self._debug:
            print('=== waiting for ScreenSaver dbus signal', file=sys.stderr)
        self._loop.run()


parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true')

mode_group = parser.add_mutually_exclusive_group(required=True)
mode_group.add_argument('--off', action='store_true')
mode_group.add_argument('--on', action='store_true')
mode_group.add_argument('--dbus', action='store_true')
args = parser.parse_args()

if args.off:
    set_tv(False)
elif args.on:
    set_tv(True)
elif args.dbus:
    listener = ScreenSaverListener(debug=args.debug)
    last_on = time.time()
    set_tv(True)
    while True:
        listener.wait_for_signal()
        now = time.time()
        if now > last_on + 10.0 and not listener.blanked:
            set_tv(True)
            last_on = now
