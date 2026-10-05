from typing import List
from core.hardware import Hardware
from core.kernel import Kernel
from core.tarefas import TCB

class SistemaOperacional:
    """
    Fachada principal do S.O.
    Encapsula o Hardware e o Kernel, expondo os controles básicos de simulação.
    """
    def __init__(self, qtde_cpus: int, algoritmo: str, quantum: int, tarefas: List[TCB]):
        self.hardware = Hardware(qtde_cpus)
        self.kernel = Kernel(self.hardware, algoritmo, tarefas)
        self.quantum_global = quantum

    def avancar_tempo(self):
        """Simula a passagem do tempo e ativação das rotinas nucleares."""
        self.kernel.tratar_interrupcao_relogio()

    @property
    def tick_atual(self) -> int:
        return self.hardware.relogio.tick_atual

    @property
    def tarefas(self) -> List[TCB]:
        return self.kernel.gerenciador_tarefas.tarefas_sistema

    @property
    def qtde_cpus(self) -> int:
        return len(self.hardware.cpus)

    @property
    def nome_algoritmo(self) -> str:
        return self.kernel.algoritmo
        
    def finalizado(self) -> bool:
        return self.kernel.gerenciador_tarefas.todas_finalizadas()
