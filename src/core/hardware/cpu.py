from __future__ import annotations
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.kernel.tcb import TCB


class CPU:
    """
    Representa uma unidade física de processamento (CPU/Core) do hardware (Maziero, Cap. 2).
    Executa ciclos de instrução da tarefa alocada ou permanece desligada quando ociosa,
    contabilizando o período total de desligamento (Requisito 1.2).
    """
    def __init__(self, id_cpu: int) -> None:
        self.id_cpu: int = id_cpu
        self.tcb_atual: Optional[TCB] = None
        self.tempo_desligado: int = 0
        self.desligada_no_tick: bool = False

    def alocar_tarefa(self, tcb: TCB) -> None:
        """Aloca uma tarefa (TCB) para execução nesta CPU e liga o processador."""
        self.tcb_atual = tcb
        self.desligada_no_tick = False

    def liberar(self) -> None:
        """Desaloca a tarefa atual da CPU."""
        self.tcb_atual = None

    def esta_livre(self) -> bool:
        """Indica se a CPU não possui tarefa em execução no momento."""
        return self.tcb_atual is None

    def registrar_ociosidade(self) -> None:
        """
        Desliga o processador no ciclo atual por ausência de tarefas prontas
        e incrementa o contador acumulado de tempo desligado (Requisito 1.2).
        """
        self.tcb_atual = None
        self.tempo_desligado += 1
        self.desligada_no_tick = True

    def executar_ciclo(self) -> Optional[TCB]:
        """
        Executa 1 ciclo de relógio (tick) na CPU física (Maziero, Cap. 2 e Cap. 4, Seção 4.4):
        - Se houver tarefa em estado EXECUTANDO alocada nesta CPU, avança seu progresso (+1 tick).
        - Caso contrário, registra 1 tick de ociosidade (CPU desligada).
        """
        if self.tcb_atual is not None:
            self.tcb_atual.tempo_ja_executado += 1
            return self.tcb_atual
        self.registrar_ociosidade()
        return None
