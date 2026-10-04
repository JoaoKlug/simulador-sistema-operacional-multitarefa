from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum

class EstadoTarefa(Enum):
    NOVA = "NOVA"
    PRONTA = "PRONTA"
    EXECUTANDO = "EXECUTANDO"
    SUSPENSA = "SUSPENSA"
    FINALIZADA = "FINALIZADA"

@dataclass
class BlocoControleTarefa:
    """
    Representa o Task Control Block (TCB). 
    Armazena configurações originais e mutáveis em tempo real.
    """
    id_tarefa: int
    cor_hex: str           
    instante_ingresso: int
    duracao_original: int  
    periodo: int
    prazo_relativo: int    
    lista_eventos: str
    
    # Propriedades Mutáveis
    estado: EstadoTarefa = EstadoTarefa.NOVA
    tempo_ja_executado: int = 0
    prazo_absoluto_atual: int = 0
    id_cpu_alocada: Optional[int] = None
    execucoes_completadas: int = 0  # Limite fixo de 10 execuções para o Projeto A
    sofreu_atraso: bool = False

@dataclass
class Processador:
    id_cpu: int
    tarefa_atual: Optional[BlocoControleTarefa] = None
    tempo_desligado: int = 0

@dataclass
class EstadoSistema:
    """Fotografia de um momento no tempo (Tick) para o histórico."""
    tick_atual: int = 0
    quantum_global: int = 0
    nome_algoritmo: str = ""
    qtde_cpus: int = 1
    cpus: List[Processador] = field(default_factory=list)
    tarefas: List[BlocoControleTarefa] = field(default_factory=list)
    eventos_sorteio: List[Tuple[int, int]] = field(default_factory=list) # (tick, id_tarefa)
