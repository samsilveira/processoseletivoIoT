import machine
import time

class StatusLEDs:
    def __init__(self, pin_ok, pin_warn, pin_crit):
        self.led_ok = machine.Pin(pin_ok, machine.Pin.OUT)
        self.led_warn = machine.Pin(pin_warn, machine.Pin.OUT)
        self.led_crit = machine.Pin(pin_crit, machine.Pin.OUT)
        self.last_blink = 0
        self.blink_state = False

    def update(self, state):
        now = time.ticks_ms()
        
        # Define intervalos de pisca
        if state == "CRITICO":
            interval = 200
        elif state == "AVISO":
            interval = 600
        else:
            interval = 0 # Ligado direto

        if interval > 0:
            if time.ticks_diff(now, self.last_blink) > interval:
                self.blink_state = not self.blink_state
                self.last_blink = now
        else:
            self.blink_state = True

        if state == "OK":
            self.led_ok.value(1)
            self.led_warn.value(0)
            self.led_crit.value(0)
        elif state == "AVISO":
            self.led_ok.value(0)
            self.led_warn.value(1 if self.blink_state else 0)
            self.led_crit.value(0)
        elif state == "CRITICO":
            self.led_ok.value(0)
            self.led_warn.value(0)
            self.led_crit.value(1 if self.blink_state else 0)
