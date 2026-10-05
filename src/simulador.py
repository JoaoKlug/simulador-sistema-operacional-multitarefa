import copy
import os
from typing import List, Tuple
from core.sistema_operacional import SistemaOperacional
from core.tarefas import TCB

class GerenciadorHistorico:
    """Guarda fotos (Snapshots) do Sistema Operacional inteiro para o Time Travel."""
    def __init__(self):
        self.pilha_passado: List[SistemaOperacional] = []
        self.pilha_futuro: List[SistemaOperacional] = []

    def salvar_passado(self, so: SistemaOperacional):
        self.pilha_passado.append(copy.deepcopy(so))
        self.pilha_futuro.clear()

class Simulador:
    """
    Controlador Principal. Faz a ponte entre a GUI e o SO.
    Orquestra o tempo, a máquina do tempo e a inicialização.
    """
    def __init__(self):
        self.so_atual: SistemaOperacional = None
        self.historico = GerenciadorHistorico()

    def _fazer_parse_arquivo(self, caminho_arquivo: str) -> Tuple[str, int, int, List[dict]]:
        """Lê o TXT, valida e quebra os dados crus para configuração."""
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
            raise ValueError("Arquivo deve ter pelo menos 2 linhas.")
            
        config_global = linhas_limpas[0].split(';')
        if len(config_global) < 3:
            raise ValueError("Linha 1 mal formatada. Esperado: algoritmo;quantum;qtde_cpus")
            
        algoritmo = config_global[0].strip()
        if algoritmo not in ("rm", "edf"):
            raise ValueError(f"Algoritmo '{algoritmo}' não suportado. Use 'rm' ou 'edf'.")
            
        quantum = int(config_global[1])
        qtde_cpus = int(config_global[2])
        
        dados_tarefas = []
        for i, linha_tarefa in enumerate(linhas_limpas[1:]):
            dados = linha_tarefa.split(';')
            if len(dados) < 6:
                continue
                
            periodo = int(dados[4])
            if periodo <= 0:
                continue
                
            lista_eventos = dados[6] if len(dados) >= 7 else ""
                
            dict_t = {
                "id_tarefa": int(dados[0]),
                "cor_hex": dados[1].upper(),
                "instante_ingresso": int(dados[2]),
                "duracao_original": int(dados[3]),
                "periodo": periodo,
                "prazo_relativo": int(dados[5]),
                "lista_eventos": lista_eventos
            }
            dados_tarefas.append(dict_t)
            
        return algoritmo, quantum, qtde_cpus, dados_tarefas

    def carregar_arquivo(self, caminho: str):
        algo, quantum, qtde_cpus, dados_tarefas = self._fazer_parse_arquivo(caminho)
        
        tarefas_obj = []
        for d in dados_tarefas:
            t = TCB(d["id_tarefa"], d["cor_hex"], d["instante_ingresso"], 
                    d["duracao_original"], d["periodo"], d["prazo_relativo"], d["lista_eventos"])
            tarefas_obj.append(t)
            
        self.so_atual = SistemaOperacional(qtde_cpus, algo, quantum, tarefas_obj)
        self.historico.pilha_passado.clear()
        self.historico.pilha_futuro.clear()

    def avancar_tick(self):
        if not self.so_atual: return

        if self.historico.pilha_futuro:
            self.historico.pilha_passado.append(self.so_atual)
            self.so_atual = self.historico.pilha_futuro.pop()
        else:
            self.historico.salvar_passado(self.so_atual)
            self.so_atual = copy.deepcopy(self.so_atual)
            self.so_atual.avancar_tempo()

    def retroceder_tick(self) -> bool:
        if self.historico.pilha_passado:
            self.historico.pilha_futuro.append(self.so_atual)
            self.so_atual = self.historico.pilha_passado.pop()
            return True
        return False

    def executar_completo(self, max_ticks: int = 5000) -> bool:
        if not self.so_atual: return True
        count = 0
        while not self.so_atual.finalizado():
            count += 1
            if count > max_ticks:
                return False
            self.historico.salvar_passado(self.so_atual)
            self.so_atual = copy.deepcopy(self.so_atual)
            self.so_atual.avancar_tempo()
        return True

    # ---------------------------------------------------------
    # MÉTODOS DE PRESENTER (Model-View-Presenter)
    # Traduzem regras do Domínio para atributos estritos de Interface
    # ---------------------------------------------------------
    def obter_cor_cartao_tcb(self, tarefa: TCB) -> str:
        """Regra de UI: O cartão da tarefa só acende se ela possuir a CPU."""
        if tarefa.estado.name == "EXECUTANDO":
            return f"#{tarefa.cor_hex}"
        return "transparent"

    def obter_titulo_cartao_tcb(self, tarefa: TCB) -> str:
        """Regra de UI: Monta o título do cartão exibindo a CPU apenas se estiver rodando."""
        if tarefa.estado.name == "EXECUTANDO" and tarefa.id_cpu_alocada is not None:
            return f"Tarefa {tarefa.id_tarefa} (CPU {tarefa.id_cpu_alocada})"
        return f"Tarefa {tarefa.id_tarefa}"

    def obter_estilo_segmento_gantt(self, estado_nome: str, cor_hex: str, sofreu_atraso: bool, cpu: int, para_exportacao: bool = False) -> dict:
        """Regra de UI: Determina cores, bordas e textos do gráfico de Gantt."""
        if estado_nome in ("NOVA", "FINALIZADA"):
            return None
            
        outline_color = "red" if sofreu_atraso else "black"
        width = 2 if sofreu_atraso else 1
        fill_color = None
        
        if estado_nome == "EXECUTANDO":
            fill_color = f"#{cor_hex}"
        elif estado_nome == "SUSPENSA":
            fill_color = "black"
        elif estado_nome == "PRONTA":
            fill_color = None if para_exportacao else "white"
            
        texto_interno = f"C{cpu}" if estado_nome == "EXECUTANDO" and cpu is not None else ""
        cor_texto = "white" if fill_color == "black" else "black"
            
        return {
            "fill": fill_color, 
            "outline": outline_color, 
            "width": width,
            "text": texto_interno,
            "text_color": cor_texto
        }
