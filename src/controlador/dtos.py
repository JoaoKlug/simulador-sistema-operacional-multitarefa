from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class DadosEdicaoTarefaDTO:
    """DTO imutável de entrada agrupando os atributos para criação ou edição de uma tarefa."""
    id_tarefa: int
    cor_hex: str
    instante_ingresso: int
    duracao: int
    periodo: int
    prazo_relativo: int
    novo_estado: str = "NOVA"
    tempo_ja_executado: int = 0


@dataclass(frozen=True)
class DadosCabecalhoDTO:
    """DTO imutável para atualização da barra superior de configurações do sistema e estado dos botões."""
    texto_info: str
    texto_linha_1: str
    texto_linha_2: str
    pode_avancar: bool
    pode_retroceder: bool
    pode_executar_completo: bool
    simulacao_finalizada: bool
    algoritmo_atual: str
    quantum_atual: int
    qtde_cpus_atual: int
    proximo_id_sugerido: int


@dataclass(frozen=True)
class CardTCBDTO:
    """DTO imutável representando um cartão de TCB na barra horizontal inferior da GUI."""
    id_tarefa: int
    titulo: str
    cor_indicador: str
    nome_estado: str
    texto_progresso: str
    texto_periodo_prazo: str
    texto_prazo_absoluto: str
    texto_execucoes: str
    esta_atrasada: bool
    # Campos brutos para autopreenchimento do modal de edição manual (Requisito 3.2 e 3.4)
    cor_hex: str
    instante_ingresso: int
    duracao: int
    periodo: int
    prazo_relativo: int
    tempo_ja_executado: int
    linhas_informacao: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class SegmentoGanttDTO:
    """DTO imutável para um bloco retangular contínuo no Gráfico de Gantt."""
    id_tarefa: int
    tick_inicio: int
    tick_fim: int
    estado: str
    cor_preenchimento: Optional[str]
    cor_borda: str
    largura_borda: int
    texto: str
    cor_texto: str
    pontilhado: bool = False


@dataclass(frozen=True)
class MarcadorEventoGanttDTO:
    """
    DTO imutável para um ícone/seta de evento exato no Gráfico de Gantt.
    Tipos: 'INGRESSO', 'TERMINO', 'DEADLINE', 'SORTEIO'.
    """
    id_tarefa: int
    tick: int
    tipo: str


@dataclass(frozen=True)
class DadosGanttDTO:
    """DTO consolidado entregue ao DesenhistaGantt (100% independente do domínio)."""
    max_tick: int
    tarefas_eixo_y: List[int]
    cpus_ids: List[int] = field(default_factory=list)
    segmentos: List[SegmentoGanttDTO] = field(default_factory=list)
    eventos: List[MarcadorEventoGanttDTO] = field(default_factory=list)
    segmentos_cpus_desligadas: List[SegmentoGanttDTO] = field(default_factory=list)
    resumo_cpus_desligadas: str = ""


@dataclass(frozen=True)
class ChamadaFuncaoLogDTO:
    """DTO imutável representando uma chamada de função-chave do core e seu efeito concreto."""
    funcao: str
    detalhe: str
    categoria: str


@dataclass(frozen=True)
class BlocoLogTickDTO:
    """DTO imutável agrupando todas as chamadas de função ocorridas em um tick/evento."""
    cabecalho_tick: str
    chamadas: List[ChamadaFuncaoLogDTO] = field(default_factory=list)


@dataclass(frozen=True)
class LogsDidaticosDTO:
    """DTO consolidado para renderização do painel lateral 'Logs' (100% independente do domínio)."""
    blocos: List[BlocoLogTickDTO] = field(default_factory=list)
