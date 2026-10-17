from dataclasses import dataclass
from typing import Optional
from core.processos.estado_tarefa import EstadoTarefa


@dataclass(frozen=True)
class EventoTarefaTick:
    """
    Representa um evento relevante ocorrido em um instante exato (tick) da simulação
    para exibição gráfica no Gráfico de Gantt (Requisitos 2.2, 3.3 e 4.3).
    Tipos suportados: 'INGRESSO', 'TERMINO', 'DEADLINE', 'SORTEIO'.
    """
    id_tarefa: int
    tick: int
    tipo: str


@dataclass(frozen=True)
class ParametrosTarefa:
    """Agrupa os dados de criação ou edição de uma tarefa, evitando listas longas de parâmetros."""
    id_tarefa: int
    cor_hex: str
    instante_ingresso: int
    duracao: int
    periodo: int
    prazo_relativo: int
    novo_estado: str = "NOVA"
    tempo_ja_executado: int = 0


@dataclass
class TCB:
    """
    Bloco de Controle de Tarefa (Task Control Block — Requisito 1.3 e Maziero Cap. 5, Seção 5.1).
    Estrutura de dados única que armazena todas as informações estáticas e dinâmicas
    de uma tarefa antes, durante e depois da simulação.
    """
    id_tarefa: int
    cor_hex: str
    instante_ingresso: int
    duracao: int
    periodo: int
    prazo_relativo: int
    lista_eventos: str = ""

    # Estado dinâmico mantido pelo Kernel ao longo da simulação
    estado: EstadoTarefa = EstadoTarefa.NOVA
    tempo_ja_executado: int = 0
    tick_inicio_ciclo_atual: int = 0
    prazo_absoluto_atual: int = 0
    id_cpu_alocada: Optional[int] = None
    execucoes_completadas: int = 0
    sofreu_atraso: bool = False
    sorteada_no_tick: bool = False

    # Registro do estado efetivamente executado durante o último intervalo [tick - 1, tick)
    estado_ultimo_intervalo: Optional[EstadoTarefa] = None
    cpu_ultimo_intervalo: Optional[int] = None
    atraso_ultimo_intervalo: bool = False

    def __post_init__(self) -> None:
        if self.tick_inicio_ciclo_atual == 0 and self.instante_ingresso > 0:
            self.tick_inicio_ciclo_atual = self.instante_ingresso

    @property
    def duracao_original(self) -> int:
        """Compatibilidade de leitura para a duração de computação configurada."""
        return self.duracao

    def obter_proximo_inicio(self) -> int:
        """
        Retorna o tick de início do próximo ciclo periódico tomando como referência
        o início real do ciclo atual (tick_inicio_ciclo_atual + periodo).
        """
        if self.execucoes_completadas == 0 and self.estado == EstadoTarefa.NOVA:
            return self.instante_ingresso
        return self.tick_inicio_ciclo_atual + self.periodo
