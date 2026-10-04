import random
from typing import Protocol, List, Callable
from modelos import BlocoControleTarefa

class ProtocoloEscalonador(Protocol):
    def __call__(self, fila_prontos: List[BlocoControleTarefa], tick_atual: int, tarefas_nas_cpus: List[int]) -> List[BlocoControleTarefa]:
        ...

def regra_desempate(t: BlocoControleTarefa, tick_atual: int, tarefas_nas_cpus: List[int]) -> tuple:
    """
    Retorna uma tupla que será usada para ordenar (sort).
    O Python ordena do menor para o maior.
    A prioridade primária do algoritmo (período ou prazo) deve ser definida antes de chamar essa regra,
    então essa função atende apenas os critérios de desempate (Regras 1 a 5).
    """
    executava = 0 if t.id_tarefa in tarefas_nas_cpus else 1
    
    # Sorteio determinístico usando o hash da tarefa e o tempo (garante o mesmo resultado ao voltar no tempo)
    sorteio = hash((t.id_tarefa, tick_atual))
    
    return (
        executava,
        t.prazo_absoluto_atual,
        t.instante_ingresso,
        t.duracao_original,
        sorteio
    )

def escalonador_rm(fila_prontos: List[BlocoControleTarefa], tick_atual: int, tarefas_nas_cpus: List[int]) -> List[BlocoControleTarefa]:
    """Taxa Monotônica: Maior prioridade para o menor período."""
    return sorted(fila_prontos, key=lambda t: (t.periodo, regra_desempate(t, tick_atual, tarefas_nas_cpus)))

def escalonador_edf(fila_prontos: List[BlocoControleTarefa], tick_atual: int, tarefas_nas_cpus: List[int]) -> List[BlocoControleTarefa]:
    """Earliest Deadline First: Maior prioridade para o menor deadline absoluto."""
    return sorted(fila_prontos, key=lambda t: (t.prazo_absoluto_atual, regra_desempate(t, tick_atual, tarefas_nas_cpus)))

def obter_escalonador(nome: str) -> ProtocoloEscalonador:
    if nome.lower() == 'rm':
        return escalonador_rm
    return escalonador_edf
