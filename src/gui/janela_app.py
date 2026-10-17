from typing import List
import customtkinter as ctk
from tkinter import filedialog, messagebox
from controlador.controlador_app import ControladorApp
from controlador.dtos import CardTCBDTO
from gui.desenhista_gantt import DesenhistaGantt
from gui.modais_edicao import ModaisConfiguracao
from gui.painel_logs import PainelLogs
from gui.utilitarios_gui import FabricaIcones, GerenciadorTooltip, obter_cor_fundo_card


class JanelaApp(ctk.CTk):
    """
    Interface Gráfica Principal da Aplicação (100% Dummy / Passive View).
    Coordena os componentes visuais de alto nível consumindo exclusivamente DTOs do ControladorApp:
    - Topo: botões de controle de simulação e resumo das configurações do sistema.
    - Esquerda: Gráfico de Gantt e barra horizontal inferior de cartões TCB.
    - Direita: PainelLogs retrátil exibindo as chamadas das funções-chave do core.
    """

    def __init__(self) -> None:
        super().__init__()
        self.title("Simulador de Sistema Operacional Multitarefa")
        self.geometry("1280x800")
        self.minsize(1100, 720)

        self.controlador: ControladorApp = ControladorApp()
        self.desenhista: DesenhistaGantt = DesenhistaGantt()
        self.tooltip: GerenciadorTooltip = GerenciadorTooltip(self)

        self.icone_editar_card: ctk.CTkImage = FabricaIcones.criar_icone_editar((15, 15))
        self.icone_editar_topo: ctk.CTkImage = FabricaIcones.criar_icone_editar((18, 18))
        self.icone_editar_legenda: ctk.CTkImage = FabricaIcones.criar_icone_editar((14, 14))
        self.icone_adicionar: ctk.CTkImage = FabricaIcones.criar_icone_adicionar((20, 20))
        self.icone_adicionar_legenda: ctk.CTkImage = FabricaIcones.criar_icone_adicionar((14, 14))

        self._configurar_interface()

        # Inicializa o sistema no estado default (1 única tarefa com dados zerados em NOVA)
        self.controlador.configurar_sistema(algoritmo="RM", quantum=0, qtde_cpus=1)
        self.atualizar_interface()

    def _configurar_interface(self) -> None:
        """Constrói o layout principal dividindo barra superior, área esquerda e sidebar de logs."""
        self._construir_barra_superior()

        self.frame_conteudo = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_conteudo.pack(side="top", fill="both", expand=True, padx=12, pady=(0, 10))

        self.painel_logs = PainelLogs(self.frame_conteudo, self.tooltip)
        self.painel_logs.pack(side="right", fill="y", padx=(8, 0))

        self.frame_area_esquerda = ctk.CTkFrame(self.frame_conteudo, fg_color="transparent")
        self.frame_area_esquerda.pack(side="left", fill="both", expand=True)

        self._construir_barra_inferior_tcb()
        self._construir_area_grafico()

    def _construir_barra_superior(self) -> None:
        """Monta a barra superior com os botões de controle à esquerda e o resumo do S.O. à direita."""
        self.frame_controles = ctk.CTkFrame(self, corner_radius=10)
        self.frame_controles.pack(side="top", fill="x", padx=12, pady=(10, 6))

        self._construir_botoes_execucao()
        self._construir_painel_resumo_sistema()

    def _construir_botoes_execucao(self) -> None:
        """Instancia os botões de controle de arquivo, avanço/retrocesso temporal e exportação."""
        self.frame_botoes_acao = ctk.CTkFrame(self.frame_controles, fg_color="transparent")
        self.frame_botoes_acao.pack(side="left", padx=8, pady=8)

        especificacoes = [
            ("btn_carregar", "Carregar Arquivo", 132, self.acao_carregar_arquivo),
            ("btn_retroceder", "Retroceder", 106, self.acao_retroceder),
            ("btn_avancar", "Avançar Tick", 114, self.acao_avancar),
            ("btn_exec_completa", "Execução Completa", 142, self.acao_executar_completo),
            ("btn_exportar", "Exportar Imagem", 132, self.acao_exportar),
        ]
        for attr, texto, largura, comando in especificacoes:
            botao = ctk.CTkButton(
                self.frame_botoes_acao,
                text=texto,
                width=largura,
                height=36,
                corner_radius=6,
                font=("Arial", 12, "bold"),
                command=comando,
            )
            botao.pack(side="left", padx=4)
            setattr(self, attr, botao)

    def _construir_painel_resumo_sistema(self) -> None:
        """Instancia o quadro informativo superior direito com os parâmetros globais e botão de edição."""
        self.frame_config_sistema = ctk.CTkFrame(
            self.frame_controles,
            fg_color=("gray88", "gray19"),
            border_width=2,
            border_color="#2E86C1",
            corner_radius=8,
        )
        self.frame_config_sistema.pack(side="right", padx=10, pady=6)

        frame_textos = ctk.CTkFrame(self.frame_config_sistema, fg_color="transparent")
        frame_textos.pack(side="left", padx=(14, 10), pady=6)

        self.lbl_config_1 = ctk.CTkLabel(
            frame_textos,
            text="Tick Atual: 0   |   Escalonador: Rate Monotonic",
            font=("Arial", 12, "bold"),
            anchor="w",
        )
        self.lbl_config_1.pack(anchor="w")

        self.lbl_config_2 = ctk.CTkLabel(
            frame_textos,
            text="Processadores: 1   |   Quantum: 0",
            font=("Arial", 12, "bold"),
            text_color=("#1B4F72", "#85C1E9"),
            anchor="w",
        )
        self.lbl_config_2.pack(anchor="w", pady=(2, 0))

        self.btn_configurar = ctk.CTkButton(
            self.frame_config_sistema,
            text="",
            image=self.icone_editar_topo,
            width=40,
            height=38,
            corner_radius=6,
            fg_color="#2E86C1",
            hover_color="#1F618D",
            command=self.acao_abrir_modal_sistema,
        )
        self.btn_configurar.pack(side="right", padx=(4, 10), pady=8)
        self.tooltip.associar(self.btn_configurar, "Editar Configuração")

    def _construir_barra_inferior_tcb(self) -> None:
        """Monta a barra horizontal inferior contendo o botão '+', os cartões TCB e a legenda."""
        cor_fundo = obter_cor_fundo_card()
        self.frame_barra_inferior = ctk.CTkFrame(
            self.frame_area_esquerda,
            height=246,
            fg_color=cor_fundo,
            border_width=1,
            border_color=("gray75", "gray30"),
            corner_radius=10,
        )
        self.frame_barra_inferior.pack(side="bottom", fill="x", pady=(8, 0))
        self.frame_barra_inferior.pack_propagate(False)

        self._construir_legenda_barra_inferior()
        self._construir_area_rolavel_cards(cor_fundo)

    def _construir_legenda_barra_inferior(self) -> None:
        """Cria a faixa inferior de legenda dos botões e indicadores de estado dos cartões TCB."""
        self.frame_legenda_cards = ctk.CTkFrame(
            self.frame_barra_inferior,
            height=28,
            fg_color=("gray84", "gray15"),
            corner_radius=6,
        )
        self.frame_legenda_cards.pack(side="bottom", fill="x", padx=8, pady=(2, 6))
        self.frame_legenda_cards.pack_propagate(False)

        ctk.CTkLabel(
            self.frame_legenda_cards,
            text="Legenda:",
            font=("Arial", 11, "bold"),
            text_color=("gray20", "gray85"),
        ).pack(side="left", padx=(8, 4), pady=2)

        ctk.CTkLabel(
            self.frame_legenda_cards,
            text=" Nova Tarefa",
            image=self.icone_adicionar_legenda,
            compound="left",
            font=("Arial", 10, "bold"),
            fg_color="#27AE60",
            text_color="white",
            corner_radius=4,
            padx=5,
            pady=1,
        ).pack(side="left", padx=3, pady=3)

        ctk.CTkLabel(
            self.frame_legenda_cards,
            text=" Editar Tarefa/Sistema",
            image=self.icone_editar_legenda,
            compound="left",
            font=("Arial", 10, "bold"),
            fg_color="#34495E",
            text_color="white",
            corner_radius=4,
            padx=5,
            pady=1,
        ).pack(side="left", padx=3, pady=3)

        texto_estados = (
            "  |  Cor: Executando  |  Branco: Pronta/Nova"
            "  |  Preto: Suspensa  |  Borda Vermelha: Perda de DeadLine"
        )
        ctk.CTkLabel(
            self.frame_legenda_cards,
            text=texto_estados,
            font=("Arial", 10, "bold"),
            text_color=("gray20", "gray85"),
        ).pack(side="left", padx=3, pady=2)

    def _construir_area_rolavel_cards(self, cor_fundo: str) -> None:
        """Instancia o botão '+' à esquerda e o canvas horizontal rolável de cartões TCB."""
        self.frame_linha_cards = ctk.CTkFrame(self.frame_barra_inferior, fg_color=cor_fundo)
        self.frame_linha_cards.pack(side="top", fill="both", expand=True, padx=8, pady=(6, 2))

        self.frame_botao_mais = ctk.CTkFrame(self.frame_linha_cards, fg_color=cor_fundo)
        self.frame_botao_mais.pack(side="left", fill="y", padx=(2, 6), pady=4)

        self.btn_adicionar_tarefa = ctk.CTkButton(
            self.frame_botao_mais,
            text="",
            image=self.icone_adicionar,
            width=48,
            corner_radius=8,
            fg_color="#27AE60",
            hover_color="#1E8449",
            command=self.acao_abrir_modal_adicionar_tarefa,
        )
        self.btn_adicionar_tarefa.pack(fill="both", expand=True)
        self.tooltip.associar(self.btn_adicionar_tarefa, "Adicionar Tarefa")

        self.frame_area_cards = ctk.CTkFrame(self.frame_linha_cards, fg_color=cor_fundo)
        self.frame_area_cards.pack(side="left", fill="both", expand=True, padx=(2, 2), pady=0)

        self.canvas_cards = ctk.CTkCanvas(
            self.frame_area_cards, bg=cor_fundo, highlightthickness=0, height=176
        )
        self.scroll_cards_x = ctk.CTkScrollbar(
            self.frame_area_cards, orientation="horizontal", command=self.canvas_cards.xview, height=14
        )
        self.canvas_cards.configure(xscrollcommand=self.scroll_cards_x.set)

        self.scroll_cards_x.pack(side="bottom", fill="x", padx=4, pady=(0, 2))
        self.canvas_cards.pack(side="top", fill="both", expand=True, padx=2, pady=(2, 2))

        self.frame_interno_cards = ctk.CTkFrame(self.canvas_cards, fg_color=cor_fundo)
        self.canvas_cards.create_window((0, 0), window=self.frame_interno_cards, anchor="nw")
        self.frame_interno_cards.bind(
            "<Configure>",
            lambda _e: self.canvas_cards.configure(scrollregion=self.canvas_cards.bbox("all")),
        )

    def _construir_area_grafico(self) -> None:
        """Monta o container central do Gráfico de Gantt com barras de rolagem horizontal e vertical."""
        self.frame_grafico = ctk.CTkFrame(self.frame_area_esquerda, corner_radius=10)
        self.frame_grafico.pack(side="top", fill="both", expand=True)

        self.canvas = ctk.CTkCanvas(self.frame_grafico, bg="#ffffff", highlightthickness=0)
        self.scroll_x = ctk.CTkScrollbar(self.frame_grafico, orientation="horizontal", command=self.canvas.xview)
        self.scroll_y = ctk.CTkScrollbar(self.frame_grafico, orientation="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.scroll_x.set, yscrollcommand=self.scroll_y.set)

        self.scroll_y.pack(side="right", fill="y", padx=(0, 4), pady=4)
        self.scroll_x.pack(side="bottom", fill="x", padx=4, pady=(0, 4))
        self.canvas.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=(4, 0))

    # ------------------------------------------------------------------
    # Tratadores de Eventos do Usuário
    # ------------------------------------------------------------------
    def acao_carregar_arquivo(self) -> None:
        """Abre diálogo de seleção de arquivo .txt e solicita carregamento ao ControladorApp."""
        caminho = filedialog.askopenfilename(
            title="Selecionar Arquivo de Configuração",
            filetypes=[("Arquivos de Texto", "*.txt"), ("Todos os Arquivos", "*.*")],
        )
        if not caminho:
            return

        try:
            avisos = self.controlador.carregar_arquivo(caminho)
            self.atualizar_interface()
            if avisos:
                messagebox.showwarning("Tarefas Aperiódicas Ignoradas", "\n\n".join(avisos))
        except Exception as e:
            messagebox.showerror("Erro ao Carregar Arquivo de Configuração", str(e))

    def acao_avancar(self) -> None:
        """Avança a simulação em 1 tick."""
        self.controlador.avancar_tick()
        self.atualizar_interface()

    def acao_retroceder(self) -> None:
        """Retrocede a simulação em 1 tick quando há histórico disponível."""
        if self.controlador.retroceder_tick():
            self.atualizar_interface()

    def acao_executar_completo(self) -> None:
        """Executa a simulação até o término das 10 instâncias de todas as tarefas válidas."""
        if not self.controlador.executar_completo():
            messagebox.showwarning(
                "Limite de Segurança",
                "O limite máximo de ticks foi atingido antes da conclusão de todas as tarefas.",
            )
        self.atualizar_interface()

    def acao_exportar(self) -> None:
        """Exporta o Gráfico de Gantt completo em alta resolução (PNG/JPG)."""
        if not self.controlador.tem_simulacao_ativa():
            messagebox.showwarning("Aviso", "Nenhuma simulação ativa para exportar.")
            return

        caminho = filedialog.asksaveasfilename(
            title="Exportar Gráfico de Gantt Completo",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg")],
        )
        if caminho:
            dados_gantt = self.controlador.obter_dados_gantt(para_exportacao=True)
            self.desenhista.exportar_para_arquivo(caminho, dados_gantt)
            messagebox.showinfo("Exportação Concluída", "Gráfico de Gantt completo exportado com sucesso!")

    def acao_abrir_modal_sistema(self) -> None:
        """Abre o diálogo modal de edição dos parâmetros do Sistema Operacional."""
        self.tooltip.esconder()
        ModaisConfiguracao.abrir_modal_sistema(self, self.controlador, self.atualizar_interface)

    def acao_abrir_modal_adicionar_tarefa(self) -> None:
        """Abre o diálogo modal para inclusão de uma nova tarefa."""
        self.tooltip.esconder()
        ModaisConfiguracao.abrir_modal_adicionar_tarefa(self, self.controlador, self.atualizar_interface)

    def _abrir_modal_editar_tarefa(self, card: CardTCBDTO) -> None:
        """Abre o diálogo modal para edição manual da tarefa selecionada."""
        self.tooltip.esconder()
        ModaisConfiguracao.abrir_modal_editar_tarefa(self, self.controlador, card, self.atualizar_interface)

    # ------------------------------------------------------------------
    # Atualização Passiva da Tela a partir dos DTOs Tipados
    # ------------------------------------------------------------------
    def atualizar_interface(self) -> None:
        """Atualiza cabeçalho, Gráfico de Gantt, cartões TCB e painel de Logs."""
        self.tooltip.esconder()
        cabecalho = self.controlador.obter_dados_cabecalho()
        self.lbl_config_1.configure(text=cabecalho.texto_linha_1)
        self.lbl_config_2.configure(text=cabecalho.texto_linha_2)

        self.btn_avancar.configure(state="normal" if cabecalho.pode_avancar else "disabled")
        self.btn_retroceder.configure(state="normal" if cabecalho.pode_retroceder else "disabled")
        self.btn_exec_completa.configure(state="normal" if cabecalho.pode_executar_completo else "disabled")

        if not self.controlador.tem_simulacao_ativa():
            return

        self.desenhista.desenhar_no_canvas(
            self.canvas, self.controlador.obter_dados_gantt(para_exportacao=False)
        )
        self._atualizar_barra_inferior_tcb(self.controlador.obter_dados_cards_tcb())
        self.painel_logs.atualizar(self.controlador.obter_dados_logs_didaticos())

    def _atualizar_barra_inferior_tcb(self, cards_tcb: List[CardTCBDTO]) -> None:
        """Reconstrói os cartões de TCB na barra horizontal inferior."""
        cor_fundo = obter_cor_fundo_card()
        for container in (
            self.frame_barra_inferior,
            self.frame_linha_cards,
            self.frame_botao_mais,
            self.frame_area_cards,
            self.frame_interno_cards,
        ):
            container.configure(fg_color=cor_fundo)
        self.canvas_cards.configure(bg=cor_fundo)

        for widget in self.frame_interno_cards.winfo_children():
            widget.destroy()

        for card in cards_tcb:
            self._criar_card_tcb_widget(card, cor_fundo)

        self.frame_interno_cards.update_idletasks()
        self.canvas_cards.configure(scrollregion=self.canvas_cards.bbox("all"))

    def _criar_card_tcb_widget(self, card: CardTCBDTO, cor_fundo: str) -> None:
        """Instancia um cartão individual de TCB com indicador colorido, dados e botão de edição."""
        borda_cor = "#E74C3C" if card.esta_atrasada else "#5D6D7E"
        frame_card = ctk.CTkFrame(
            self.frame_interno_cards,
            width=172,
            height=168,
            fg_color=cor_fundo,
            border_width=2 if card.esta_atrasada else 1,
            border_color=borda_cor,
            corner_radius=8,
        )
        frame_card.pack(side="left", padx=5, pady=3)
        frame_card.pack_propagate(False)

        frame_topo = ctk.CTkFrame(frame_card, fg_color=cor_fundo)
        frame_topo.pack(fill="x", padx=8, pady=(6, 2))

        ctk.CTkFrame(
            frame_topo,
            width=12,
            height=12,
            fg_color=card.cor_indicador,
            border_color="black",
            border_width=1,
            corner_radius=3,
        ).pack(side="left", padx=(0, 5))

        ctk.CTkLabel(
            frame_topo,
            text=card.titulo,
            font=("Arial", 12, "bold"),
            fg_color=cor_fundo,
        ).pack(side="left")

        btn_editar = ctk.CTkButton(
            frame_topo,
            text="",
            image=self.icone_editar_card,
            width=26,
            height=24,
            corner_radius=5,
            fg_color="#34495E",
            hover_color="#2E86C1",
            command=lambda c=card: self._abrir_modal_editar_tarefa(c),
        )
        btn_editar.pack(side="right", padx=(2, 0))
        self.tooltip.associar(btn_editar, f"Editar Tarefa {card.id_tarefa}")

        ctk.CTkLabel(
            frame_card,
            text="\n".join(card.linhas_informacao),
            font=("Arial", 11),
            justify="left",
            anchor="w",
            fg_color=cor_fundo,
        ).pack(fill="both", expand=True, padx=8, pady=(0, 6))

