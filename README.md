# SmartRoom Monitor: Auditoria Energética Autônoma para Ambientes Inteligentes

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/SamuelSilveira/processoseletivoIoT/actions)
[![MicroPython](https://img.shields.io/badge/micropython-1.x-blue)](https://micropython.org)
[![Wokwi](https://img.shields.io/badge/simulator-Wokwi-orange)](https://wokwi.com)

*Nome:* Samuel Wagner Tiburi Silveira
*Instituição:* Universidade Federal do Cariri (UFCA)
*GitHub:* [samsilveira](https://github.com/samsilveira)

---

![Circuito do SmartRoom Monitor](img/circuito.png)

**Figura:** Simulação no Wokwi com Sensores NTC, LDR, PIR, Potenciômetro de Carga, LEDs de controle e Botão de Modo (Rigoroso / Padrão).

---

## 1. Visão Geral

O **SmartRoom Monitor** é um sistema embarcado autônomo de alta performance projetado para auditoria energética em tempo real. O sistema utiliza uma arquitetura modular orientada a objetos e técnicas de sistemas de tempo real para garantir resiliência, eficiência energética e uma interface de usuário dinâmica, focando no combate ao desperdício em ambientes inteligentes.

---

## 2. Arquitetura da Solução (Modular e POO)

O firmware é estruturado sob o paradigma de **Orientação a Objetos (POO)**, dividindo as responsabilidades em módulos especializados para garantir escalabilidade e manutenibilidade:

- **`sensors.py`**: Abstração de hardware. Contém a classe `AnalogSensor` (filtragem e conversão) e `PresenceSensor` (detecção baseada em evento).
- **`actuators.py`**: Gerenciamento de feedback visual através da classe `StatusLEDs`.
- **`state_machine.py`**: Núcleo de decisão. Implementa uma **Máquina de Estados Finitos (FSM)** robusta com suporte a múltiplos perfis de auditoria.
- **`main.py`**: Ponto de entrada que orquestra o loop de eventos, Watchdog e políticas de economia de energia.

### Fluxo de Dados e Controle

1. **Percepção (IRQ/ADC):** Coleta de dados analógicos suavizados e sinais digitais via interrupções para atualização instantânea.
2. **Processamento:** Classes especializadas realizam a conversão para grandezas físicas (Celsius, Lux, %).
3. **Decisão:** A FSM avalia as condições ambientais baseada no perfil de auditoria selecionado (Rigoroso ou Padrão).
4. **Atuação:** Geração de alertas visuais e logs estruturados em formato JSON para auditoria externa.

---

## 3. Hardware e Componentes

| Componente | Especificação | Função |
| --- | --- | --- |
| **MCU** | ESP32-DevKit-C-V4 | Processador principal |
| **Sensor NTC** | Analógico (GPIO 34) | Medição de temperatura |
| **Sensor LDR** | Analógico (GPIO 35) | Medição de luminosidade |
| **Sensor PIR** | **Digital IRQ (GPIO 33)** | Detecção de presença (Evento imediato) |
| **Potenciômetro** | Analógico (GPIO 32) | Simulador de carga energética (0-100%) |
| **LEDs** | 3x (Verde, Amarelo, Vermelho) | Feedback visual de estado |
| **Botão de Modo**| **Digital IRQ (GPIO 12)** | Alternância entre perfis de auditoria |

---

## 4. Inovações e Decisões Técnicas

### 4.1 Interrupções de Hardware (IRQ) Seguras

A detecção de movimento e a interface de botão operam via **Interrupções de Hardware (IRQ)** para otimizar o uso da CPU:
- **Resiliência:** O uso de `micropython.schedule()` garante que o processamento de eventos (como logs e cálculos) ocorra fora do contexto crítico da interrupção, prevenindo erros de alocação de memória no hardware real.
- **Eficiência:** Permite que o processador entre em estados de baixo consumo sem perder eventos críticos de sensores.

### 4.2 FSM com Transições Temporizadas (Persistence Check)

Para garantir estabilidade operacional e evitar alarmes falsos:
- A lógica de decisão exige que uma condição de trigger persista por **3 segundos** antes de consolidar a mudança de estado.
- Este mecanismo elimina o "chattering" causado por ruídos analógicos ou sensores operando em limiares de transição.

### 4.3 Modos de Operação: Auditoria Rigorosa vs Padrão

O sistema disponibiliza perfis selecionáveis para diferentes necessidades de gestão:
- **Modo Auditoria Rigorosa:** Aplica limiares mais estritos para maximizar a economia de recursos.
- **Modo Padrão:** Equilibra a economia de energia com o conforto dos ocupantes.
- A troca de perfil é realizada via interrupção no botão físico, fornecendo feedback imediato no terminal.

### 4.4 Resiliência e Gestão de Energia

- **Watchdog Timer (WDT):** Um sentinela de hardware monitora o loop principal, reiniciando o sistema automaticamente em caso de falha de software.
- **Eficiência Energética:** Implementação de `machine.lightsleep()` entre ciclos de amostragem, reduzindo o consumo energético simulado e real do dispositivo IoT.

---

## 5. Como Executar e Testar

### Geração do Filesystem Modular

O processo de build via Docker integra todos os módulos Python no binário do sistema de arquivos (`fs.bin`):

```powershell
docker build -t esp32-builder -f Dockerfile . ;
docker create --name esp32-fs-builder esp32-builder ;
docker cp esp32-fs-builder:/fs.bin . ;
docker rm esp32-fs-builder
```

### Protocolo de Teste na Simulação

1. **Validação de Modo:** Clique no botão azul "Modo" para observar a troca de perfil no console.
2. **Teste de Persistência:** Force uma condição de alerta (ex: luz acesa sem presença). O LED deve mudar de cor somente após o tempo de confirmação de 3 segundos.
3. **Detecção PIR:** Verifique se o registro de presença no log JSON responde instantaneamente ao acionamento do sensor.

---

## 6. Resultados e Limitações

### Resultados Alcançados

- **Autonomia e Inteligência Local:** Lógica de decisão processada inteiramente na borda (Edge Computing).
- **Arquitetura Industrial:** Separação em módulos POO que permite escalabilidade e adição de novos sensores com baixo impacto no código base.
- **Confiabilidade Elevada:** Uso de WDT, IRQ seguras e filtragem por persistência elevam o projeto ao padrão de produto comercial.
- **Auditabilidade:** Logs JSON estruturados facilitam a integração com sistemas de monitoramento externos.

### Trade-offs e Limitações

- **Ruído em Hardware Real:** Embora a média móvel e a persistência mitiguem ruídos, implementações físicas podem exigir janelas de amostragem maiores.
- **Sincronização Temporal:** O timestamp (`ts`) é relativo ao tempo de boot. Implementações de produção requerem sincronização via NTP ou módulo RTC.
- **Consumo de UI:** O feedback visual contínuo por LEDs, embora útil, representa um ponto de consumo que pode ser otimizado para dispositivos operando exclusivamente por bateria.

---

## 7. Conclusão

O **SmartRoom Monitor** demonstra a viabilidade de implementar controle robusto e inteligente em hardware embarcado de baixo custo. Através do uso de técnicas avançadas como máquinas de estados temporizadas, interrupções seguras e modularização de código, o projeto atende com rigor aos requisitos técnicos e de inovação, operando como uma solução confiável para a preservação de recursos energéticos.
