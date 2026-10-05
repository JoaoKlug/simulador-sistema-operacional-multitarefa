from enum import Enum
from typing import Optional

class EstadoTarefa(Enum):
    NOVA = "NOVA"
    PRONTA = "PRONTA"
    EXECUTANDO = "EXECUTANDO"
    SUSPENSA = "SUSPENSA"
    FINALIZADA = "FINALIZADA"

class TCB:
    """
    Bloco de Controle de Tarefa (Task Control Block).
    Representa uma tarefa (processo/thread) dentro do Sistema Operacional.
    """
    def __init__(self, id_tarefa: int, cor_hex: str, instante_ingresso: int, 
                 duracao_original: int, periodo: int, prazo_relativo: int, lista_eventos: str):
        # Propriedades imutáveis / Configuração inicial
        self.id_tarefa = id_tarefa
        self.cor_hex = cor_hex
        self.instante_ingresso = instante_ingresso
        self.duracao_original = duracao_original
        self.periodo = periodo
        self.prazo_relativo = prazo_relativo
        self.lista_eventos = lista_eventos
        
        # Estado dinâmico (Mutável ao longo do tempo)
        self.estado = EstadoTarefa.NOVA
        self.tempo_ja_executado = 0
        self.prazo_absoluto_atual = 0
        self.id_cpu_alocada: Optional[int] = None
        self.execucoes_completadas = 0
        self.sofreu_atraso = False

    # Fim da classe TCB
