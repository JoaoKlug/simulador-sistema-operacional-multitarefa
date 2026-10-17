import re
from typing import List, Optional
from core.hardware.cpu import CPU
from core.hardware.hardware import Hardware
from core.kernel.tcb import TCB, ParametrosTarefa, EventoTarefaTick
from core.kernel.kernel import Kernel
from core.logger import limpar_log, log_core, log_secao
from core.processos.estado_tarefa import EstadoTarefa


class SistemaOperacional:
    """
    Fachada Principal do Sistema Operacional (Maziero, Cap. 2, Figura 2.1).
    Integra o Hardware físico e o Núcleo Monolítico (Kernel), oferecendo a interface
    unificada para inspeção e modificação validada de parâmetros e tarefas em tempo
    de execução (Requisitos 1.5.2, 3.1 e 3.4).
    """
    PADRAO_COR_HEX = re.compile(r"^[0-9A-Fa-f]{6}$")

    def __init__(
        self,
        qtde_cpus: int,
        algoritmo: str,
        quantum: int,
        tarefas: List[TCB],
    ) -> None:
        if qtde_cpus < 1:
            raise ValueError("A quantidade de processadores (CPUs) deve ser no mínimo 1.")
        if quantum < 0:
            raise ValueError("O quantum não pode ser negativo.")

        limpar_log()
        log_secao("INICIALIZAÇÃO DO SISTEMA OPERACIONAL (TICK 0)")

        self.quantum_global: int = quantum
        self.hardware: Hardware = Hardware(qtde_cpus=qtde_cpus, tick_inicial=0)
        self.kernel: Kernel = Kernel(hardware=self.hardware, algoritmo=algoritmo, tcbs=tarefas)

        tarefas_resumo = [
            f"T{t.id_tarefa}(Ing={t.instante_ingresso}, Dur={t.duracao}, P={t.periodo}, DL={t.prazo_relativo})"
            for t in tarefas
            if t.duracao > 0 and t.periodo > 0
        ]
        texto_tarefas = ", ".join(tarefas_resumo) if tarefas_resumo else "1 tarefa padrão (NOVA, parâmetros zerados)"
        log_core(
            "SistemaOperacional.__init__",
            f"Sistema inicializado | CPUs={qtde_cpus} | Política={algoritmo.upper()} | Quantum={quantum} | Tarefas=[{texto_tarefas}].",
        )

    def avancar_tempo(self) -> int:
        """
        Aciona o pulso do temporizador físico do Hardware (IRQ 0), que interrompe
        e notifica diretamente o tratador registrado pelo Kernel (Maziero, Cap. 2, Seção 2.2.2).
        """
        return self.hardware.gerar_interrupcao_tick()

    def modificar_parametros_sistema(self, algoritmo: str, quantum: int, qtde_cpus: int) -> None:
        """
        Altera parâmetros globais do sistema antes ou durante a simulação (Requisito 3.1),
        validando semanticamente os novos valores.
        """
        if qtde_cpus < 1:
            raise ValueError("Modificação inválida: a quantidade de CPUs deve ser no mínimo 1.")
        if quantum < 0:
            raise ValueError("Modificação inválida: o quantum não pode ser negativo.")

        log_secao(f"CONFIGURAÇÃO DO SISTEMA (TICK {self.tick_atual})")
        self.kernel.gerenciador_tarefas.limpar_eventos_tick()
        self.kernel.alterar_algoritmo(algoritmo)
        self.quantum_global = quantum
        self._redimensionar_cpus(qtde_cpus)

        log_core(
            "SistemaOperacional.modificar_parametros_sistema",
            f"Parâmetros globais atualizados: Escalonador={algoritmo.upper()} | Quantum={quantum} | CPUs={qtde_cpus}.",
        )
        self.kernel.reescalonar_estado_atual(self.tick_atual)

    def _redimensionar_cpus(self, qtde_cpus: int) -> None:
        """Adiciona ou remove processadores físicos preservando o contexto das tarefas ativas."""
        atual_cpus = len(self.hardware.cpus)
        if qtde_cpus > atual_cpus:
            for i in range(atual_cpus, qtde_cpus):
                self.hardware.cpus.append(CPU(id_cpu=i + 1))
        elif qtde_cpus < atual_cpus:
            for cpu_removida in self.hardware.cpus[qtde_cpus:]:
                if cpu_removida.tcb_atual is not None:
                    self.kernel.despachante.salvar_contexto(cpu_removida.tcb_atual, cpu_removida)
            self.hardware.cpus = self.hardware.cpus[:qtde_cpus]

    def adicionar_tarefa(self, params: ParametrosTarefa) -> None:
        """Adiciona uma nova tarefa ao sistema com validação semântica completa."""
        if any(t.id_tarefa == params.id_tarefa for t in self.tarefas):
            raise ValueError(f"Modificação inválida: já existe uma tarefa com o ID {params.id_tarefa}.")

        cor_limpa = params.cor_hex.strip().lstrip("#").upper()
        self._validar_atributos_tarefa(params, cor_limpa)

        novo_tcb = TCB(
            id_tarefa=params.id_tarefa,
            cor_hex=cor_limpa,
            instante_ingresso=params.instante_ingresso,
            duracao=params.duracao,
            periodo=params.periodo,
            prazo_relativo=params.prazo_relativo,
            tick_inicio_ciclo_atual=params.instante_ingresso,
        )
        log_secao(f"ADIÇÃO DE TAREFA (TICK {self.tick_atual})")
        self.kernel.gerenciador_tarefas.limpar_eventos_tick()
        self.kernel.gerenciador_tarefas.tcbs.append(novo_tcb)
        log_core(
            "SistemaOperacional.adicionar_tarefa",
            f"Criado TCB de T{params.id_tarefa} no estado NOVA "
            f"(Ingresso={params.instante_ingresso}, Duração={params.duracao}, "
            f"Período={params.periodo}, DL_Rel={params.prazo_relativo}).",
        )
        self.kernel.reescalonar_estado_atual(self.tick_atual)

    def modificar_tarefa(self, params: ParametrosTarefa) -> None:
        """
        Modifica manualmente o estado atual ou as características de uma tarefa em qualquer
        estágio da simulação, validando a semântica da alteração (Requisitos 1.5.2, 3.1 e 3.4).
        """
        tcb: Optional[TCB] = next((t for t in self.tarefas if t.id_tarefa == params.id_tarefa), None)
        if tcb is None:
            raise ValueError(f"Tarefa {params.id_tarefa} não encontrada no sistema.")

        cor_limpa = params.cor_hex.strip().lstrip("#").upper()
        self._validar_atributos_tarefa(params, cor_limpa)

        novo_estado = self._interpretar_estado(params.novo_estado)
        self._validar_transicao_estado(tcb, params, novo_estado)

        estado_anterior = tcb.estado
        log_secao(f"EDIÇÃO MANUAL DE TAREFA T{params.id_tarefa} (TICK {self.tick_atual})")
        self.kernel.gerenciador_tarefas.limpar_eventos_tick()
        novo_estado_efetivo = self._aplicar_parametros_no_tcb(tcb, params, cor_limpa, novo_estado)

        log_core(
            "SistemaOperacional.modificar_tarefa",
            f"T{params.id_tarefa} atualizada: Estado={estado_anterior.value}->{novo_estado_efetivo.value} | "
            f"Exec={tcb.tempo_ja_executado}/{tcb.duracao} | Período={tcb.periodo} | "
            f"DL_Rel={tcb.prazo_relativo} | DL_Abs={tcb.prazo_absoluto_atual}.",
        )
        self._realocar_cpu_apos_edicao(tcb, estado_anterior, novo_estado_efetivo)

    def _interpretar_estado(self, novo_estado_str: str) -> EstadoTarefa:
        """Converte o nome textual do estado em uma instância de EstadoTarefa."""
        estado_norm = novo_estado_str.strip().upper()
        if estado_norm.startswith("AGUARDANDO"):
            return EstadoTarefa.AGUARDANDO
        try:
            return EstadoTarefa[estado_norm]
        except KeyError:
            raise ValueError(f"Estado '{novo_estado_str}' inválido.")

    def _validar_transicao_estado(
        self,
        tcb: TCB,
        params: ParametrosTarefa,
        novo_estado: EstadoTarefa,
    ) -> None:
        """Valida se o estado e progresso desejados são semanticamente compatíveis com o relógio atual."""
        if novo_estado != EstadoTarefa.NOVA and self.tick_atual < params.instante_ingresso:
            raise ValueError(
                f"Modificação semanticamente inválida: a Tarefa {tcb.id_tarefa} não pode assumir o estado "
                f"'{novo_estado.value}' no Tick {self.tick_atual} porque seu instante de ingresso é "
                f"apenas no Tick {params.instante_ingresso}."
            )

        if novo_estado == EstadoTarefa.NOVA:
            if self.tick_atual > params.instante_ingresso:
                raise ValueError(
                    f"Modificação semanticamente inválida: a Tarefa {tcb.id_tarefa} não pode voltar ao estado 'NOVA' "
                    f"no Tick {self.tick_atual} mantendo instante de ingresso {params.instante_ingresso} < {self.tick_atual}."
                )
            if tcb.execucoes_completadas > 0:
                raise ValueError(
                    f"Modificação semanticamente inválida: a Tarefa {tcb.id_tarefa} já concluiu "
                    f"{tcb.execucoes_completadas} ciclo(s) e não pode voltar ao estado inicial 'NOVA'."
                )

        if novo_estado != EstadoTarefa.FINALIZADA and tcb.execucoes_completadas >= 10:
            raise ValueError(
                f"Modificação semanticamente inválida: a Tarefa {tcb.id_tarefa} já completou o limite de "
                f"10 execuções do Projeto A e encerrou seu ciclo."
            )

        if novo_estado in (EstadoTarefa.PRONTA, EstadoTarefa.EXECUTANDO, EstadoTarefa.SUSPENSA):
            if params.tempo_ja_executado >= params.duracao:
                raise ValueError(
                    f"Modificação semanticamente inválida: para manter a Tarefa {tcb.id_tarefa} em "
                    f"'{novo_estado.value}', a Execução Atual ({params.tempo_ja_executado}) deve ser menor "
                    f"que a Duração ({params.duracao}). Para encerrar o ciclo atual, selecione 'AGUARDANDO'."
                )

    def _aplicar_parametros_no_tcb(
        self,
        tcb: TCB,
        params: ParametrosTarefa,
        cor_limpa: str,
        novo_estado: EstadoTarefa,
    ) -> EstadoTarefa:
        """
        Atualiza os atributos temporais, prazo absoluto e indicador de atraso no TCB.
        Garante que alterar o Período não altere a DeadLine Abs. do ciclo atual.
        """
        tcb.cor_hex = cor_limpa
        tcb.instante_ingresso = params.instante_ingresso
        tcb.duracao = params.duracao
        tcb.periodo = params.periodo
        tcb.prazo_relativo = params.prazo_relativo

        if novo_estado == EstadoTarefa.NOVA:
            tcb.tempo_ja_executado = 0
            tcb.tick_inicio_ciclo_atual = params.instante_ingresso
            tcb.prazo_absoluto_atual = 0
            tcb.sofreu_atraso = False
            return EstadoTarefa.NOVA

        if novo_estado == EstadoTarefa.FINALIZADA:
            tcb.tempo_ja_executado = params.duracao
            tcb.execucoes_completadas = 10
            tcb.sofreu_atraso = False
            return EstadoTarefa.FINALIZADA

        if novo_estado == EstadoTarefa.AGUARDANDO:
            return self._configurar_estado_aguardando(tcb, params)

        # Estados ativos: PRONTA, EXECUTANDO ou SUSPENSA
        if tcb.estado in (EstadoTarefa.NOVA, EstadoTarefa.AGUARDANDO, EstadoTarefa.FINALIZADA):
            tcb.tick_inicio_ciclo_atual = self.tick_atual

        tcb.tempo_ja_executado = params.tempo_ja_executado
        tcb.prazo_absoluto_atual = tcb.tick_inicio_ciclo_atual + params.prazo_relativo
        tcb.sofreu_atraso = (
            self.tick_atual >= tcb.prazo_absoluto_atual and tcb.tempo_ja_executado < tcb.duracao
        )
        return novo_estado

    def _configurar_estado_aguardando(self, tcb: TCB, params: ParametrosTarefa) -> EstadoTarefa:
        """Configura o TCB quando a tarefa está ou é colocada manualmente em AGUARDANDO."""
        if tcb.estado != EstadoTarefa.AGUARDANDO:
            tcb.execucoes_completadas = min(10, tcb.execucoes_completadas + 1)
            tcb.tempo_ja_executado = params.duracao
            tcb.sofreu_atraso = False
            if tcb.execucoes_completadas >= 10:
                return EstadoTarefa.FINALIZADA
            if tcb.tick_inicio_ciclo_atual + params.periodo <= self.tick_atual:
                tcb.tick_inicio_ciclo_atual = self.tick_atual
        else:
            tcb.tempo_ja_executado = min(params.tempo_ja_executado, params.duracao)
            tcb.sofreu_atraso = False
        return EstadoTarefa.AGUARDANDO

    def _realocar_cpu_apos_edicao(
        self,
        tcb: TCB,
        estado_anterior: EstadoTarefa,
        novo_estado: EstadoTarefa,
    ) -> None:
        """Ajusta a alocação física das CPUs sem duplicar tarefas e reescalona o Kernel."""
        if novo_estado in (
            EstadoTarefa.SUSPENSA,
            EstadoTarefa.AGUARDANDO,
            EstadoTarefa.FINALIZADA,
            EstadoTarefa.NOVA,
        ):
            self._liberar_cpu_da_tarefa(tcb)
            tcb.estado = novo_estado
            self.kernel.reescalonar_estado_atual(self.tick_atual)
            return

        if novo_estado == EstadoTarefa.PRONTA:
            self._liberar_cpu_da_tarefa(tcb)
            tcb.estado = EstadoTarefa.PRONTA
            self.kernel.reescalonar_estado_atual(self.tick_atual)
            return

        # novo_estado == EstadoTarefa.EXECUTANDO
        if estado_anterior == EstadoTarefa.EXECUTANDO:
            tcb.estado = EstadoTarefa.EXECUTANDO
            self.kernel.reescalonar_estado_atual(self.tick_atual)
            return

        self._liberar_cpu_da_tarefa(tcb)
        cpu_alvo = next((c for c in self.hardware.cpus if c.tcb_atual is None), self.hardware.cpus[-1])
        if cpu_alvo.tcb_atual is not None and cpu_alvo.tcb_atual.id_tarefa != tcb.id_tarefa:
            self.kernel.despachante.salvar_contexto(cpu_alvo.tcb_atual, cpu_alvo)
        self.kernel.despachante.restaurar_contexto(tcb, cpu_alvo)

    def _liberar_cpu_da_tarefa(self, tcb: TCB) -> None:
        """Remove a tarefa de qualquer CPU em que esteja alocada."""
        for cpu in self.hardware.cpus:
            if cpu.tcb_atual is not None and cpu.tcb_atual.id_tarefa == tcb.id_tarefa:
                cpu.liberar()
        tcb.id_cpu_alocada = None

    def _validar_atributos_tarefa(self, params: ParametrosTarefa, cor_limpa: str) -> None:
        """Valida os campos numéricos e o código hexadecimal de cor de uma tarefa."""
        if not self.PADRAO_COR_HEX.match(cor_limpa):
            raise ValueError(
                f"Cor hexadecimal '{cor_limpa}' inválida. Informe 6 dígitos hexadecimais (ex: F0E0D0)."
            )
        if params.instante_ingresso < 0:
            raise ValueError("Modificação inválida: o instante de ingresso não pode ser negativo.")
        if params.duracao <= 0:
            raise ValueError("Modificação inválida: a duração da tarefa deve ser maior que zero.")
        if params.periodo < 0:
            raise ValueError("Modificação inválida: o período não pode ser negativo (erro de configuração).")
        if params.periodo == 0:
            raise ValueError(
                "Modificação inválida no Projeto A: período igual a 0 indica tarefa aperiódica, "
                "que é abordada apenas no Projeto B (Requisito 4.4)."
            )
        if params.prazo_relativo <= 0:
            raise ValueError("Modificação inválida: o prazo (deadline) deve ser maior que zero.")
        if params.tempo_ja_executado < 0 or params.tempo_ja_executado > params.duracao:
            raise ValueError(
                f"Modificação inválida: o tempo já executado ({params.tempo_ja_executado}) "
                f"deve estar entre 0 e a duração ({params.duracao})."
            )

    @property
    def tick_atual(self) -> int:
        return self.hardware.tick_atual

    @property
    def tarefas(self) -> List[TCB]:
        return self.kernel.gerenciador_tarefas.tcbs

    @property
    def eventos_tick_atual(self) -> List[EventoTarefaTick]:
        return self.kernel.gerenciador_tarefas.eventos_tick_atual

    @property
    def cpus(self) -> List[CPU]:
        return self.hardware.cpus

    @property
    def qtde_cpus(self) -> int:
        return len(self.hardware.cpus)

    @property
    def nome_algoritmo(self) -> str:
        return self.kernel.algoritmo

    def finalizado(self) -> bool:
        return self.kernel.gerenciador_tarefas.todas_finalizadas()
