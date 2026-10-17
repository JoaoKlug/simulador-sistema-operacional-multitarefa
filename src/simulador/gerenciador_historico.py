import copy
from typing import List
from core.sistema_operacional import SistemaOperacional


class GerenciadorHistorico:
    """
    Gerenciador de Histórico de Simulação (Padrão Memento / Time-Travel).
    Armazena fotografias completas (snapshots) do Sistema Operacional na pilha do passado.
    Ao retroceder, o estado atual (incluindo qualquer mudança manual feita nele) é descartado
    definitivamente, garantindo que ao avançar novamente a mudança desfeita não persista.
    """
    def __init__(self) -> None:
        self.pilha_passado: List[SistemaOperacional] = []

    def salvar_passado(self, so: SistemaOperacional) -> None:
        """Salva uma cópia profunda do estado atual do SO na pilha do passado."""
        self.pilha_passado.append(copy.deepcopy(so))

    def pode_retroceder(self) -> bool:
        """Indica se há estados passados gravados para retroceder."""
        return len(self.pilha_passado) > 0

    def retroceder(self, so_atual: SistemaOperacional) -> SistemaOperacional:
        """Descarta definitivamente o estado atual e recupera o último estado do passado."""
        if not self.pode_retroceder():
            return so_atual
        return self.pilha_passado.pop()

    def limpar(self) -> None:
        """Limpa todo o histórico de execução."""
        self.pilha_passado.clear()
