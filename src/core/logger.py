import os
import sys


def obter_caminho_log() -> str:
    """Retorna o caminho absoluto do arquivo log_so.txt no diretório base da aplicação."""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_dir, "log_so.txt")


def limpar_log() -> None:
    """Reinicia o arquivo de log no início de uma nova simulação."""
    caminho = obter_caminho_log()
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("")


def log_secao(titulo: str) -> None:
    """Escreve um cabeçalho divisor de seção/tick diretamente no arquivo de log."""
    caminho = obter_caminho_log()
    with open(caminho, "a", encoding="utf-8") as f:
        f.write(f"\n{'=' * 85}\n{titulo}\n{'=' * 85}\n")


def log_core(classe_funcao: str, mensagem: str) -> None:
    """Registra uma linha de log tradicional diretamente no arquivo .txt (estilo console.log)."""
    caminho = obter_caminho_log()
    with open(caminho, "a", encoding="utf-8") as f:
        f.write(f"[{classe_funcao}] {mensagem}\n")

