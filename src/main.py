import machine
import time
import math

# Configuracao de Hardware

# Sensores Analogicos
adc_ntc = machine.ADC(machine.Pin(34))
adc_ldr = machine.ADC(machine.Pin(35))
adc_pwr = machine.ADC(machine.Pin(32))

for adc in [adc_ntc, adc_ldr, adc_pwr]:
    adc.atten(machine.ADC.ATTN_11DB)
    adc.width(machine.ADC.WIDTH_12BIT)

# Sensores Digitais
pin_pir = machine.Pin(33, machine.Pin.IN)

# Atuadores (LEDs)
led_ok       = machine.Pin(14, machine.Pin.OUT)
led_warning  = machine.Pin(27, machine.Pin.OUT)
led_critical = machine.Pin(26, machine.Pin.OUT)

# Constantes e Variaveis de Controle

BETA    = 3950
GAMMA   = 0.7
RL10    = 50
V_REF   = 3.3
ADC_RES = 4095

# Media Movel
WINDOW = 10
buffers = {"temp": [], "lux": [], "pwr": []}

# Temporizacao (Nao bloqueante)
last_sample_time = 0
last_log_time    = 0
last_blink_time  = 0
sample_interval  = 100  # 100ms para leitura e processamento
log_interval     = 1000 # 1s para log serial

# Estado Global
current_state = "OK"
blink_led_state = False

# Funcoes de Processamento

def smooth(key, val):
    buf = buffers[key]
    buf.append(val)
    if len(buf) > WINDOW:
        buf.pop(0)
    return sum(buf) / len(buf)

def get_temperature(raw_val):
    if raw_val <= 0: raw_val = 1
    if raw_val >= ADC_RES: raw_val = ADC_RES - 1

    # a resistencia do sensor diminui com o aumento da temperatura (NTC)
    # Formula correta para a resistencia do NTC no circuito do Wokwi
    r_ntc = 10000 / (ADC_RES / raw_val - 1)

    t_kelvin = 1 / (1/298.15 + (1/BETA) * math.log(r_ntc / 10000))
    return round(t_kelvin - 273.15, 1)

def get_lux(raw_val):
    if raw_val <= 0: raw_val = 1
    if raw_val >= ADC_RES: raw_val = ADC_RES - 1
    voltage = raw_val / ADC_RES * V_REF
    if voltage >= V_REF: return 0.0
    resistance = 10000 * voltage / (V_REF - voltage)
    lux = math.pow(RL10 * 1e3 * math.pow(10, GAMMA) / resistance, (1 / GAMMA))
    return round(lux, 1)

def get_pwr(raw_val):
    return round((raw_val / ADC_RES) * 100, 1)

# Atuacao e Feedback Visual

def update_visuals(state, current_ms):
    global last_blink_time, blink_led_state

    # Define intervalos de pisca: Critico = 200ms (Rapido), Aviso = 600ms (Lento)
    blink_interval = 200 if state == "CRITICO" else 600

    if current_ms - last_blink_time >= blink_interval:
        blink_led_state = not blink_led_state
        last_blink_time = current_ms

    # Logica de acionamento
    if state == "OK":
        led_ok.value(1)
        led_warning.value(0)
        led_critical.value(0)
    elif state == "AVISO":
        led_ok.value(0)
        led_warning.value(1 if blink_led_state else 0)
        led_critical.value(0)
    elif state == "CRITICO":
        led_ok.value(0)
        led_warning.value(0)
        led_critical.value(1 if blink_led_state else 0)

# Logica de Decisao

def evaluate(temp, lux, presence, pwr):
    if not presence:
        if temp < 23.0 or lux > 300:
            return "CRITICO"
    if pwr > 85.0:
        return "CRITICO"
    if pwr > 65.0 or (presence and lux > 800):
        return "AVISO"
    return "OK"

# Loop Principal

print("Teste")
print("--- SmartRoom Monitor ---")
print("\tIniciando Auditoria Energetica...")

while True:
    current_ms = time.ticks_ms()

    # Tarefa 1: Amostragem e Processamento (100ms)
    if current_ms - last_sample_time >= sample_interval:
        last_sample_time = current_ms

        # Leitura com media movel
        raw_t = smooth("temp", adc_ntc.read())
        raw_l = smooth("lux", adc_ldr.read())
        raw_p = smooth("pwr", adc_pwr.read())

        # Conversao fisica
        temp = get_temperature(raw_t)
        lux  = get_lux(raw_l)
        pwr  = get_pwr(raw_p)
        presence = pin_pir.value() == 1

        # Avaliacao de estado
        current_state = evaluate(temp, lux, presence, pwr)

    # Tarefa 2: Feedback Visual (Continuo para permitir pisca)
    update_visuals(current_state, current_ms)

    # Tarefa 3: Log Serial (1000ms)
    if current_ms - last_log_time >= log_interval:
        last_log_time = current_ms
        print('{"ts":%d, "state":"%s", "temp":%.1f, "lux":%.1f, "presence":%d, "pwr":%.1f}' %
              (current_ms, current_state, temp, lux, 1 if presence else 0, pwr))
