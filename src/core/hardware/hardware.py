from typing import List, Callable, Optional
from core.hardware.cpu import CPU
from core.logger import log_core, log_secao


class Hardware:
    """
    Subsistema de Hardware físico do computador simulado (Maziero, Cap. 2, Seções 2.2.2 e 2.2.4).
    Integra os múltiplos processadores (CPUs) e o circuito temporizador físico (Timer),
    sendo responsável por avançar os ticks de relógio e gerar a interrupção de hardware (IRQ 0)
    que notifica o Núcleo (Kernel) do Sistema Operacional.
    """
    def __init__(self, qtde_cpus: int, tick_inicial: int = 0) -> None:
        self.cpus: List[CPU] = [CPU(id_cpu=i + 1) for i in range(qtde_cpus)]
        self.tick_atual: int = tick_inicial
        self._tratador_irq_relogio: Optional[Callable[[int], None]] = None

    def registrar_tratador_interrupcao(self, tratador_irq: Callable[[int], None]) -> None:
        """
        Registra na Tabela de Vetores de Interrupção (IVT) do Hardware a rotina do Kernel
        responsável por tratar a interrupção do temporizador físico (Maziero, Cap. 2, Seção 2.2.2).
        """
        self._tratador_irq_relogio = tratador_irq
        nome_tratador = getattr(tratador_irq, "__qualname__", getattr(tratador_irq, "__name__", "tratador_irq"))
        log_core(
            "Hardware.registrar_tratador_interrupcao",
            f"IVT configurada: IRQ 0 (Temporizador) associada à rotina '{nome_tratador}'.",
        )

    def gerar_interrupcao_tick(self, tratador_irq: Optional[Callable[[int], None]] = None) -> int:
        """
        Avança o relógio físico do Hardware em 1 tick e emite o sinal de interrupção
        do temporizador (IRQ 0), desviando o fluxo para a rotina registrada pelo Kernel.
        """
        tick_anterior = self.tick_atual
        self.tick_atual += 1
        log_secao(f"TICK {tick_anterior} -> {self.tick_atual} (Intervalo [{tick_anterior}, {self.tick_atual}))")
        log_core(
            "Hardware.gerar_interrupcao_tick",
            f"Relógio físico avançou de {tick_anterior} para {self.tick_atual}. Emitindo IRQ 0 ao Kernel.",
        )
        rotina = tratador_irq if tratador_irq is not None else self._tratador_irq_relogio
        if rotina is not None:
            rotina(self.tick_atual)
        return self.tick_atual
