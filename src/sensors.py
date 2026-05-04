import machine
import time
import math
import micropython

# Pre-aloca o buffer para mensagens de erro de interrupção (boa prática)
micropython.alloc_emergency_exception_buf(100)

class AnalogSensor:
    def __init__(self, pin_num, conversion_fn, window_size=10):
        self.adc = machine.ADC(machine.Pin(pin_num))
        self.adc.atten(machine.ADC.ATTN_11DB)
        self.adc.width(machine.ADC.WIDTH_12BIT)
        self.conversion_fn = conversion_fn
        self.window_size = window_size
        self.buffer = []

    def read_raw(self):
        val = self.adc.read()
        self.buffer.append(val)
        if len(self.buffer) > self.window_size:
            self.buffer.pop(0)
        return sum(self.buffer) / len(self.buffer)

    def read(self):
        raw_avg = self.read_raw()
        return self.conversion_fn(raw_avg)

class PresenceSensor:
    def __init__(self, pin_num, timeout_ms=30000):
        self.pin = machine.Pin(pin_num, machine.Pin.IN)
        self.timeout_ms = timeout_ms
        self.last_presence_time = -timeout_ms - 1
        # Configura interrupção de hardware (IRQ)
        self.pin.irq(trigger=machine.Pin.IRQ_RISING, handler=self._irq_handler)

    def _irq_handler(self, pin):
        self.last_presence_time = time.ticks_ms()

    @property
    def is_present(self):
        return time.ticks_diff(time.ticks_ms(), self.last_presence_time) < self.timeout_ms

class Button:
    def __init__(self, pin_num, callback):
        self.pin = machine.Pin(pin_num, machine.Pin.IN, machine.Pin.PULL_UP)
        self.callback = callback
        self.last_press = 0
        self.pin.irq(trigger=machine.Pin.IRQ_FALLING, handler=self._irq_handler)

    def _deferred_callback(self, _):
        """Executa o callback original fora do contexto de interrupção."""
        self.callback()

    def _irq_handler(self, pin):
        """Handler de interrupção (Hard IRQ)."""
        now = time.ticks_ms()
        # Debounce simples
        if time.ticks_diff(now, self.last_press) > 200:
            self.last_press = now
            # Agenda a execução para o loop principal
            micropython.schedule(self._deferred_callback, None)

# Funções de Conversão estáticas

def ntc_to_celsius(raw_val):
    ADC_RES = 4095
    BETA = 3950
    if raw_val <= 0: raw_val = 1
    if raw_val >= ADC_RES: raw_val = ADC_RES - 1
    r_ntc = 10000 / (ADC_RES / raw_val - 1)
    t_kelvin = 1 / (1/298.15 + (1/BETA) * math.log(r_ntc / 10000))
    return round(t_kelvin - 273.15, 1)

def ldr_to_lux(raw_val):
    ADC_RES = 4095
    V_REF = 3.3
    RL10 = 50
    GAMMA = 0.7
    if raw_val <= 0: raw_val = 1
    if raw_val >= ADC_RES: raw_val = ADC_RES - 1
    voltage = raw_val / ADC_RES * V_REF
    if voltage >= V_REF: return 0.0
    resistance = 10000 * voltage / (V_REF - voltage)
    lux = math.pow(RL10 * 1e3 * math.pow(10, GAMMA) / resistance, (1 / GAMMA))
    return round(lux, 1)

def raw_to_pwr_percent(raw_val):
    ADC_RES = 4095
    return round((raw_val / ADC_RES) * 100, 1)
