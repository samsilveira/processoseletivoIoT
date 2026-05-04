import machine
import time
from sensors import AnalogSensor, PresenceSensor, Button, ntc_to_celsius, ldr_to_lux, raw_to_pwr_percent
from actuators import StatusLEDs
from state_machine import RoomController

# 1. Instanciacao de Hardware
print("--- SmartRoom Monitor ---")
print("[Inicializando Hardware e Módulos...]")

# Sensores
ntc = AnalogSensor(34, ntc_to_celsius)
ldr = AnalogSensor(35, ldr_to_lux)
pwr = AnalogSensor(32, raw_to_pwr_percent)
pir = PresenceSensor(33, timeout_ms=30000)

# Atuadores
leds = StatusLEDs(pin_ok=14, pin_warn=27, pin_crit=26)

# Controle
controller = RoomController(debounce_ms=3000)

# Botao de Modo
btn = Button(12, callback=controller.toggle_mode)

# Watchdog Timer (WDT) - 5 segundos de timeout
wdt = machine.WDT(timeout=5000)

# 2. Variaveis de Sincronismo
last_sample_time = 0
last_log_time = 0
sample_interval = 100
log_interval = 1000

# 3. Loop Principal
print("[Auditoria Energetica em Execução]")

while True:
    current_ms = time.ticks_ms()

    # Alimenta o Watchdog a cada ciclo para evitar reset
    wdt.feed()

    # Tarefa 1: Amostragem e Decisao (100ms)
    if time.ticks_diff(current_ms, last_sample_time) >= sample_interval:
        last_sample_time = current_ms

        # Leituras (Analogicas com Suavizacao e PIR via IRQ)
        temp_val = ntc.read()
        lux_val  = ldr.read()
        pwr_val  = pwr.read()
        presence = pir.is_present

        # Atualiza FSM
        current_state = controller.update(temp_val, lux_val, presence, pwr_val)

        # Atualiza Visuals
        leds.update(current_state)

    # Tarefa 2: Log Serial (1000ms)
    if time.ticks_diff(current_ms, last_log_time) >= log_interval:
        last_log_time = current_ms
        print('{"ts":%d, "mode":"%s", "state":"%s", "temp":%.1f, "lux":%.1f, "presence":%d, "pwr":%.1f}' %
              (current_ms, controller.mode, controller.state, temp_val, lux_val, 1 if presence else 0, pwr_val))

    # Tarefa 3: Eficiencia Energetica (Light Sleep)
    # Dorme ate o proximo ciclo de amostragem para economizar energia
    time_to_next = sample_interval - time.ticks_diff(time.ticks_ms(), last_sample_time)
    if time_to_next > 5:
        machine.lightsleep(time_to_next)
