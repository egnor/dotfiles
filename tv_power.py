#!/usr/bin/env python3

import argparse
import cec
import dbus
import dbus.mainloop.glib
import gi.repository.GLib
import socket
import sys
import time



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


class CecController:
    def __init__(self, debug=False):
        self._debug = debug

        config = cec.libcec_configuration()
        config.strDeviceName = socket.gethostname()
        config.deviceTypes.Add(cec.CEC_DEVICE_TYPE_PLAYBACK_DEVICE)
        config.setLogCallback(self._cec_log_callback)

        self._adapter_open = None
        self._lib = cec.ICECAdapter.Create(config)
        if not self._lib:
            raise IOError("ICECAdapter.Create failed")

    def set_power(power_on):
        if self._adapter_open:
            try:
                self._send_set_power(power_on)
            except IOError as e:
                print(f"*** {e} - retrying", file=sys.stderr)
                self._adapter_open = None
                lib.Close()

        adapters = self._lib.DetectAdapters()
        if not adapters:
            raise FileNotFoundError("No CEC adapters found")
        if not lib.Open(adapters[0].strComName):
            raise IOError("CEC adapter Open failed")

        self._adapter_open = adapters[0]
        if self._debug:
            name = self._adapter_open.strComName
            print(f"=== Using CEC adapter: {name}", file=sys.stderr)

        self._send_set_power(power_on)

    def _send_set_power(power_on):
        if power_on:
            if self._debug:
                print(f"=== Sending CEC PowerOnDevices", file=sys.stderr)
            if not self._lib.PowerOnDevices(cec.CECDEVICE_TV):
                raise IOError("CEC PowerOnDevices failed")
        else:
            if self._debug:
                print(f"=== Sending CEC StandbyDevices", file=sys.stderr)
            if not self._lib.StandbyDevices(cec.CECDEVICE_TV):
                raise IOError("CEC StandbyDevices failed")

    def _cec_log_callback(self, level, time, message):
        prefix = {
            getattr(cec, f"CEC_LOG_{level}"): level
            for level in ["ERROR", "WARNING", "NOTICE", "TRAFFIC", "DEBUG"]
        }

        if self._debug or level >= cec.CEC_LOG_WARNING:
            print(f"CEC {prefix.get(level, level)}: {message}", file=sys.stderr)


parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true')

mode_group = parser.add_mutually_exclusive_group(required=True)
mode_group.add_argument('--off', action='store_true')
mode_group.add_argument('--on', action='store_true')
mode_group.add_argument('--dbus', action='store_true')
args = parser.parse_args()

cec = CecController(debug=args.debug)
if args.off:
    cec.set_power(False)
elif args.on:
    cec.set_power(True)
elif args.dbus:
    listener = ScreenSaverListener(debug=args.debug)
    last_on = time.time()
    cec.set_power(True)
    while True:
        listener.wait_for_signal()
        now = time.time()
        if now > last_on + 10.0 and not listener.blanked:
            try:
                cec.set_power(True)
                last_on = now
            except IOError as e:
                print(f"*** {e}", file=sys.stderr)
