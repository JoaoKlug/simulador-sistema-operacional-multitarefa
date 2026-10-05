from typing import Optional
from core.tarefas import TCB

class Processador:
    """Representa uma CPU física do hardware."""
    def __init__(self, id_cpu: int):
        self.id_cpu = id_cpu
        self.tarefa_atual: Optional[TCB] = None
        self.tempo_desligado = 0

class Relogio:
    """Componente de hardware responsável por emitir interrupções de tempo (Ticks)."""
    def __init__(self):
        self.tick_atual = 0

class Hardware:
    """Conjunto de componentes físicos do computador."""
    def __init__(self, qtde_cpus: int):
        self.cpus = [Processador(i+1) for i in range(qtde_cpus)]
        self.relogio = Relogio()
