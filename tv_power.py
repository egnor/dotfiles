#!/usr/bin/env python3

import argparse
import cec
import dbus
import dbus.mainloop.glib
import gi.repository.GLib
import signal
import socket
import sys
import time


class ScreenSaverListener:
    def __init__(self, debug=False):
        dbus_loop = dbus.mainloop.glib.DBusGMainLoop()
        self._debug = debug
        self._dbus = dbus.SessionBus(mainloop=dbus_loop)
        self._loop = gi.repository.GLib.MainLoop()

        self.screensaver_active = None
        self.display_powersave = None

        self._dbus.add_signal_receiver(
            handler_function=self._on_displayconfig,
            signal_name='PropertiesChanged',
            dbus_interface='org.freedesktop.DBus.Properties',
            bus_name=None,
            path='/org/gnome/Mutter/DisplayConfig')

        self._dbus.add_signal_receiver(
            handler_function=self._on_screensaver_wakeup,
            signal_name='WakeUpScreen',
            dbus_interface='org.gnome.ScreenSaver',
            bus_name=None,
            path='/org/gnome/ScreenSaver')

        self._dbus.add_signal_receiver(
            handler_function=self._on_screensaver_activechanged,
            signal_name='ActiveChanged',
            dbus_interface='org.gnome.ScreenSaver',
            bus_name=None,
            path='/org/gnome/ScreenSaver')

    def _on_screensaver_wakeup(self):
        if self._debug:
            print(f'DBUS ScreenSaver WakeUpScreen', file=sys.stderr)
        self.screensaver_active = False
        self._loop.quit()

    def _on_screensaver_activechanged(self, active):
        if self._debug:
            print(f'DBUS ScreenSaver ActiveChanged:', active, file=sys.stderr)
        self.screensaver_active = bool(active)
        self._loop.quit()

    def _on_displayconfig(self, interface, changed, invalid):
        if self._debug:
            changed_py = {str(k): int(v) for k, v in changed.items()}
            print(f'DBUS DisplayConfig:', changed_py, file=sys.stderr)
        powersave = changed.get('PowerSaveMode')
        if powersave is not None:
            self.display_powersave = int(powersave)
            self._loop.quit()

    def wait_for_signal(self):
        if self._debug:
            print('DBUS waiting...', file=sys.stderr)
        self._loop.run()


class CecController:
    def __init__(self, debug=False):
        self._debug = debug
        self._config = cec.libcec_configuration()  # Object must remain
        self._config.strDeviceName = socket.gethostname()
        self._config.deviceTypes.Add(cec.CEC_DEVICE_TYPE_PLAYBACK_DEVICE)
        self._config.SetLogCallback(self._cec_log_callback)

        if self._debug:
            print("CEC === initializing ===", file=sys.stderr)
        self._adapter_open = None
        self._lib = cec.ICECAdapter.Create(self._config)
        if not self._lib:
            raise IOError("ICECAdapter.Create failed")


    def set_power(self, power_on):
        if self._adapter_open:
            try:
                self._send_set_power(power_on)
                return
            except IOError as e:
                print(f"*** {e} - retrying", file=sys.stderr)
                self._adapter_open = None
                self._lib.Close()

        if self._debug:
            print("CEC === detecting adapters ===", file=sys.stderr)
        adapters = self._lib.DetectAdapters()
        if not adapters:
            raise FileNotFoundError("No CEC adapters found")
        if not self._lib.Open(adapters[0].strComName):
            raise IOError("CEC adapter Open failed")

        self._adapter_open = adapters[0]
        if self._debug:
            name = self._adapter_open.strComName
            print(f"CEC === using adapter: {name} ===", file=sys.stderr)

        self._send_set_power(power_on)

    def _send_set_power(self, power_on):
        if power_on:
            if self._debug:
                print(f"CEC === sending PowerOnDevices ===", file=sys.stderr)
            if not self._lib.PowerOnDevices(cec.CECDEVICE_TV):
                raise IOError("CEC PowerOnDevices failed")
        else:
            if self._debug:
                print(f"CEC === sending StandbyDevices ===", file=sys.stderr)
            if not self._lib.StandbyDevices(cec.CECDEVICE_TV):
                raise IOError("CEC StandbyDevices failed")

    def _cec_log_callback(self, level, time, message):
        prefix = {
            getattr(cec, f"CEC_LOG_{level}"): level
            for level in ["ERROR", "WARNING", "NOTICE", "TRAFFIC", "DEBUG"]
        }

        if self._debug or level <= cec.CEC_LOG_WARNING:
            print(f"CEC {prefix.get(level, level)} {message}", file=sys.stderr)


signal.signal(signal.SIGINT, signal.SIG_DFL)  # Sane ^C behavior.

parser = argparse.ArgumentParser()
parser.add_argument('--debug_cec', action='store_true')
parser.add_argument('--debug_dbus', action='store_true')

mode_group = parser.add_mutually_exclusive_group(required=True)
mode_group.add_argument('--off', action='store_true')
mode_group.add_argument('--on', action='store_true')
mode_group.add_argument('--dbus', action='store_true')
args = parser.parse_args()

controller = CecController(debug=args.debug_cec)
if args.off:
    controller.set_power(False)
elif args.on:
    controller.set_power(True)
elif args.dbus:
    listener = ScreenSaverListener(debug=args.debug_dbus)
    last_on = time.time()
    controller.set_power(True)
    while True:
        listener.wait_for_signal()
        now = time.time()
        if listener.display_powersave and listener.screensaver_active:
            if args.debug_dbus:
                print("DBUS --- screensaver powersave; no action ---")
        elif now - last_on < 10.0:
            if args.debug_dbus:
                print(f"DBUS --- on {now - last_on:.1f}s ago, no action ---")
        else:
            if args.debug_dbus:
                print(f"DBUS => CEC === WAKE UP ===")
            try:
                controller.set_power(True)
                last_on = now
            except IOError as e:
                print(f"*** {e}", file=sys.stderr)
