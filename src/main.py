import machine
import time
import math

# Configuracao de Hardware

# Sensores Analogicos
adc_ntc = machine.ADC(machine.Pin(34))
adc_ldr = machine.ADC(machine.Pin(35))
adc_pwr = machine.ADC(machine.Pin(32))

for adc in [adc_ntc, adc_ldr, adc_pwr]:
    adc.atten(machine.ADC.ATTN_11DB)   # Faixa 0-3.6V
    adc.width(machine.ADC.WIDTH_12BIT)  # Resolucao 0-4095

# Sensores Digitais
pin_pir = machine.Pin(33, machine.Pin.IN)

# Atuadores (LEDs)
led_ok       = machine.Pin(14, machine.Pin.OUT)
led_warning  = machine.Pin(27, machine.Pin.OUT)
led_critical = machine.Pin(26, machine.Pin.OUT)

# Constantes de Conversao

BETA    = 3950    # Coeficiente Beta do NTC
GAMMA   = 0.7     # Coeficiente do LDR
RL10    = 50      # Resistencia do LDR a 10 lux (em kOhm)
V_REF   = 3.3     # Tensao de referencia
ADC_RES = 4095    # Resolucao 12-bit

# Funcoes de Processamento

def get_temperature():
    """Converte leitura analogica do NTC para Celsius (Steinhart-Hart)"""
    val = adc_ntc.read()
    if val >= ADC_RES: val = ADC_RES - 1
    if val <= 0: val = 1

    # Calculo para o divisor de tensao interno do sensor
    celsius = 1 / (math.log(1 / (ADC_RES / val - 1)) / BETA + 1.0 / 298.15) - 273.15
    return round(celsius, 1)

def get_lux():
    """Converte leitura analogica do LDR para Lux"""
    val = adc_ldr.read()
    if val >= ADC_RES: val = ADC_RES - 1
    if val <= 0: val = 1

    voltage = val / ADC_RES * V_REF
    if voltage >= V_REF:
        return 0.0 # Evita divisao por zero e indica escuridao total
    # Calculo da resistencia e conversao para Lux
    resistance = 10000 * voltage / (V_REF - voltage)
    lux = math.pow(RL10 * 1e3 * math.pow(10, GAMMA) / resistance, (1 / GAMMA))
    return round(lux, 1)

def get_power_percent():
    """Simula consumo relativo baseado no potenciometro (0-100%)"""
    return round((adc_pwr.read() / ADC_RES) * 100, 1)

def set_state_visual(state):
    """Atualiza o estado dos LEDs fisicos"""
    led_ok.value(1 if state == "OK" else 0)
    led_warning.value(1 if state == "AVISO" else 0)
    led_critical.value(1 if state == "CRITICO" else 0)

# Logica de Decisao Multicriterio

def evaluate_environment(temp, lux, presence, pwr):
    # Regra 1: Desperdicio Critico (Sala vazia com AC ou Luz ligados)
    # AC ligado se Temp < 23 C
    # Luz ligada se Lux > 300
    if not presence:
        if temp < 23.0 or lux > 300:
            return "CRITICO"

    # Regra 2: Sobrecarga ou uso excessivo
    if pwr > 85.0:
        return "CRITICO"

    if pwr > 65.0 or (presence and lux > 800):
        return "AVISO"

    return "OK"

# Loop de Execucao

print("Teste")
print("SmartRoom Monitor — Iniciando Auditoria Energetica...")

while True:
    # Leitura dos sensores
    current_temp = get_temperature()
    current_lux  = get_lux()
    presence     = pin_pir.value() == 1
    current_pwr  = get_power_percent()

    # Avaliacao logica
    state = evaluate_environment(current_temp, current_lux, presence, current_pwr)

    # Atuacao fisica
    set_state_visual(state)

    # Log estruturado para auditoria
    print('{"state":"%s", "temp":%.1f, "lux":%.1f, "presence":%d, "pwr":%.1f}' %
          (state, current_temp, current_lux, presence, current_pwr))

    time.sleep(1) # Intervalo de 1 segundo entre leituras
