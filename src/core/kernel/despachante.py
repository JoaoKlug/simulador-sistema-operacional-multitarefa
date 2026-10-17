from typing import List, Dict, Optional
from core.hardware.cpu import CPU
from core.kernel.tcb import TCB
from core.kernel.gerenciador_tarefas import GerenciadorTarefas
from core.logger import log_core
from core.processos.estado_tarefa import EstadoTarefa


class Despachante:
    """
    Despachante (Dispatcher) do Kernel (Maziero, Cap. 5, Seção 5.2, Figura 5.1).
    Implementa exclusivamente o MECANISMO de troca de contexto:
    - Salva o contexto da tarefa preemptada em seu TCB (EXECUTANDO -> PRONTA);
    - Restaura o contexto da tarefa eleita a partir de seu TCB na CPU (PRONTA -> EXECUTANDO);
    - Mantém a tarefa na mesma CPU sem troca de contexto quando ela continua eleita.
    """
    def salvar_contexto(self, tcb: TCB, cpu: Optional[CPU] = None) -> None:
        """
        Passo 4 da Figura 5.1 de Maziero: salva o contexto da tarefa que perde o processador
        em seu TCB, atualizando seu estado de EXECUTANDO para PRONTA.
        """
        id_cpu_anterior = cpu.id_cpu if cpu is not None else tcb.id_cpu_alocada
        if cpu is not None and cpu.tcb_atual is not None and cpu.tcb_atual.id_tarefa == tcb.id_tarefa:
            cpu.liberar()
        tcb.estado = EstadoTarefa.PRONTA
        tcb.id_cpu_alocada = None
        info_cpu = f" da C{id_cpu_anterior}" if id_cpu_anterior is not None else ""
        log_core(
            "Despachante.salvar_contexto",
            f"Preempção: contexto de T{tcb.id_tarefa} salvo no TCB (retirada{info_cpu}: EXECUTANDO -> PRONTA).",
        )

    def restaurar_contexto(self, tcb: TCB, cpu: CPU) -> None:
        """
        Passo 6 da Figura 5.1 de Maziero: resgata o contexto da tarefa eleita de seu TCB,
        comuta seu estado de PRONTA para EXECUTANDO e a aloca na CPU física.
        """
        tcb.estado = EstadoTarefa.EXECUTANDO
        tcb.id_cpu_alocada = cpu.id_cpu
        cpu.alocar_tarefa(tcb)
        log_core(
            "Despachante.restaurar_contexto",
            f"Contexto de T{tcb.id_tarefa} restaurado na C{cpu.id_cpu} (PRONTA -> EXECUTANDO).",
        )

    def despachar(
        self,
        cpus: List[CPU],
        fila_ordenada: List[TCB],
        tick_evento: int,
        gerenciador_tarefas: GerenciadorTarefas,
    ) -> None:
        """
        Distribui as tarefas eleitas nas CPUs físicas para o intervalo [tick_evento, tick_evento + 1).
        - Se a tarefa já estava executando em uma CPU específica e continua eleita, preserva-a sem troca de contexto.
        - Se uma tarefa em execução perdeu a vez para outra mais prioritária, executa salvar_contexto (preempção).
        - Aloca as novas tarefas eleitas via restaurar_contexto.
        """
        mapa_cpu_anterior: Dict[int, TCB] = {
            cpu.id_cpu: cpu.tcb_atual for cpu in cpus if cpu.tcb_atual is not None
        }
        ids_nas_cpus_antes = [t.id_tarefa for t in mapa_cpu_anterior.values()]

        eleitas = fila_ordenada[: len(cpus)]
        nao_eleitas = fila_ordenada[len(cpus) :]

        self._preemptar_nao_eleitas(cpus, nao_eleitas)

        eleitas_pendentes: List[TCB] = list(eleitas)
        acoes_cpus: Dict[int, str] = {}
        cpus_livres = self._manter_tarefas_atuais(cpus, eleitas_pendentes, acoes_cpus)

        for cpu in cpus_livres:
            tcb_antigo = mapa_cpu_anterior.get(cpu.id_cpu)
            tcb_eleito = eleitas_pendentes.pop(0) if eleitas_pendentes else None
            if tcb_eleito is not None and tcb_eleito.sorteada_no_tick and tcb_eleito.id_tarefa not in ids_nas_cpus_antes:
                gerenciador_tarefas.registrar_evento(tcb_eleito.id_tarefa, tick_evento, "SORTEIO")
            self._alocar_cpu_livre(cpu, tcb_eleito, tcb_antigo, acoes_cpus)

        partes_despacho = [acoes_cpus[c.id_cpu] for c in cpus if c.id_cpu in acoes_cpus]
        if nao_eleitas:
            espera_str = ", ".join(f"T{t.id_tarefa}" for t in nao_eleitas)
            partes_despacho.append(f"Aguardando na fila PRONTA: [{espera_str}]")

        log_core("Despachante.despachar", " | ".join(partes_despacho))

    def _preemptar_nao_eleitas(self, cpus: List[CPU], nao_eleitas: List[TCB]) -> None:
        """Salva o contexto das tarefas que perderam o processador e permanecem em PRONTA."""
        for tcb_espera in nao_eleitas:
            if tcb_espera.estado == EstadoTarefa.EXECUTANDO or tcb_espera.id_cpu_alocada is not None:
                cpu_antiga = next((c for c in cpus if c.id_cpu == tcb_espera.id_cpu_alocada), None)
                self.salvar_contexto(tcb_espera, cpu_antiga)
            else:
                tcb_espera.estado = EstadoTarefa.PRONTA
                tcb_espera.id_cpu_alocada = None

    def _manter_tarefas_atuais(
        self,
        cpus: List[CPU],
        eleitas_pendentes: List[TCB],
        acoes_cpus: Dict[int, str],
    ) -> List[CPU]:
        """Mantém na mesma CPU (sem troca de contexto) as tarefas eleitas que já estavam nela."""
        cpus_livres: List[CPU] = []
        for cpu in cpus:
            mantida = next((t for t in eleitas_pendentes if t.id_cpu_alocada == cpu.id_cpu), None)
            if mantida is not None:
                eleitas_pendentes.remove(mantida)
                mantida.estado = EstadoTarefa.EXECUTANDO
                mantida.id_cpu_alocada = cpu.id_cpu
                cpu.alocar_tarefa(mantida)
                acoes_cpus[cpu.id_cpu] = f"C{cpu.id_cpu} manteve T{mantida.id_tarefa} (sem troca de contexto)"
            else:
                cpu.liberar()
                cpus_livres.append(cpu)
        return cpus_livres

    def _alocar_cpu_livre(
        self,
        cpu: CPU,
        tcb_eleito: Optional[TCB],
        tcb_antigo: Optional[TCB],
        acoes_cpus: Dict[int, str],
    ) -> None:
        """Restaura o contexto da tarefa eleita na CPU livre ou desliga a CPU no ciclo."""
        if tcb_eleito is None:
            cpu.tcb_atual = None
            cpu.desligada_no_tick = True
            acoes_cpus[cpu.id_cpu] = f"C{cpu.id_cpu}: sem tarefa apta (desligada no ciclo)"
            return

        self.restaurar_contexto(tcb_eleito, cpu)
        if tcb_antigo is not None and tcb_antigo.id_tarefa != tcb_eleito.id_tarefa:
            acoes_cpus[cpu.id_cpu] = (
                f"C{cpu.id_cpu}: trocou contexto de T{tcb_antigo.id_tarefa} (preemptada) "
                f"para T{tcb_eleito.id_tarefa} (EXECUTANDO)"
            )
            return

        acoes_cpus[cpu.id_cpu] = f"C{cpu.id_cpu}: alocou T{tcb_eleito.id_tarefa} (PRONTA -> EXECUTANDO)"
