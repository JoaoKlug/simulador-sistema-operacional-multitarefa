from typing import List
from modelos import EstadoSistema
import copy

class GerenciadorHistorico:
    """
    Mantém o histórico de estados do sistema para permitir "Time Travel".
    """
    def __init__(self):
        self.pilha_passado: List[EstadoSistema] = []
        self.pilha_futuro: List[EstadoSistema] = []
        self.estado_atual: EstadoSistema = None

    def iniciar(self, estado_inicial: EstadoSistema):
        self.estado_atual = copy.deepcopy(estado_inicial)
        self.pilha_passado.clear()
        self.pilha_futuro.clear()

    def avancar(self, estado_novo: EstadoSistema):
        if self.estado_atual:
            self.pilha_passado.append(self.estado_atual)
        self.estado_atual = copy.deepcopy(estado_novo)
        # Se avançou calculando novo estado, invalida o futuro
        self.pilha_futuro.clear()

    def avancar_do_historico(self):
        """Avança pegando do futuro (Time Travel pra frente sem recalcular)."""
        if self.pilha_futuro:
            self.pilha_passado.append(self.estado_atual)
            self.estado_atual = self.pilha_futuro.pop()
            return True
        return False

    def retroceder(self):
        if self.pilha_passado:
            self.pilha_futuro.append(self.estado_atual)
            self.estado_atual = self.pilha_passado.pop()
            return True
        return False

    def limpar_futuro(self):
        """Chamado quando o usuário modifica o estado no meio de um time-travel"""
        self.pilha_futuro.clear()
