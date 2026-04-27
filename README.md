# SmartRoom Monitor: Auditoria Energética Autônoma para Ambientes Inteligentes

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/SamuelSilveira/processoseletivoIoT/actions)
[![MicroPython](https://img.shields.io/badge/micropython-1.x-blue)](https://micropython.org)
[![Wokwi](https://img.shields.io/badge/simulator-Wokwi-orange)](https://wokwi.com)

*Nome:* Samuel Wagner Tiburi Silveira
*Instituição:* Universidade Federal do Cariri (UFCA)
*GitHub:* [samsilveira](https://github.com/samsilveira)

---

![Circuito do SmartRoom Monitor](img/circuito.png)

**Figura:** Simulação no Wokwi com Sensor NTC (GPIO 34), LDR (GPIO 35), PIR (GPIO 33), Potenciômetro de Carga (GPIO 32) e LEDs de controle (GPIO 14, 27 e 26).

---

## 1. Visão Geral

O **SmartRoom Monitor** é um sistema embarcado autônomo projetado para auditoria energética em tempo real. O foco central é combater o desperdício em salas de aula e escritórios, identificando quando sistemas de climatização e iluminação permanecem ativos em ambientes desocupados.

Diferente de sistemas que apenas reportam dados, o SmartRoom Monitor processa a telemetria localmente e gera alertas visuais e logs estruturados, operando como um "sentinela" de eficiência energética sem a necessidade de processamento em nuvem para a tomada de decisão crítica.

---

## 2. Arquitetura da Solução

O firmware utiliza uma arquitetura baseada em camadas para garantir modularidade e facilitar a calibração individual de cada sensor:

```
┌───────────────────────────────────────────────┐
│         Camada de Apresentação                │
│  (Monitor Serial - Logs estruturados em JSON) │
└───────────────────────────────────────────────┘
                      ↕
┌───────────────────────────────────────────────┐
│         Camada de Atuação                     │
│  • Alerta Crítico (LED Vermelho - GPIO 26)    │
│  • Alerta de Aviso (LED Amarelo - GPIO 27)    │
│  • Estado Eficiente (LED Verde - GPIO 14)     │
└───────────────────────────────────────────────┘
                      ↕
┌───────────────────────────────────────────────┐
│         Camada de Processamento               │
│  • Média móvel (suavização de ruído)          │
│  • Lógica de decisão com histerese            │
│  • Latch de presença (Timeout de 30s)         │
└───────────────────────────────────────────────┘
                      ↕
┌───────────────────────────────────────────────┐
│         Camada de Percepção                   │
│  • ADC Temperatura (NTC)                      │
│  • ADC Luminosidade (LDR)                     │
│  • Digital Presença (PIR)                     │
│  • ADC Carga Simulada (Potenciômetro)         │
└───────────────────────────────────────────────┘
```

### Dinâmica de Funcionamento

1.  **Percepção:** Coleta contínua de dados analógicos com resolução de 12 bits e sinais digitais.
2.  **Processamento:** Os dados brutos passam por um filtro de média móvel (janela de 10 amostras). A presença é validada por um latch que mantém o estado "ocupado" por 30 segundos após o último movimento detectado pelo sensor PIR.
3.  **Decisão:** Uma máquina de estados aplica limiares com histerese para evitar oscilações rápidas (chattering) nos atuadores.
4.  **Atuação:** Resposta visual imediata. Os LEDs piscam em frequências distintas conforme a gravidade: Crítico (200ms) e Aviso (600ms).

---

## 3. Hardware e Componentes

| Componente | Especificação | Função |
|---|---|---|
| **MCU** | ESP32-DevKit-C-V4 | Processador principal |
| **Sensor NTC** | Analógico (GPIO 34) | Medição de temperatura (Equação Steinhart-Hart) |
| **Sensor LDR** | Analógico (GPIO 35) | Medição de luminosidade (Lux) |
| **Sensor PIR** | Digital (GPIO 33) | Detecção de presença/movimento |
| **Potenciômetro** | Analógico (GPIO 32) | Simulador de carga energética (0-100%) |
| **LEDs** | 3x (Verde, Amarelo, Vermelho) | Feedback visual de estado |

---

## 4. Decisões Técnicas Relevantes

### 4.1 Temporização Não-Bloqueante e Robustez de Tempo
O uso de `time.sleep()` foi totalmente banido em favor de uma estrutura baseada em `time.ticks_ms()` e `time.ticks_diff()`.
- **Prevenção de Overflow:** O uso de `time.ticks_diff()` é uma decisão crítica de engenharia que garante que o cálculo de intervalos permaneça correto mesmo após o rollover (estouro) do contador de milissegundos do hardware, permitindo operação contínua de longo prazo.
- **Multitarefa Cooperativa:** Essa abordagem permite que o sistema processe sensores a 10Hz, emita logs a 1Hz e gerencie o pisca-pisca dos LEDs simultaneamente, mantendo a responsividade total.

### 4.2 Robustez com Histerese e Latch de Presença
Para evitar alarmes falsos e instabilidade operacional:
- **Histerese:** Foram definidos thresholds de entrada e saída distintos. O alerta de climatização, por exemplo, é ativado em 23°C, mas só é desativado quando a temperatura sobe acima de 25°C.
- **Latch de PIR e Inicialização Segura:** Sensores PIR detectam movimento, não presença estática. O firmware implementa um timeout de 30 segundos de persistência.
- **Prevenção de Falso Positivo no Boot:** O estado de presença é inicializado via software como "expirado" (fora do intervalo de timeout), garantindo que o sistema comece corretamente em estado desocupado e não gere alertas falsos nos primeiros 30 segundos após a inicialização.

### 4.3 Matemática Embarcada e Proteção de Operações
O firmware realiza o processamento real das grandezas físicas com foco em robustez:
- **Steinhart-Hart e Guards Matemáticos:** Conversão precisa para temperatura em Celsius. Foram implementados "Guards" que impedem divisões por zero e erros de logaritmo caso os sensores atinjam saturação máxima ou mínima (0 ou 4095 no ADC), garantindo que o sistema não trave em condições extremas.
- **Conversão Lux:** Cálculo logarítmico para luminosidade real calibrado para o sensor LDR.
- **Média Móvel:** Filtra ruídos elétricos, garantindo que a lógica de decisão seja baseada em dados estáveis e não em picos transitórios.
- **Tratamento de Saturação de ADC:** O firmware limita via software os valores de entrada do ADC antes do processamento, assegurando a estabilidade operacional mesmo em caso de falha de hardware ou desconexão física de sensores.

---

## 5. Como Executar e Testar

### Geração do Filesystem (Local)
Para gerar o arquivo `fs.bin` necessário para a simulação local no VS Code utilizando Docker (PowerShell):

```powershell
docker build -t esp32-builder -f Dockerfile . ;
docker create --name esp32-fs-builder esp32-builder ;
docker cp esp32-fs-builder:/fs.bin . ;
docker rm esp32-fs-builder
```

### Simulação Interativa
1. Abra o arquivo `diagram.json`.
2. Inicie o simulador Wokwi no VS Code.
3. **Teste de Desperdício:** Com o PIR em "No Motion", reduza a temperatura no NTC para menos de 23°C. O LED Vermelho deve começar a piscar rapidamente.
4. **Teste de Histerese:** Aumente a temperatura para 24°C; o alerta deve persistir, cessando apenas ao ultrapassar 25°C.

---

## 6. Resultados e Limitações

### Resultados Alcançados
- **Autonomia Total:** Lógica de decisão 100% local no nó de borda.
- **Eficiência de Código:** Execução multitarefa sem dependência de bibliotecas externas complexas.
- **Auditabilidade:** Logs JSON estruturados facilitam a integração com brokers MQTT ou bancos de dados.

### Trade-offs e Limitações Honestas
- **Ruído em Hardware Real:** Embora a média móvel funcione bem na simulação, hardware real pode apresentar ruídos que exigiriam janelas de filtragem maiores.
- **Sincronização Temporal:** O timestamp (`ts`) no log é relativo ao boot. Em uma implementação de produção, seria necessário um servidor NTP ou um módulo RTC para obter o horário real.
- **Consumo de Energia:** O sistema de pisca-pisca contínuo em estados de alerta consome ciclos de CPU, o que foi um tradeoff aceito em favor da clareza visual.

---

## Conclusão

O **SmartRoom Monitor** demonstra que é possível implementar inteligência de detecção e controle robusto em hardware limitado. A adoção de técnicas de sistemas de tempo real, como loops não-bloqueantes e bandas de histerese, garante que o dispositivo atue de forma confiável na preservação de recursos energéticos, cumprindo rigorosamente os objetivos do desafio técnico.
