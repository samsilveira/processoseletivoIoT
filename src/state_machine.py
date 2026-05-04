import time

class RoomController:
    # Modos de Operacao
    MODE_RIGOROSO = "RIGOROSO"
    MODE_PADRAO = "PADRAO"

    # Thresholds: { MODO: { VAR: (ON, OFF) } }
    THRESHOLDS = {
        MODE_RIGOROSO: {
            "temp": (24.0, 26.0),
            "lux":  (400, 250),
            "pwr_crit": (80.0, 75.0),
            "pwr_warn": (60.0, 55.0)
        },
        MODE_PADRAO: {
            "temp": (22.0, 24.0),
            "lux":  (250, 150),
            "pwr_crit": (90.0, 85.0),
            "pwr_warn": (70.0, 65.0)
        }
    }

    def __init__(self, debounce_ms=3000):
        self.state = "OK"
        self.mode = self.MODE_RIGOROSO
        self.debounce_ms = debounce_ms
        self.pending_state = None
        self.last_transition_req = 0

    def toggle_mode(self):
        self.mode = self.MODE_PADRAO if self.mode == self.MODE_RIGOROSO else self.MODE_RIGOROSO
        print(f"[Sistema] Modo alterado para: {self.mode}")

    def _evaluate_instant_state(self, t, l, pres, p):
        thr = self.THRESHOLDS[self.mode]
        in_alert = self.state in ("CRITICO", "AVISO")

        # Selecao de limiares com Histerese
        t_lim = thr["temp"][1] if in_alert else thr["temp"][0]
        l_lim = thr["lux"][1]  if in_alert else thr["lux"][0]
        pc_lim = thr["pwr_crit"][1] if in_alert else thr["pwr_crit"][0]
        pw_lim = thr["pwr_warn"][1] if in_alert else thr["pwr_warn"][0]

        # Regras de transicao
        # Critico: Desperdicio (Sala vazia + AC ou Luz) ou Sobrecarga
        if not pres and (t < t_lim or l > l_lim):
            return "CRITICO"
        if p > pc_lim:
            return "CRITICO"

        # Aviso: Consumo elevado
        if p > pw_lim:
            return "AVISO"

        return "OK"

    def update(self, t, l, pres, p):
        now = time.ticks_ms()
        new_instant_state = self._evaluate_instant_state(t, l, pres, p)

        if new_instant_state != self.state:
            if new_instant_state != self.pending_state:
                self.pending_state = new_instant_state
                self.last_transition_req = now
            
            # So troca de estado se a condicao persistir (Debounce/Persistence)
            if time.ticks_diff(now, self.last_transition_req) >= self.debounce_ms:
                self.state = self.pending_state
                self.pending_state = None
        else:
            self.pending_state = None

        return self.state
