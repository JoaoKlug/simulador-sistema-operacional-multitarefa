from typing import List, Optional
from core.sistema_operacional import SistemaOperacional
from core.kernel.tcb import TCB, ParametrosTarefa
from simulador.gerenciador_historico import GerenciadorHistorico
from simulador.leitor_configuracao import LeitorConfiguracao


class Simulador:
    """
    Motor Central de Simulação.
    Orquestra a inicialização do Sistema Operacional, o avanço/retrocesso temporal (Time-Travel)
    com suporte a Memento (GerenciadorHistorico) e a aplicação de modificações em tempo real.
    """
    # Valores padrão sugeridos (Requisito 3.2)
    ALGORITMO_PADRAO: str = "rm"
    QUANTUM_PADRAO: int = 0
    QTDE_CPUS_PADRAO: int = 1

    def __init__(self) -> None:
        self.so_atual: Optional[SistemaOperacional] = None
        self.historico: GerenciadorHistorico = GerenciadorHistorico()
        self.ultimos_avisos: List[str] = []

    def carregar_arquivo(self, caminho_arquivo: str) -> List[str]:
        """
        Carrega e inicializa o Sistema Operacional a partir de um arquivo .txt.
        Retorna a lista de avisos gerados (ex: tarefas aperiódicas ignoradas).
        """
        config = LeitorConfiguracao.ler_arquivo(caminho_arquivo)
        self.so_atual = SistemaOperacional(
            qtde_cpus=config.qtde_cpus,
            algoritmo=config.algoritmo,
            quantum=config.quantum,
            tarefas=config.tcbs,
        )
        self.historico.limpar()
        self.ultimos_avisos = list(config.avisos)
        return self.ultimos_avisos

    def inicializar_sistema_customizado(
        self,
        algoritmo: str = ALGORITMO_PADRAO,
        quantum: int = QUANTUM_PADRAO,
        qtde_cpus: int = QTDE_CPUS_PADRAO,
        tarefas: Optional[List[TCB]] = None,
    ) -> None:
        """
        Inicializa o sistema por padrão com 1 única tarefa com dados zerados no estado NOVA,
        ou atualiza os parâmetros globais de uma simulação existente.
        """
        if self.so_atual is None:
            lista_tcbs = tarefas if tarefas is not None else [
                TCB(
                    id_tarefa=1,
                    cor_hex="33A1FF",
                    instante_ingresso=0,
                    duracao=0,
                    periodo=0,
                    prazo_relativo=0,
                )
            ]
            self.so_atual = SistemaOperacional(
                qtde_cpus=qtde_cpus,
                algoritmo=algoritmo,
                quantum=quantum,
                tarefas=lista_tcbs,
            )
            self.historico.limpar()
        else:
            self.historico.salvar_passado(self.so_atual)
            try:
                self.so_atual.modificar_parametros_sistema(algoritmo, quantum, qtde_cpus)
            except Exception:
                self.so_atual = self.historico.pilha_passado.pop()
                raise

    def adicionar_tarefa_em_execucao(self, params: ParametrosTarefa) -> None:
        """Adiciona uma nova tarefa ao sistema preservando snapshot anterior no histórico."""
        if self.so_atual is None:
            self.inicializar_sistema_customizado(tarefas=[])

        assert self.so_atual is not None
        self.historico.salvar_passado(self.so_atual)
        try:
            self.so_atual.adicionar_tarefa(params)
        except Exception:
            self.so_atual = self.historico.pilha_passado.pop()
            raise

    def modificar_tarefa_em_execucao(self, params: ParametrosTarefa) -> None:
        """
        Modifica o estado ou características de uma tarefa em qualquer passo da simulação
        (Requisitos 1.5.2, 3.1 e 3.4), gravando o estado anterior no histórico.
        """
        if not self.so_atual:
            raise ValueError("Nenhuma simulação ativa no momento.")

        self.historico.salvar_passado(self.so_atual)
        try:
            self.so_atual.modificar_tarefa(params)
        except Exception:
            self.so_atual = self.historico.pilha_passado.pop()
            raise

    def avancar_tick(self) -> None:
        """Avança a simulação em exatamente 1 tick acionando o temporizador do Hardware (IRQ 0)."""
        if not self.so_atual:
            return

        self.historico.salvar_passado(self.so_atual)
        self.so_atual.hardware.gerar_interrupcao_tick()

    def retroceder_tick(self) -> bool:
        """Retrocede a simulação em 1 passo no histórico, descartando o estado/edição atual."""
        if not self.so_atual or not self.historico.pode_retroceder():
            return False

        self.so_atual = self.historico.retroceder(self.so_atual)
        return True

    def executar_completo(self, max_ticks: int = 10000) -> bool:
        """Executa a simulação continuamente até que todas as tarefas válidas completem 10 execuções."""
        if not self.so_atual:
            return True

        if not any(t.duracao > 0 and t.periodo > 0 for t in self.so_atual.tarefas):
            return True

        contador = 0
        while not self.so_atual.finalizado():
            contador += 1
            if contador > max_ticks:
                return False
            self.historico.salvar_passado(self.so_atual)
            self.so_atual.hardware.gerar_interrupcao_tick()
        return True

    def obter_todos_estados(self) -> List[SistemaOperacional]:
        """Retorna a linha do tempo de snapshots do Sistema Operacional até o instante atual."""
        if not self.so_atual:
            return []
        return self.historico.pilha_passado + [self.so_atual]
