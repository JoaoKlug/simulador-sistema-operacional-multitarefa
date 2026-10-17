import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from core.kernel.tcb import TCB, ParametrosTarefa


@dataclass(frozen=True)
class ConfiguracaoSimulacao:
    """Estrutura imutável resultante da leitura e validação do arquivo de configuração."""
    algoritmo: str
    quantum: int
    qtde_cpus: int
    tcbs: List[TCB]
    avisos: List[str] = field(default_factory=list)


class LeitorConfiguracao:
    """
    Parser e validador do arquivo de configuração em formato texto simples (.txt).
    Implementa todas as regras da Seção 3.3 e 4.4 de requisitos_funcionais.pdf:
    - Case-insensitive para todas as strings.
    - Caractere ';' opcional ao final de qualquer linha.
    - Espaços e linhas em branco ignorados.
    - Rejeição explícita de período < 0 e alerta claro para tarefas aperiódicas (período == 0).
    """
    PADRAO_COR_HEX = re.compile(r"^[0-9A-Fa-f]{6}$")

    @classmethod
    def ler_arquivo(cls, caminho_arquivo: str) -> ConfiguracaoSimulacao:
        """Lê, valida e converte um arquivo .txt em uma instância de ConfiguracaoSimulacao."""
        linhas_uteis = cls._ler_linhas_uteis(caminho_arquivo)
        num_linha_1, texto_linha_1 = linhas_uteis[0]
        algoritmo, quantum, qtde_cpus = cls._interpretar_parametros_sistema(num_linha_1, texto_linha_1)

        tcbs: List[TCB] = []
        ids_vistos: set[int] = set()
        avisos: List[str] = []

        for num_linha, texto_linha in linhas_uteis[1:]:
            tcb = cls._interpretar_linha_tarefa(num_linha, texto_linha, ids_vistos, avisos)
            if tcb is not None:
                tcbs.append(tcb)

        if not tcbs:
            raise ValueError(
                "Nenhuma tarefa periódica válida restou após o carregamento do arquivo de configuração."
            )

        return ConfiguracaoSimulacao(
            algoritmo=algoritmo,
            quantum=quantum,
            qtde_cpus=qtde_cpus,
            tcbs=tcbs,
            avisos=avisos,
        )

    @classmethod
    def _ler_linhas_uteis(cls, caminho_arquivo: str) -> List[Tuple[int, str]]:
        """Lê o arquivo texto e retorna as linhas não vazias higienizadas com sua numeração."""
        if not os.path.exists(caminho_arquivo):
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {caminho_arquivo}")

        try:
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                linhas_brutas = f.readlines()
        except Exception as e:
            raise ValueError(f"Não foi possível ler o arquivo de configuração: {e}")

        linhas_uteis: List[Tuple[int, str]] = []
        for idx, linha in enumerate(linhas_brutas, start=1):
            limpa = linha.strip().replace(" ", "").replace("\t", "").rstrip(";")
            if limpa:
                linhas_uteis.append((idx, limpa))

        if len(linhas_uteis) < 2:
            raise ValueError(
                "Erro no arquivo de configuração: o arquivo deve possuir pelo menos 2 linhas válidas "
                "(1ª linha com parâmetros do sistema e ao menos 1 linha de tarefa)."
            )
        return linhas_uteis

    @classmethod
    def _interpretar_parametros_sistema(cls, num_linha: int, texto_linha: str) -> Tuple[str, int, int]:
        """Valida e extrai (algoritmo, quantum, qtde_cpus) da primeira linha útil do arquivo."""
        campos = texto_linha.split(";")
        if len(campos) != 3:
            raise ValueError(
                f"Erro na linha {num_linha} ('{texto_linha}'): formato esperado é "
                "'algoritmo_escalonamento;quantum;qtde_cpus'."
            )

        algoritmo = campos[0].lower()
        if algoritmo not in ("rm", "edf"):
            raise ValueError(
                f"Erro na linha {num_linha}: algoritmo '{campos[0]}' não suportado. Utilize 'RM' ou 'EDF'."
            )

        try:
            quantum = int(campos[1])
            qtde_cpus = int(campos[2])
        except ValueError:
            raise ValueError(
                f"Erro na linha {num_linha}: quantum e quantidade de CPUs devem ser números inteiros."
            )

        if quantum < 0:
            raise ValueError(f"Erro na linha {num_linha}: o quantum ({quantum}) não pode ser negativo.")
        if qtde_cpus < 1:
            raise ValueError(
                f"Erro na linha {num_linha}: a quantidade de processadores ({qtde_cpus}) deve ser no mínimo 1."
            )
        return algoritmo, quantum, qtde_cpus

    @classmethod
    def _interpretar_linha_tarefa(
        cls,
        num_linha: int,
        texto_linha: str,
        ids_vistos: set[int],
        avisos: List[str],
    ) -> Optional[TCB]:
        """Interpreta e valida uma linha de tarefa, retornando seu TCB ou None se for aperiódica."""
        campos = texto_linha.split(";")
        if len(campos) < 6:
            raise ValueError(
                f"Erro na linha {num_linha} ('{texto_linha}'): esperado no mínimo 6 campos "
                "'id;cor;ingresso;duracao;periodo;prazo[;lista_eventos]'."
            )

        try:
            params = ParametrosTarefa(
                id_tarefa=int(campos[0]),
                cor_hex=campos[1].upper().lstrip("#"),
                instante_ingresso=int(campos[2]),
                duracao=int(campos[3]),
                periodo=int(campos[4]),
                prazo_relativo=int(campos[5]),
            )
        except ValueError:
            raise ValueError(
                f"Erro na linha {num_linha} ('{texto_linha}'): os campos id, ingresso, duracao, "
                "periodo e prazo devem ser números inteiros válidos."
            )

        cls._validar_campos_tarefa(num_linha, params, ids_vistos)

        # Requisito 4.4: tarefas aperiódicas (período == 0) são ignoradas no Projeto A e reportadas ao usuário
        if params.periodo == 0:
            avisos.append(
                f"Linha {num_linha}: Tarefa ID {params.id_tarefa} possui período = 0 (aperiódica) e foi ignorada "
                "conforme especificação do Projeto A (Requisito 4.4)."
            )
            return None

        ids_vistos.add(params.id_tarefa)
        lista_eventos = ";".join(campos[6:]) if len(campos) >= 7 else ""
        return TCB(
            id_tarefa=params.id_tarefa,
            cor_hex=params.cor_hex,
            instante_ingresso=params.instante_ingresso,
            duracao=params.duracao,
            periodo=params.periodo,
            prazo_relativo=params.prazo_relativo,
            lista_eventos=lista_eventos,
        )

    @classmethod
    def _validar_campos_tarefa(
        cls,
        num_linha: int,
        params: ParametrosTarefa,
        ids_vistos: set[int],
    ) -> None:
        """Valida restrições de unicidade, cor e limites temporais de uma linha de tarefa."""
        if params.id_tarefa in ids_vistos:
            raise ValueError(f"Erro na linha {num_linha}: o ID de tarefa {params.id_tarefa} está duplicado no arquivo.")
        if not cls.PADRAO_COR_HEX.match(params.cor_hex):
            raise ValueError(
                f"Erro na linha {num_linha}: a cor '{params.cor_hex}' da tarefa {params.id_tarefa} deve estar em "
                "formato RGB Hexadecimal de 6 dígitos (ex: F0E0D0)."
            )
        if params.instante_ingresso < 0:
            raise ValueError(
                f"Erro na linha {num_linha}: o instante de ingresso ({params.instante_ingresso}) da tarefa "
                f"{params.id_tarefa} não pode ser negativo."
            )
        if params.duracao <= 0:
            raise ValueError(
                f"Erro na linha {num_linha}: a duração ({params.duracao}) da tarefa {params.id_tarefa} "
                "deve ser maior que zero."
            )
        if params.periodo < 0:
            raise ValueError(
                f"Erro na linha {num_linha}: o período ({params.periodo}) da tarefa {params.id_tarefa} é menor que "
                "zero, o que indica erro no arquivo de configuração (Requisito 3.3)."
            )
        if params.periodo > 0 and params.prazo_relativo <= 0:
            raise ValueError(
                f"Erro na linha {num_linha}: o prazo/deadline ({params.prazo_relativo}) da tarefa "
                f"{params.id_tarefa} deve ser maior que zero."
            )
