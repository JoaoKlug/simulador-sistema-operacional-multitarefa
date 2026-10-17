from typing import List, Tuple, Dict
from core.kernel.tcb import TCB
from core.logger import log_core


class Escalonador:
    """
    Interface base para as políticas de escalonamento preemptivo do Kernel (Maziero, Cap. 6).
    Define 'quem' da fila global de tarefas prontas deve receber o processador,
    aplicando os 5 critérios obrigatórios de desempate (Requisito 4.3).
    """
    def eleger(self, fila_prontos: List[TCB], tick_atual: int, tarefas_nas_cpus: List[int]) -> List[TCB]:
        """Ordena e retorna a lista de tarefas prontas conforme a política e regras de desempate."""
        for t in fila_prontos:
            t.sorteada_no_tick = False

        # Contabiliza quantas tarefas empatam na prioridade principal + 4 primeiros critérios
        contagem_empates: Dict[Tuple[int, int, int, int, int], int] = {}
        for t in fila_prontos:
            chave4 = self._chave_quatro_criterios(t, tarefas_nas_cpus)
            contagem_empates[chave4] = contagem_empates.get(chave4, 0) + 1

        # Marca tarefas que precisaram do 5º critério (sorteio) para desempatar
        for t in fila_prontos:
            chave4 = self._chave_quatro_criterios(t, tarefas_nas_cpus)
            if contagem_empates[chave4] > 1:
                t.sorteada_no_tick = True

        fila_ordenada = sorted(
            fila_prontos,
            key=lambda t: (
                self._prioridade_principal(t),
                self.regra_desempate(t, tick_atual, tarefas_nas_cpus),
            ),
        )
        self._registrar_decisao_eleicao(fila_ordenada, tarefas_nas_cpus)
        return fila_ordenada

    def _prioridade_principal(self, t: TCB) -> int:
        """Retorna a métrica de prioridade principal (menor valor = maior prioridade)."""
        raise NotImplementedError("Subclasses devem implementar _prioridade_principal.")

    def _rotulo_metrica(self, t: TCB) -> str:
        """Formata a métrica principal da tarefa para exibição enxuta no log."""
        raise NotImplementedError("Subclasses devem implementar _rotulo_metrica.")

    def _registrar_decisao_eleicao(self, fila_ordenada: List[TCB], tarefas_nas_cpus: List[int]) -> None:
        """Escreve no arquivo de log a decisão tomada pelo método eleger() e seus critérios."""
        origem = f"{self.__class__.__name__}.eleger"
        if not fila_ordenada:
            log_core(origem, "Fila de prontos vazia -> nenhuma tarefa apta a disputar a CPU.")
            return

        itens_ord = ", ".join(self._rotulo_metrica(t) for t in fila_ordenada)
        if len(fila_ordenada) == 1:
            log_core(origem, f"Única tarefa apta eleita: [{itens_ord}].")
            return

        desempates: List[str] = []
        for i in range(len(fila_ordenada) - 1):
            motivo = self._descrever_desempate(fila_ordenada[i], fila_ordenada[i + 1], tarefas_nas_cpus)
            if motivo:
                desempates.append(motivo)

        complemento = f" | {' ; '.join(desempates)}" if desempates else ""
        log_core(origem, f"Fila de prioridade ordenada: [{itens_ord}]{complemento}.")

    def _descrever_desempate(self, t1: TCB, t2: TCB, tarefas_nas_cpus: List[int]) -> str:
        """Identifica qual critério desempatou duas tarefas adjacentes caso empatem na prioridade principal."""
        if self._prioridade_principal(t1) != self._prioridade_principal(t2):
            return ""
        par = f"(T{t1.id_tarefa} vs T{t2.id_tarefa})"
        if (t1.id_tarefa in tarefas_nas_cpus) != (t2.id_tarefa in tarefas_nas_cpus):
            return f"Desempate 1º {par}: T{t1.id_tarefa} já estava executando na CPU"
        if t1.prazo_absoluto_atual != t2.prazo_absoluto_atual:
            return f"Desempate 2º {par}: menor DeadLine Abs. ({t1.prazo_absoluto_atual} < {t2.prazo_absoluto_atual})"
        if t1.instante_ingresso != t2.instante_ingresso:
            return f"Desempate 3º {par}: menor Ingresso ({t1.instante_ingresso} < {t2.instante_ingresso})"
        if t1.duracao != t2.duracao:
            return f"Desempate 4º {par}: menor Duração ({t1.duracao} < {t2.duracao})"
        return f"Desempate 5º {par}: Sorteio determinístico venceu para T{t1.id_tarefa}"

    def _chave_quatro_criterios(self, t: TCB, tarefas_nas_cpus: List[int]) -> Tuple[int, int, int, int, int]:
        """Retorna a tupla com a prioridade principal e os 4 primeiros critérios determinísticos."""
        executava = 0 if t.id_tarefa in tarefas_nas_cpus else 1
        return (
            self._prioridade_principal(t),
            executava,
            t.prazo_absoluto_atual,
            t.instante_ingresso,
            t.duracao,
        )

    def regra_desempate(self, t: TCB, tick_atual: int, tarefas_nas_cpus: List[int]) -> Tuple[int, int, int, int, int]:
        """
        Critérios obrigatórios de desempate em ordem estrita (Requisito 4.3):
        1. Tarefa executando imediatamente antes (evita troca de contexto desnecessária)
        2. Menor prazo absoluto (deadline)
        3. Menor instante de ingresso original
        4. Menor duração de computação
        5. Sorteio determinístico reproduzível (permite Time-Travel consistente)
        """
        executava = 0 if t.id_tarefa in tarefas_nas_cpus else 1
        sorteio = ((t.id_tarefa * 1103515245 + (tick_atual + 1) * 12345 + 6789) & 0x7FFFFFFF)
        return (executava, t.prazo_absoluto_atual, t.instante_ingresso, t.duracao, sorteio)


class EscalonadorRM(Escalonador):
    """
    Política Rate Monotonic (RM — Requisito 4.1).
    Prioridade fixa/estática baseada na frequência: menor período = maior prioridade.
    """
    def _prioridade_principal(self, t: TCB) -> int:
        return t.periodo

    def _rotulo_metrica(self, t: TCB) -> str:
        return f"T{t.id_tarefa}(P={t.periodo})"


class EscalonadorEDF(Escalonador):
    """
    Política Earliest Deadline First (EDF — Requisito 4.1).
    Prioridade dinâmica baseada na urgência: menor prazo absoluto atual = maior prioridade.
    """
    def _prioridade_principal(self, t: TCB) -> int:
        return t.prazo_absoluto_atual

    def _rotulo_metrica(self, t: TCB) -> str:
        return f"T{t.id_tarefa}(DL_Abs={t.prazo_absoluto_atual})"


def criar_escalonador(algoritmo: str) -> Escalonador:
    """Fábrica desacoplada para instanciação de políticas de escalonamento (Requisito 4.2)."""
    algo_norm = algoritmo.strip().lower()
    if algo_norm == "rm":
        return EscalonadorRM()
    if algo_norm == "edf":
        return EscalonadorEDF()
    raise ValueError(f"Algoritmo de escalonamento '{algoritmo}' não suportado. Utilize 'RM' ou 'EDF'.")
