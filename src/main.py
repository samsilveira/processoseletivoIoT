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

# Constantes de Conversao e Limiares (Histerese)

BETA          = 3950
GAMMA         = 0.7
RL10          = 50
V_REF         = 3.3
ADC_RES       = 4095

# Thresholds com Histerese (Entrada / Saida)
TEMP_AC_ON    = 23.0;  TEMP_AC_OFF    = 25.0
LUX_LIGHT_ON  = 300;   LUX_LIGHT_OFF  = 200
PWR_CRIT_ON   = 85.0;  PWR_CRIT_OFF   = 80.0
PWR_WARN_ON   = 65.0;  PWR_WARN_OFF   = 60.0

# Configuracoes de Tempo
PRESENCE_TIMEOUT_MS = 30000 # 30 segundos de persistencia
WINDOW              = 10
sample_interval     = 100
log_interval        = 1000

# Variaveis Globais e Buffers
buffers = {"temp": [], "lux": [], "pwr": []}
last_sample_time   = 0
last_log_time      = 0
last_blink_time    = 0
last_presence_time = -30001 # Inicializa como expirado para evitar presenca no boot
blink_led_state    = False

# Inicializacao de Variaveis de Estado (Evita NameError)
temp = 25.0
lux  = 0.0
pwr  = 0.0
presence = False
current_state = "OK"

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

def update_presence(raw_pir, current_ms):
    global last_presence_time
    if raw_pir == 1:
        last_presence_time = current_ms
    # Uso de ticks_diff para seguranca de tempo real
    return time.ticks_diff(current_ms, last_presence_time) < PRESENCE_TIMEOUT_MS

# Atuacao e Feedback Visual

def update_visuals(state, current_ms):
    global last_blink_time, blink_led_state

    blink_interval = 200 if state == "CRITICO" else 600

    # Uso de ticks_diff para gerenciar o pisca-pisca
    if time.ticks_diff(current_ms, last_blink_time) >= blink_interval:
        blink_led_state = not blink_led_state
        last_blink_time = current_ms

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

# Logica de Decisao com Histerese

def evaluate(t, l, pres, p, prev_state):
    in_alert = prev_state in ("CRITICO", "AVISO")

    # Selecao de limiares baseada no estado anterior (Histerese)
    t_thr  = TEMP_AC_OFF   if in_alert else TEMP_AC_ON
    l_thr  = LUX_LIGHT_OFF if in_alert else LUX_LIGHT_ON
    p_crit = PWR_CRIT_OFF  if in_alert else PWR_CRIT_ON
    p_warn = PWR_WARN_OFF  if in_alert else PWR_WARN_ON

    # Regra Critica: Desperdicio (Sala vazia + AC ou Luz) ou Sobrecarga
    if not pres and (t < t_thr or l > l_thr):
        return "CRITICO"
    if p > p_crit:
        return "CRITICO"

    # Regra de Aviso: Consumo elevado ou Luz excessiva com baixa carga
    if p > p_warn or (pres and l > 800 and p < 40.0):
        return "AVISO"

    return "OK"

# Loop Principal

print("Teste")
print("--- SmartRoom Monitor ---")
print("[Iniciando Auditoria Energetica...]")

while True:
    current_ms = time.ticks_ms()

    # Tarefa 1: Amostragem e Processamento (100ms)
    if time.ticks_diff(current_ms, last_sample_time) >= sample_interval:
        last_sample_time = current_ms

        # Leitura e Suavizacao
        raw_t = smooth("temp", adc_ntc.read())
        raw_l = smooth("lux", adc_ldr.read())
        raw_p = smooth("pwr", adc_pwr.read())

        # Conversao Fisica
        temp     = get_temperature(raw_t)
        lux      = get_lux(raw_l)
        pwr      = get_pwr(raw_p)
        presence = update_presence(pin_pir.value(), current_ms)

        # Avaliacao de estado com Histerese
        current_state = evaluate(temp, lux, presence, pwr, current_state)

    # Tarefa 2: Feedback Visual
    update_visuals(current_state, current_ms)

    # Tarefa 3: Log Serial (1000ms)
    if time.ticks_diff(current_ms, last_log_time) >= log_interval:
        last_log_time = current_ms
        print('{"ts":%d, "state":"%s", "temp":%.1f, "lux":%.1f, "presence":%d, "pwr":%.1f}' %
              (current_ms, current_state, temp, lux, 1 if presence else 0, pwr))
