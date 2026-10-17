from enum import Enum


class EstadoTarefa(Enum):
    """
    Representa os estados possíveis no ciclo de vida de uma tarefa periódica
    conforme o Capítulo 4 (Seção 4.4) do livro de Carlos Maziero, acrescido do
    estado explícito AGUARDANDO entre ativações periódicas.
    """
    NOVA = "NOVA"
    PRONTA = "PRONTA"
    EXECUTANDO = "EXECUTANDO"
    SUSPENSA = "SUSPENSA"
    AGUARDANDO = "AGUARDANDO"
    FINALIZADA = "FINALIZADA"
