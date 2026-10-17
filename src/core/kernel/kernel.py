from typing import List
from core.hardware.hardware import Hardware
from core.kernel.tcb import TCB
from core.kernel.escalonador import Escalonador, criar_escalonador
from core.kernel.despachante import Despachante
from core.kernel.gerenciador_tarefas import GerenciadorTarefas


class Kernel:
    """
    Núcleo Monolítico do Sistema Operacional (Maziero, Cap. 3, Seção 3.1, Figura 3.1).
    Integra em espaço privilegiado o Gerenciador de Tarefas, o Escalonador (política)
    e o Despachante (mecanismo), respondendo diretamente às interrupções de relógio
    geradas pelo Hardware (Maziero, Cap. 2, Seção 2.2.2 e Cap. 4, Figura 4.6).
    """
    def __init__(self, hardware: Hardware, algoritmo: str, tcbs: List[TCB]) -> None:
        self.hardware: Hardware = hardware
        self.algoritmo: str = algoritmo.strip().lower()
        self.gerenciador_tarefas: GerenciadorTarefas = GerenciadorTarefas(tcbs)
        self.despachante: Despachante = Despachante()
        self.escalonador: Escalonador = criar_escalonador(self.algoritmo)

        # Registra a rotina de tratamento do temporizador na Tabela de Interrupções (IVT) do Hardware
        self.hardware.registrar_tratador_interrupcao(self.tratar_interrupcao_relogio)

        # Registra o log inicial de boot do sistema no Tick 0
        self.gerenciador_tarefas.limpar_eventos_tick(titulo_log="Tick 0 · Inicialização do Sistema")
        tarefas_validas = [f"T{t.id_tarefa}" for t in tcbs if t.duracao > 0 and t.periodo > 0]
        resumo_tarefas = ", ".join(tarefas_validas) if tarefas_validas else "1 tarefa padrão (NOVA)"
        self.gerenciador_tarefas.registrar_log(
            funcao="Hardware.registrar_tratador_interrupcao(Kernel.tratar_interrupcao_relogio)",
            detalhe=(
                f"IVT configurada para IRQ 0 | CPUs: {len(self.hardware.cpus)} | "
                f"Política: {self.algoritmo.upper()} | Tarefas: {resumo_tarefas}."
            ),
            categoria="SISTEMA",
        )

    def alterar_algoritmo(self, novo_algoritmo: str) -> None:
        """Altera dinamicamente a política de escalonamento do Kernel (Requisito 3.1)."""
        self.escalonador = criar_escalonador(novo_algoritmo)
        self.algoritmo = novo_algoritmo.strip().lower()

    def tratar_interrupcao_relogio(self, tick_atual: int) -> None:
        """
        Rotina de Tratamento de Interrupção do Temporizador (Timer ISR):
        Invocada pelo Hardware quando o relógio avança de 'tick_inicio = tick_atual - 1' para 'tick_atual'.
        1. Admite e reativa tarefas cujo instante/período iniciou em 'tick_inicio'.
        2. Consulta o Escalonador para ordenar as tarefas aptas (PRONTA e EXECUTANDO) em 'tick_inicio'.
        3. Aciona o Despachante para efetivar trocas de contexto (salvar_contexto / restaurar_contexto).
        4. Executa 1 ciclo nas CPUs físicas (CPU.executar_ciclo) e contabiliza términos/deadlines em 'tick_atual'.
        """
        tick_inicio = max(0, tick_atual - 1)
        self.gerenciador_tarefas.limpar_eventos_tick(
            titulo_log=f"Tick {tick_inicio} → {tick_atual} (Intervalo [{tick_inicio}, {tick_atual}))"
        )

        self.gerenciador_tarefas.registrar_log(
            funcao=f"Hardware.gerar_interrupcao_tick() → Kernel.tratar_interrupcao_relogio({tick_atual})",
            detalhe=f"Temporizador físico pulsou para T{tick_atual} e disparou IRQ 0 ao Kernel.",
            categoria="IRQ",
        )

        # Identifica quem estava executando nas CPUs imediatamente antes deste ciclo
        ids_nas_cpus_antes = [
            cpu.tcb_atual.id_tarefa
            for cpu in self.hardware.cpus
            if cpu.tcb_atual is not None and cpu.tcb_atual.estado.name == "EXECUTANDO"
        ]

        # 1. Prepara ingressos e reativações periódicas no início do intervalo
        self.gerenciador_tarefas.preparar_inicio_intervalo(tick_inicio)

        # 2. Escalonador ordena as tarefas aptas segundo a política ativa (RM ou EDF)
        elegiveis = self.gerenciador_tarefas.obter_elegiveis()
        fila_prontos = self.escalonador.eleger(elegiveis, tick_inicio, ids_nas_cpus_antes)
        self.gerenciador_tarefas.logs_tick_atual.append(
            self.escalonador.gerar_log_eleicao(fila_prontos, ids_nas_cpus_antes)
        )

        # 3. Despachante realiza trocas de contexto ou mantém tarefas nas CPUs físicas
        self.despachante.despachar(
            cpus=self.hardware.cpus,
            fila_ordenada=fila_prontos,
            tick_evento=tick_inicio,
            gerenciador_tarefas=self.gerenciador_tarefas,
        )

        # 4. CPUs executam 1 ciclo e GerenciadorTarefas contabiliza términos e deadlines em tick_atual
        self.gerenciador_tarefas.concluir_intervalo_tick(self.hardware.cpus, tick_atual)

    def reescalonar_estado_atual(self, tick_atual: int) -> None:
        """
        Reavalia a alocação das CPUs após uma edição manual pelo usuário quando tick_atual > 0.
        No Tick 0 (antes de iniciar a simulação), não força tarefas para EXECUTANDO.
        """
        if tick_atual == 0:
            return

        ids_nas_cpus_antes = [
            cpu.tcb_atual.id_tarefa for cpu in self.hardware.cpus if cpu.tcb_atual is not None
        ]

        self.gerenciador_tarefas.preparar_inicio_intervalo(tick_atual)
        elegiveis = self.gerenciador_tarefas.obter_elegiveis()
        fila_prontos = self.escalonador.eleger(elegiveis, tick_atual, ids_nas_cpus_antes)
        self.gerenciador_tarefas.logs_tick_atual.append(
            self.escalonador.gerar_log_eleicao(fila_prontos, ids_nas_cpus_antes)
        )
        self.despachante.despachar(
            cpus=self.hardware.cpus,
            fila_ordenada=fila_prontos,
            tick_evento=tick_atual,
            gerenciador_tarefas=self.gerenciador_tarefas,
        )
