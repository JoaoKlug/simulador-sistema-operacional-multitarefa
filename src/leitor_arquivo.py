import os
from typing import List, Tuple
from modelos import BlocoControleTarefa, EstadoSistema, Processador

def ler_estado_inicial(caminho_arquivo: str) -> EstadoSistema:
    """
    Lê o arquivo .txt, ignorando case-sensitive e espaços, e retorna o estado
    inicial do sistema (EstadoSistema) já formatado.
    """
    if not os.path.exists(caminho_arquivo):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_arquivo}")

    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        linhas = f.readlines()
        
    linhas_limpas = []
    for linha in linhas:
        l_limpa = linha.strip().replace(" ", "")
        if l_limpa.endswith(";"):
            l_limpa = l_limpa[:-1]
        if l_limpa:
            linhas_limpas.append(l_limpa.lower())
            
    if len(linhas_limpas) < 2:
        raise ValueError("Arquivo de configuração deve ter pelo menos 2 linhas.")
        
    config_global = linhas_limpas[0].split(';')
    if len(config_global) < 3:
        raise ValueError("Linha 1 mal formatada. Esperado: algoritmo;quantum;qtde_cpus")
        
    algoritmo = config_global[0].strip()
    if algoritmo not in ("rm", "edf"):
        raise ValueError(f"Algoritmo '{algoritmo}' não suportado. Use 'rm' ou 'edf'.")
        
    quantum = int(config_global[1])
    qtde_cpus = int(config_global[2])
    
    tarefas = []
    for linha_tarefa in linhas_limpas[1:]:
        dados = linha_tarefa.split(';')
        if len(dados) < 7:
            continue # Pula linhas mal formatadas ou tenta extrair o que dá
            
        periodo = int(dados[4])
        if periodo < 0:
            raise ValueError(f"Erro no arquivo: Tarefa {dados[0]} tem período negativo.")
        if periodo == 0:
            print(f"Aviso: Tarefa {dados[0]} é aperiódica e será ignorada nesta versão do simulador.")
            continue
            
        t = BlocoControleTarefa(
            id_tarefa=int(dados[0]),
            cor_hex=dados[1].upper(),
            instante_ingresso=int(dados[2]),
            duracao_original=int(dados[3]),
            periodo=periodo,
            prazo_relativo=int(dados[5]),
            lista_eventos=dados[6]
        )
        tarefas.append(t)
        
    return EstadoSistema(
        tick_atual=0,
        quantum_global=quantum,
        nome_algoritmo=algoritmo,
        qtde_cpus=qtde_cpus,
        cpus=[Processador(id_cpu=i+1) for i in range(qtde_cpus)],
        tarefas=tarefas
    )
