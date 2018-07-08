# This file is executed on every boot (including wake-boot from deepsleep)
import esp
import gc

# Disable ESP debugging for ampy.
esp.osdebug(None)

# Garbage-collect after initialization.
gc.collect()
