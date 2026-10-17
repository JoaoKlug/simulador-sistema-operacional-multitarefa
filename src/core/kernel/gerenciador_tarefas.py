from typing import List, Optional, Tuple
from core.hardware.cpu import CPU
from core.kernel.tcb import TCB, EventoTarefaTick, RegistroLogCore
from core.processos.estado_tarefa import EstadoTarefa


class GerenciadorTarefas:
    """
    Subsistema do Kernel responsável pela gestão integral do ciclo de vida das tarefas
    (Maziero, Cap. 4 e 5). Controla admissões, progresso de execução, términos,
    reativações periódicas (limite de 10 execuções) e detecção de perda de deadline.
    """
    LIMITE_EXECUCOES_PROJETO_A: int = 10

    def __init__(self, tcbs: List[TCB]) -> None:
        self.tcbs: List[TCB] = tcbs
        self.eventos_tick_atual: List[EventoTarefaTick] = []
        self.logs_tick_atual: List[RegistroLogCore] = []
        self.titulo_log_atual: str = ""

    def limpar_eventos_tick(self, titulo_log: str = "") -> None:
        """Limpa os eventos pontuais e registros de log antes de processar um novo passo."""
        self.eventos_tick_atual = []
        self.logs_tick_atual = []
        self.titulo_log_atual = titulo_log

    def registrar_log(self, funcao: str, detalhe: str, categoria: str = "INFO") -> None:
        """Registra a execução de uma função-chave do core para exibição didática."""
        self.logs_tick_atual.append(
            RegistroLogCore(funcao=funcao, detalhe=detalhe, categoria=categoria)
        )

    def registrar_evento(self, id_tarefa: int, tick: int, tipo: str) -> None:
        """Registra um evento relevante ocorrido no instante 'tick' se ainda não registrado."""
        evento = EventoTarefaTick(id_tarefa=id_tarefa, tick=tick, tipo=tipo)
        if evento not in self.eventos_tick_atual:
            self.eventos_tick_atual.append(evento)

    def preparar_inicio_intervalo(self, tick_inicio: int) -> None:
        """
        Prepara as tarefas no instante 'tick_inicio' para o intervalo [tick_inicio, tick_inicio + 1):
        admite tarefas novas, reativa períodos e verifica estouros de deadline no início do tick.
        """
        ingressos: List[str] = []
        reativacoes: List[str] = []
        atrasos: List[str] = []

        for t in self.tcbs:
            if not self._tarefa_configurada_valida(t):
                continue
            if self._atingiu_limite_ciclos(t):
                continue

            msg_ing, msg_reat = self._avaliar_ingresso_ou_reativacao(t, tick_inicio)
            if msg_ing:
                ingressos.append(msg_ing)
            if msg_reat:
                reativacoes.append(msg_reat)

            msg_atraso = self._verificar_atraso_tarefa(t, tick_inicio)
            if msg_atraso:
                atrasos.append(msg_atraso)

        self._registrar_log_inicio_intervalo(tick_inicio, ingressos, reativacoes, atrasos)

    def _tarefa_configurada_valida(self, t: TCB) -> bool:
        """Indica se a tarefa possui parâmetros periódicos válidos (> 0)."""
        return t.duracao > 0 and t.periodo > 0

    def _atingiu_limite_ciclos(self, t: TCB) -> bool:
        """Garante que tarefas que completaram 10 execuções permaneçam finalizadas."""
        if t.execucoes_completadas >= self.LIMITE_EXECUCOES_PROJETO_A:
            t.estado = EstadoTarefa.FINALIZADA
            t.id_cpu_alocada = None
            return True
        return False

    def _avaliar_ingresso_ou_reativacao(
        self, t: TCB, tick_inicio: int
    ) -> Tuple[Optional[str], Optional[str]]:
        """Processa a transição NOVA -> PRONTA ou AGUARDANDO -> PRONTA quando o tick de ativação chega."""
        if t.estado == EstadoTarefa.NOVA and tick_inicio >= t.instante_ingresso:
            self._ativar_instancia_tarefa(t, tick_inicio, tick_inicio)
            return f"T{t.id_tarefa} (NOVA → PRONTA, DL={t.prazo_absoluto_atual})", None

        if t.estado == EstadoTarefa.AGUARDANDO:
            proximo_inicio = t.obter_proximo_inicio()
            if tick_inicio >= proximo_inicio:
                self._ativar_instancia_tarefa(t, tick_inicio, tick_inicio)
                ciclo_num = t.execucoes_completadas + 1
                return None, f"T{t.id_tarefa} (AGUARDANDO → PRONTA, Ciclo {ciclo_num}/10, DL={t.prazo_absoluto_atual})"

        return None, None

    def _ativar_instancia_tarefa(self, t: TCB, inicio_ciclo: int, tick_evento: int) -> None:
        """Inicializa o ciclo da tarefa na fila de prontos, atualizando tick_inicio_ciclo_atual e deadline."""
        t.estado = EstadoTarefa.PRONTA
        t.tick_inicio_ciclo_atual = inicio_ciclo
        t.prazo_absoluto_atual = inicio_ciclo + t.prazo_relativo
        t.tempo_ja_executado = 0
        t.sofreu_atraso = False
        self.registrar_evento(t.id_tarefa, tick_evento, "INGRESSO")

    def _verificar_atraso_tarefa(self, t: TCB, tick_ref: int) -> Optional[str]:
        """Verifica se uma tarefa ativa ultrapassou seu deadline absoluto no instante tick_ref."""
        estados_ativos = (EstadoTarefa.PRONTA, EstadoTarefa.EXECUTANDO, EstadoTarefa.SUSPENSA)
        if t.estado in estados_ativos and tick_ref >= t.prazo_absoluto_atual and t.tempo_ja_executado < t.duracao:
            if not t.sofreu_atraso:
                t.sofreu_atraso = True
                self.registrar_evento(t.id_tarefa, tick_ref, "DEADLINE")
                return f"⚠ T{t.id_tarefa} perdeu DeadLine em T{tick_ref} (DL={t.prazo_absoluto_atual})"
        return None

    def _registrar_log_inicio_intervalo(
        self,
        tick_inicio: int,
        ingressos: List[str],
        reativacoes: List[str],
        atrasos: List[str],
    ) -> None:
        """Formata e registra o log sintético de preparar_inicio_intervalo."""
        partes: List[str] = []
        if ingressos:
            partes.append("Ingresso: " + ", ".join(ingressos))
        if reativacoes:
            partes.append("Reativação: " + ", ".join(reativacoes))
        if atrasos:
            partes.append("; ".join(atrasos))

        detalhe = " | ".join(partes) if partes else "Sem novos ingressos ou reativações neste instante."
        self.registrar_log(
            funcao=f"GerenciadorTarefas.preparar_inicio_intervalo({tick_inicio})",
            detalhe=detalhe,
            categoria="CICLO_VIDA" if partes else "INFO",
        )

    def concluir_intervalo_tick(self, cpus: List[CPU], tick_fim: int) -> None:
        """
        Registra o estado executado durante o intervalo [tick_fim - 1, tick_fim),
        aciona CPU.executar_ciclo() em cada processador e verifica términos e deadlines.
        """
        self._fotografar_estado_intervalo()

        resumo_cpus: List[str] = []
        terminos: List[str] = []
        for cpu in cpus:
            msg_cpu, msg_termino = self._processar_ciclo_cpu(cpu, tick_fim)
            resumo_cpus.append(msg_cpu)
            if msg_termino:
                terminos.append(msg_termino)

        self.registrar_log(
            funcao="CPU.executar_ciclo()",
            detalhe=" | ".join(resumo_cpus) if resumo_cpus else "Nenhuma CPU ativa.",
            categoria="HARDWARE",
        )

        atrasos_fim = [
            msg for t in self.tcbs if self._tarefa_configurada_valida(t)
            for msg in [self._verificar_atraso_tarefa(t, tick_fim)] if msg
        ]
        self._registrar_log_conclusao(tick_fim, terminos, atrasos_fim)

    def _fotografar_estado_intervalo(self) -> None:
        """Salva no TCB o estado efetivamente executado durante o intervalo que se encerra."""
        for t in self.tcbs:
            t.estado_ultimo_intervalo = t.estado
            t.cpu_ultimo_intervalo = t.id_cpu_alocada if t.estado == EstadoTarefa.EXECUTANDO else None
            t.atraso_ultimo_intervalo = t.sofreu_atraso

    def _processar_ciclo_cpu(self, cpu: CPU, tick_fim: int) -> Tuple[str, Optional[str]]:
        """Executa 1 ciclo na CPU e verifica se a tarefa alocada concluiu sua duração."""
        tcb_exec = cpu.executar_ciclo()
        if tcb_exec is None:
            return f"C{cpu.id_cpu} ociosa → registrar_ociosidade() (acumulado: {cpu.tempo_desligado}t OFF)", None

        msg_cpu = f"C{cpu.id_cpu} executou T{tcb_exec.id_tarefa} ({tcb_exec.tempo_ja_executado}/{tcb_exec.duracao})"
        if tcb_exec.tempo_ja_executado >= tcb_exec.duracao:
            tcb_exec.execucoes_completadas += 1
            tcb_exec.id_cpu_alocada = None
            tcb_exec.sofreu_atraso = False
            if tcb_exec.execucoes_completadas >= self.LIMITE_EXECUCOES_PROJETO_A:
                tcb_exec.estado = EstadoTarefa.FINALIZADA
                destino = "FINALIZADA"
            else:
                tcb_exec.estado = EstadoTarefa.AGUARDANDO
                destino = f"AGUARDANDO T{tcb_exec.obter_proximo_inicio()}"
            cpu.liberar()
            self.registrar_evento(tcb_exec.id_tarefa, tick_fim, "TERMINO")
            msg_termino = (
                f"T{tcb_exec.id_tarefa} concluiu ({tcb_exec.duracao}/{tcb_exec.duracao}) "
                f"→ {destino} (Ciclo {tcb_exec.execucoes_completadas}/10, CPU.liberar())"
            )
            return msg_cpu, msg_termino

        return msg_cpu, None

    def _registrar_log_conclusao(self, tick_fim: int, terminos: List[str], atrasos_fim: List[str]) -> None:
        """Registra o log sintético de concluir_intervalo_tick."""
        partes = terminos + atrasos_fim
        detalhe = (
            " | ".join(partes)
            if partes
            else "Prazos verificados; nenhum término ou estouro de DeadLine no fim do tick."
        )
        categoria = "DEADLINE" if atrasos_fim else ("CONCLUSAO" if terminos else "INFO")
        self.registrar_log(
            funcao=f"GerenciadorTarefas.concluir_intervalo_tick({tick_fim})",
            detalhe=detalhe,
            categoria=categoria,
        )

    def atualizar_ciclo_de_vida(self, tick_atual: int) -> None:
        """Atualiza o ciclo de vida após edição manual pelo usuário."""
        self.preparar_inicio_intervalo(tick_atual)

    def obter_elegiveis(self) -> List[TCB]:
        """Retorna todas as tarefas válidas aptas a disputar a CPU (PRONTA e EXECUTANDO)."""
        return [
            t for t in self.tcbs
            if self._tarefa_configurada_valida(t)
            and t.estado in (EstadoTarefa.PRONTA, EstadoTarefa.EXECUTANDO)
            and t.execucoes_completadas < self.LIMITE_EXECUCOES_PROJETO_A
        ]

    def todas_finalizadas(self) -> bool:
        """Indica se todas as tarefas válidas do sistema completaram suas 10 execuções."""
        tarefas_validas = [t for t in self.tcbs if self._tarefa_configurada_valida(t)]
        if not tarefas_validas:
            return False
        return all(
            t.estado == EstadoTarefa.FINALIZADA and t.execucoes_completadas >= self.LIMITE_EXECUCOES_PROJETO_A
            for t in tarefas_validas
        )
