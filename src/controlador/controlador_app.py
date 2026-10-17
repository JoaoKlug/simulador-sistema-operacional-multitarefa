from dataclasses import dataclass
from typing import Any, List, Dict, Optional, Tuple
from core.sistema_operacional import SistemaOperacional
from core.kernel.tcb import TCB, ParametrosTarefa
from simulador.simulador import Simulador
from controlador.dtos import (
    DadosEdicaoTarefaDTO,
    DadosCabecalhoDTO,
    CardTCBDTO,
    SegmentoGanttDTO,
    MarcadorEventoGanttDTO,
    DadosGanttDTO,
    ChamadaFuncaoLogDTO,
    BlocoLogTickDTO,
    LogsDidaticosDTO,
)


@dataclass(frozen=True)
class _EstadoIntervaloTarefa:
    """Estrutura auxiliar interna que agrupa o estado visual de uma tarefa em um intervalo [t, t+1)."""
    id_tarefa: int
    estado_nome: str
    cor_hex: str
    id_cpu: Optional[int]
    atraso: bool


class ControladorApp:
    """
    Controlador / Presenter da Aplicação (Padrão Passive View / MVP).
    Faz a mediação entre a GUI (100% Dummy) e o Simulador:
    - Recebe comandos da interface gráfica.
    - Orquestra o Simulador.
    - Converte o estado do Sistema Operacional em DTOs fortemente tipados (@dataclass).
    """
    NOMES_ALGORITMOS = {
        "rm": "Rate Monotonic",
        "edf": "Earliest DeadLine First",
    }

    def __init__(self) -> None:
        self.simulador: Simulador = Simulador()

    def carregar_arquivo(self, caminho_arquivo: str) -> List[str]:
        """Comanda o carregamento do arquivo .txt e retorna eventuais avisos."""
        return self.simulador.carregar_arquivo(caminho_arquivo)

    def configurar_sistema(self, algoritmo: str, quantum: int, qtde_cpus: int) -> None:
        """Aplica ou inicializa os parâmetros globais do sistema com validação."""
        self.simulador.inicializar_sistema_customizado(
            algoritmo=algoritmo,
            quantum=quantum,
            qtde_cpus=qtde_cpus,
        )

    def adicionar_tarefa(self, dados: DadosEdicaoTarefaDTO) -> None:
        """Adiciona uma nova tarefa antes ou durante a simulação."""
        self.simulador.adicionar_tarefa_em_execucao(self._converter_para_parametros(dados))

    def modificar_tarefa(self, dados: DadosEdicaoTarefaDTO) -> None:
        """Modifica manualmente uma tarefa existente em qualquer estágio da simulação."""
        self.simulador.modificar_tarefa_em_execucao(self._converter_para_parametros(dados))

    def _converter_para_parametros(self, dados: DadosEdicaoTarefaDTO) -> ParametrosTarefa:
        """Converte o DTO de edição da GUI no Value Object de parâmetros do domínio."""
        return ParametrosTarefa(
            id_tarefa=dados.id_tarefa,
            cor_hex=dados.cor_hex,
            instante_ingresso=dados.instante_ingresso,
            duracao=dados.duracao,
            periodo=dados.periodo,
            prazo_relativo=dados.prazo_relativo,
            novo_estado=dados.novo_estado,
            tempo_ja_executado=dados.tempo_ja_executado,
        )

    def avancar_tick(self) -> None:
        """Avança 1 tick na simulação."""
        self.simulador.avancar_tick()

    def retroceder_tick(self) -> bool:
        """Retrocede 1 passo no histórico da simulação."""
        return self.simulador.retroceder_tick()

    def executar_completo(self) -> bool:
        """Executa a simulação completa até a finalização de todas as tarefas."""
        return self.simulador.executar_completo()

    def tem_simulacao_ativa(self) -> bool:
        """Indica se há um Sistema Operacional carregado/ativo."""
        return self.simulador.so_atual is not None

    def obter_dados_cabecalho(self) -> DadosCabecalhoDTO:
        """Gera o DTO tipado com as configurações atuais de forma assertiva, padronizada e sem parênteses."""
        so = self.simulador.so_atual
        if not so:
            return self._obter_cabecalho_padrao()

        finalizou = so.finalizado()
        pode_retroceder = self.simulador.historico.pode_retroceder()
        maior_id = max((t.id_tarefa for t in so.tarefas), default=0)

        nome_extenso = self.NOMES_ALGORITMOS.get(so.nome_algoritmo.lower(), so.nome_algoritmo.upper())
        linha_1 = f"Tick Atual: {so.tick_atual}   |   Escalonador: {nome_extenso}"
        linha_2 = f"Processadores: {so.qtde_cpus}   |   Quantum: {so.quantum_global}"

        return DadosCabecalhoDTO(
            texto_info=f"{linha_1} | {linha_2}",
            texto_linha_1=linha_1,
            texto_linha_2=linha_2,
            pode_avancar=not finalizou,
            pode_retroceder=pode_retroceder,
            pode_executar_completo=not finalizou,
            simulacao_finalizada=finalizou,
            algoritmo_atual=so.nome_algoritmo.upper(),
            quantum_atual=so.quantum_global,
            qtde_cpus_atual=so.qtde_cpus,
            proximo_id_sugerido=maior_id + 1,
        )

    def _obter_cabecalho_padrao(self) -> DadosCabecalhoDTO:
        """Retorna os valores padrão do cabeçalho quando nenhuma simulação foi iniciada."""
        nome_extenso = self.NOMES_ALGORITMOS.get(self.simulador.ALGORITMO_PADRAO.lower(), "Rate Monotonic")
        l1 = f"Tick Atual: 0   |   Escalonador: {nome_extenso}"
        l2 = f"Processadores: {self.simulador.QTDE_CPUS_PADRAO}   |   Quantum: {self.simulador.QUANTUM_PADRAO}"
        return DadosCabecalhoDTO(
            texto_info=f"{l1} | {l2}",
            texto_linha_1=l1,
            texto_linha_2=l2,
            pode_avancar=False,
            pode_retroceder=False,
            pode_executar_completo=False,
            simulacao_finalizada=False,
            algoritmo_atual=self.simulador.ALGORITMO_PADRAO.upper(),
            quantum_atual=self.simulador.QUANTUM_PADRAO,
            qtde_cpus_atual=self.simulador.QTDE_CPUS_PADRAO,
            proximo_id_sugerido=1,
        )

    def obter_dados_cards_tcb(self) -> List[CardTCBDTO]:
        """Gera a lista de DTOs tipados para os cards de TCB de forma sintética, padronizada e sem parênteses."""
        so = self.simulador.so_atual
        if not so:
            return []
        return [self._criar_card_tcb_dto(tcb) for tcb in sorted(so.tarefas, key=lambda t: t.id_tarefa)]

    def _criar_card_tcb_dto(self, tcb: TCB) -> CardTCBDTO:
        """Constrói o DTO de um card individual de TCB a partir do estado atual da tarefa."""
        is_executando = tcb.estado.name == "EXECUTANDO"
        if is_executando:
            cor_indicador = f"#{tcb.cor_hex}"
        elif tcb.estado.name == "SUSPENSA":
            cor_indicador = "black"
        else:
            cor_indicador = "white"

        titulo = (
            f"Tarefa {tcb.id_tarefa} · C{tcb.id_cpu_alocada}"
            if is_executando and tcb.id_cpu_alocada is not None
            else f"Tarefa {tcb.id_tarefa}"
        )

        if tcb.estado.name == "AGUARDANDO":
            proximo_tick = tcb.obter_proximo_inicio()
            nome_estado_exibicao = f"AGUARDANDO T{proximo_tick}"
        else:
            nome_estado_exibicao = tcb.estado.value

        linhas_info = [
            f"Estado: {nome_estado_exibicao}",
            f"Execução: {tcb.tempo_ja_executado}/{tcb.duracao}",
            f"Ciclos: {tcb.execucoes_completadas}/10",
            f"Ingresso: {tcb.instante_ingresso}",
            f"Período: {tcb.periodo}",
            f"DeadLine Rel.: {tcb.prazo_relativo}",
            f"DeadLine Abs.: {tcb.prazo_absoluto_atual}",
        ]

        return CardTCBDTO(
            id_tarefa=tcb.id_tarefa,
            titulo=titulo,
            cor_indicador=cor_indicador,
            nome_estado=nome_estado_exibicao,
            texto_progresso=f"Execução: {tcb.tempo_ja_executado}/{tcb.duracao}",
            texto_periodo_prazo=f"Período: {tcb.periodo}",
            texto_prazo_absoluto=f"DeadLine Abs.: {tcb.prazo_absoluto_atual}",
            texto_execucoes=f"Ciclos: {tcb.execucoes_completadas}/10",
            esta_atrasada=tcb.sofreu_atraso,
            cor_hex=tcb.cor_hex,
            instante_ingresso=tcb.instante_ingresso,
            duracao=tcb.duracao,
            periodo=tcb.periodo,
            prazo_relativo=tcb.prazo_relativo,
            tempo_ja_executado=tcb.tempo_ja_executado,
            linhas_informacao=linhas_info,
        )

    def obter_dados_gantt(self, para_exportacao: bool = False) -> DadosGanttDTO:
        """
        Compila todo o histórico de snapshots em um DadosGanttDTO pronto para o DesenhistaGantt.
        - Ordena o eixo Y em ordem decrescente de ID (menor ID na base, próximo ao eixo X — Req. 2.5).
        - Mapeia cada intervalo concluído [t, t+1) para seu estado real executado.
        - Constrói a faixa compacta de ociosidade (CPU OFF) das CPUs desligadas em cada ciclo.
        """
        estados = self.simulador.obter_todos_estados()
        if not estados:
            return DadosGanttDTO(max_tick=0, tarefas_eixo_y=[], cpus_ids=[])

        so_atual = estados[-1]
        max_tick = so_atual.tick_atual
        mapa_por_tick, tarefas_eixo_y, cpus_ids, eventos_vistos = self._coletar_historico_gantt(
            estados, max_tick
        )
        segmentos = self._compilar_segmentos_tarefas(
            tarefas_eixo_y, mapa_por_tick, max_tick, para_exportacao
        )
        segmentos_off = self._compilar_segmentos_cpus_off(mapa_por_tick, max_tick)
        resumo_off = "   |   ".join(f"C{c.id_cpu}: {c.tempo_desligado} ticks" for c in so_atual.cpus)

        return DadosGanttDTO(
            max_tick=max_tick,
            tarefas_eixo_y=tarefas_eixo_y,
            cpus_ids=cpus_ids,
            segmentos=segmentos,
            eventos=eventos_vistos,
            segmentos_cpus_desligadas=segmentos_off,
            resumo_cpus_desligadas=resumo_off,
        )

    def _coletar_historico_gantt(
        self,
        estados: List[SistemaOperacional],
        max_tick: int,
    ) -> Tuple[Dict[int, SistemaOperacional], List[int], List[int], List[MarcadorEventoGanttDTO]]:
        """Extrai o mapa temporal de estados, IDs ordenados de tarefas/CPUs e marcadores de eventos."""
        mapa_por_tick: Dict[int, SistemaOperacional] = {}
        todas_tarefas_ids: set[int] = set()
        todas_cpus_ids: set[int] = set()
        eventos_vistos: List[MarcadorEventoGanttDTO] = []

        for est in estados:
            if est.tick_atual not in mapa_por_tick:
                mapa_por_tick[est.tick_atual] = est
            todas_tarefas_ids.update(t.id_tarefa for t in est.tarefas)
            todas_cpus_ids.update(c.id_cpu for c in est.cpus)
            self._acumular_eventos_estado(est, max_tick, eventos_vistos)

        tarefas_eixo_y = sorted(list(todas_tarefas_ids), reverse=True)
        cpus_ids = sorted(list(todas_cpus_ids))
        return mapa_por_tick, tarefas_eixo_y, cpus_ids, eventos_vistos

    def _acumular_eventos_estado(
        self,
        est: SistemaOperacional,
        max_tick: int,
        eventos_vistos: List[MarcadorEventoGanttDTO],
    ) -> None:
        """Adiciona eventos únicos de um snapshot à lista global de marcadores do Gantt."""
        for ev in est.eventos_tick_atual:
            if ev.tipo == "SORTEIO" and ev.tick >= max_tick:
                continue
            dto_ev = MarcadorEventoGanttDTO(id_tarefa=ev.id_tarefa, tick=ev.tick, tipo=ev.tipo)
            if dto_ev not in eventos_vistos:
                eventos_vistos.append(dto_ev)

    def _compilar_segmentos_tarefas(
        self,
        tarefas_eixo_y: List[int],
        mapa_por_tick: Dict[int, SistemaOperacional],
        max_tick: int,
        para_exportacao: bool,
    ) -> List[SegmentoGanttDTO]:
        """Compila os blocos retangulares contínuos de todas as tarefas no intervalo [0, max_tick)."""
        segmentos: List[SegmentoGanttDTO] = []
        for id_tarefa in tarefas_eixo_y:
            segmentos.extend(
                self._compilar_segmentos_tarefa_individual(
                    id_tarefa, mapa_por_tick, max_tick, para_exportacao
                )
            )
        return segmentos

    def _agrupar_intervalos_contiguos(
        self,
        amostras: List[Tuple[int, object]],
    ) -> List[Tuple[int, int, Any]]:
        """Agrupa ticks consecutivos [t, t+1) que compartilham o mesmo valor em intervalos [inicio, fim)."""
        grupos: List[Tuple[int, int, Any]] = []
        for tick, valor in amostras:
            if grupos and grupos[-1][2] == valor and grupos[-1][1] == tick:
                ini, _, val_ant = grupos[-1]
                grupos[-1] = (ini, tick + 1, val_ant)
            else:
                grupos.append((tick, tick + 1, valor))
        return grupos

    def _compilar_segmentos_tarefa_individual(
        self,
        id_tarefa: int,
        mapa_por_tick: Dict[int, SistemaOperacional],
        max_tick: int,
        para_exportacao: bool,
    ) -> List[SegmentoGanttDTO]:
        """Agrupa ticks adjacentes de mesmo estado/CPU/atraso de uma tarefa em segmentos contínuos."""
        amostras: List[Tuple[int, object]] = []
        for tck in range(0, max_tick):
            info = self._extrair_estado_intervalo_tarefa(id_tarefa, mapa_por_tick.get(tck + 1))
            if info is not None:
                amostras.append((tck, info))

        segmentos: List[SegmentoGanttDTO] = []
        for ini, fim, info in self._agrupar_intervalos_contiguos(amostras):
            seg = self._criar_segmento_tarefa_dto(info, ini, fim, para_exportacao)
            if seg is not None:
                segmentos.append(seg)
        return segmentos

    def _extrair_estado_intervalo_tarefa(
        self,
        id_tarefa: int,
        est_intervalo: Optional[SistemaOperacional],
    ) -> Optional[_EstadoIntervaloTarefa]:
        """Obtém o estado executado por uma tarefa em um snapshot específico do histórico."""
        if est_intervalo is None:
            return None
        tcb = next((t for t in est_intervalo.tarefas if t.id_tarefa == id_tarefa), None)
        if tcb is None or tcb.estado_ultimo_intervalo is None:
            return None

        est_nome = tcb.estado_ultimo_intervalo.name
        cpu_aloc = tcb.cpu_ultimo_intervalo if est_nome == "EXECUTANDO" else None
        return _EstadoIntervaloTarefa(
            id_tarefa=id_tarefa,
            estado_nome=est_nome,
            cor_hex=tcb.cor_hex,
            id_cpu=cpu_aloc,
            atraso=tcb.atraso_ultimo_intervalo,
        )

    def _criar_segmento_tarefa_dto(
        self,
        info: _EstadoIntervaloTarefa,
        tick_inicio: int,
        tick_fim: int,
        para_exportacao: bool,
    ) -> Optional[SegmentoGanttDTO]:
        """Cria um SegmentoGanttDTO para estados visíveis (EXECUTANDO, PRONTA, SUSPENSA)."""
        if info.estado_nome in ("NOVA", "AGUARDANDO", "FINALIZADA") or tick_fim <= tick_inicio:
            return None

        cor_borda = "#D32F2F" if info.atraso else "black"
        largura_borda = 2 if info.atraso else 1
        cor_preenchimento: Optional[str] = None
        pontilhado = False
        texto_interno = ""

        if info.estado_nome == "EXECUTANDO":
            cor_preenchimento = f"#{info.cor_hex}"
            texto_interno = f"C{info.id_cpu}" if info.id_cpu is not None else ""
        elif info.estado_nome == "SUSPENSA":
            cor_preenchimento = "white"
            pontilhado = True
        elif info.estado_nome == "PRONTA":
            cor_preenchimento = None if para_exportacao else "white"

        return SegmentoGanttDTO(
            id_tarefa=info.id_tarefa,
            tick_inicio=tick_inicio,
            tick_fim=tick_fim,
            estado=info.estado_nome,
            cor_preenchimento=cor_preenchimento,
            cor_borda=cor_borda,
            largura_borda=largura_borda,
            texto=texto_interno,
            cor_texto="black",
            pontilhado=pontilhado,
        )

    def _compilar_segmentos_cpus_off(
        self,
        mapa_por_tick: Dict[int, SistemaOperacional],
        max_tick: int,
    ) -> List[SegmentoGanttDTO]:
        """Agrupa os intervalos contínuos em que uma ou mais CPUs permaneceram ociosas (CPU OFF)."""
        amostras: List[Tuple[int, object]] = []
        for tck in range(0, max_tick):
            rotulo = self._obter_rotulo_off_no_tick(mapa_por_tick.get(tck + 1))
            if rotulo:
                amostras.append((tck, rotulo))

        return [
            self._criar_segmento_cpu_off_dto(ini, fim, rotulo)
            for ini, fim, rotulo in self._agrupar_intervalos_contiguos(amostras)
        ]

    def _obter_rotulo_off_no_tick(self, est_intervalo: Optional[SistemaOperacional]) -> str:
        """Retorna o rótulo compacto das CPUs desligadas em um snapshot ou string vazia."""
        if est_intervalo is None:
            return ""
        ids_desligadas = sorted(c.id_cpu for c in est_intervalo.cpus if c.desligada_no_tick)
        return self._formatar_rotulo_cpus_off(ids_desligadas)

    def _criar_segmento_cpu_off_dto(self, tick_inicio: int, tick_fim: int, rotulo: str) -> SegmentoGanttDTO:
        """Instancia um SegmentoGanttDTO padronizado para a faixa de CPUs desligadas."""
        return SegmentoGanttDTO(
            id_tarefa=0,
            tick_inicio=tick_inicio,
            tick_fim=tick_fim,
            estado="CPU_DESLIGADA",
            cor_preenchimento=None,
            cor_borda="#7F8C8D",
            largura_borda=1,
            texto=rotulo,
            cor_texto="#555555",
            pontilhado=False,
        )

    def _formatar_rotulo_cpus_off(self, ids_off: List[int]) -> str:
        """Formata de modo enxuto a lista de CPUs ociosas em um tick (ex: 'C1', 'C1,C2', 'C1-C4')."""
        if not ids_off:
            return ""
        if len(ids_off) == 1:
            return f"C{ids_off[0]}"
        if len(ids_off) == 2:
            return f"C{ids_off[0]},C{ids_off[1]}"
        if ids_off == list(range(ids_off[0], ids_off[-1] + 1)):
            return f"C{ids_off[0]}-C{ids_off[-1]}"
        return f"{len(ids_off)}C"

    def obter_dados_logs_didaticos(self) -> LogsDidaticosDTO:
        """
        Compila a linha do tempo de chamadas das funções-chave de src/core/
        em um LogsDidaticosDTO pronto para a sidebar 'Logs' da GUI.
        """
        estados = self.simulador.obter_todos_estados()
        if not estados:
            return LogsDidaticosDTO(blocos=[])

        blocos: List[BlocoLogTickDTO] = []
        for est in estados:
            if not est.logs_tick_atual:
                continue
            cabecalho = (
                est.titulo_log_atual
                if est.titulo_log_atual
                else f"Tick {max(0, est.tick_atual - 1)} → {est.tick_atual}"
            )
            chamadas = [
                ChamadaFuncaoLogDTO(
                    funcao=reg.funcao,
                    detalhe=reg.detalhe,
                    categoria=reg.categoria,
                )
                for reg in est.logs_tick_atual
            ]
            blocos.append(BlocoLogTickDTO(cabecalho_tick=cabecalho, chamadas=chamadas))

        return LogsDidaticosDTO(blocos=blocos)
