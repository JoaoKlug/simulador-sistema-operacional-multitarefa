from typing import Callable, Dict, Tuple
import customtkinter as ctk
from controlador.dtos import BlocoLogTickDTO, LogsDidaticosDTO
from gui.utilitarios_gui import GerenciadorTooltip, obter_cor_fundo_card


class PainelLogs(ctk.CTkFrame):
    """
    Sidebar direita retrátil 'Logs' (100% Passive View).
    Exibe em ordem cronológica as chamadas das funções-chave de src/core/
    com tipografia reduzida (9pt) para leitura confortável e sem poluição visual.
    """
    LARGURA_EXPANDIDA: int = 360
    LARGURA_RECOLHIDA: int = 44

    # Paleta declarativa por categoria (cor_modo_claro, cor_modo_escuro)
    PALETA_CATEGORIAS: Dict[str, Tuple[str, str]] = {
        "IRQ": ("#6C3483", "#BB8FCE"),
        "CICLO_VIDA": ("#1E8449", "#58D68D"),
        "ESCALONADOR": ("#9A7D0A", "#F4D03F"),
        "DESPACHANTE": ("#1F618D", "#5DADE2"),
        "PREEMPCAO": ("#CA6F1E", "#EB984E"),
        "CONCLUSAO": ("#1E8449", "#58D68D"),
        "DEADLINE": ("#C0392B", "#EC7063"),
        "HARDWARE": ("#117864", "#48C9B0"),
        "SISTEMA": ("#1B4F72", "#5DADE2"),
        "INFO": ("#2C3E50", "#AEB6BF"),
    }

    def __init__(
        self,
        container_pai: ctk.CTkBaseClass,
        gerenciador_tooltip: GerenciadorTooltip,
    ) -> None:
        super().__init__(
            container_pai,
            width=self.LARGURA_EXPANDIDA,
            fg_color=obter_cor_fundo_card(),
            border_width=1,
            border_color=("gray75", "gray30"),
            corner_radius=10,
        )
        self.pack_propagate(False)
        self._tooltip: GerenciadorTooltip = gerenciador_tooltip
        self._recolhida: bool = False
        self._qtde_blocos_renderizados: int = 0
        self._primeiro_cabecalho_renderizado: str = ""

        self._construir_componentes()

    def _construir_componentes(self) -> None:
        """Instancia o cabeçalho com título 'Logs', botão de recolhimento e área de texto."""
        self.frame_topo = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_topo.pack(side="top", fill="x", padx=10, pady=(8, 4))

        self.lbl_titulo = ctk.CTkLabel(
            self.frame_topo,
            text="Logs",
            font=("Arial", 13, "bold"),
            anchor="w",
        )
        self.lbl_titulo.pack(side="left", padx=(2, 4))

        self.btn_alternar = ctk.CTkButton(
            self.frame_topo,
            text="»",
            width=28,
            height=26,
            corner_radius=6,
            font=("Arial", 13, "bold"),
            fg_color="#34495E",
            hover_color="#2E86C1",
            command=self.alternar_recolhimento,
        )
        self.btn_alternar.pack(side="right")
        self._tooltip.associar(self.btn_alternar, "Recolher / Expandir Logs")

        self.txt_logs = ctk.CTkTextbox(
            self,
            wrap="word",
            font=("Consolas", 9),
            corner_radius=8,
            fg_color=("#FFFFFF", "#1B1B1B"),
            border_width=1,
            border_color=("gray78", "gray28"),
            activate_scrollbars=True,
        )
        self.txt_logs.pack(side="top", fill="both", expand=True, padx=8, pady=(2, 8))
        self._configurar_tags_texto()
        self.txt_logs.configure(state="disabled")

    def _configurar_tags_texto(self) -> None:
        """Configura as tags tipográficas (9pt) no Textbox interno de acordo com o tema ativo."""
        indice_cor = 1 if ctk.get_appearance_mode().lower() == "dark" else 0
        tb = self.txt_logs._textbox

        cor_cabecalho = self.PALETA_CATEGORIAS["SISTEMA"][indice_cor]
        cor_detalhe = "#E5E7E9" if indice_cor == 1 else "#222222"

        tb.tag_configure(
            "cabecalho",
            font=("Consolas", 9, "bold"),
            foreground=cor_cabecalho,
            spacing1=5,
            spacing3=1,
        )
        for categoria, par_cores in self.PALETA_CATEGORIAS.items():
            tb.tag_configure(
                f"fn_{categoria}",
                font=("Consolas", 9, "bold"),
                foreground=par_cores[indice_cor],
            )
        tb.tag_configure(
            "detalhe",
            font=("Segoe UI", 9),
            foreground=cor_detalhe,
            lmargin1=12,
            lmargin2=12,
            spacing3=2,
        )

    def alternar_recolhimento(self) -> None:
        """Recolhe ou expande a sidebar para ampliar a área útil do Gráfico de Gantt."""
        self._tooltip.esconder()
        self._recolhida = not self._recolhida
        if self._recolhida:
            self.txt_logs.pack_forget()
            self.lbl_titulo.pack_forget()
            self.frame_topo.pack_configure(padx=6)
            self.btn_alternar.configure(text="«")
            self.configure(width=self.LARGURA_RECOLHIDA)
        else:
            self.configure(width=self.LARGURA_EXPANDIDA)
            self.frame_topo.pack_configure(padx=10)
            self.lbl_titulo.pack(side="left", padx=(2, 4))
            self.btn_alternar.configure(text="»")
            self.txt_logs.pack(side="top", fill="both", expand=True, padx=8, pady=(2, 8))
            self.txt_logs.see("end")

    def atualizar(self, logs_dto: LogsDidaticosDTO) -> None:
        """Atualiza o console de logs de forma incremental ou reconstrói ao retroceder/recarregar."""
        self.configure(fg_color=obter_cor_fundo_card())
        self._configurar_tags_texto()

        blocos = logs_dto.blocos
        primeiro_cab = blocos[0].cabecalho_tick if blocos else ""

        self.txt_logs.configure(state="normal")
        tb = self.txt_logs._textbox

        if self._pode_anexar_incrementalmente(len(blocos), primeiro_cab):
            for idx in range(self._qtde_blocos_renderizados, len(blocos)):
                self._inserir_bloco(blocos[idx], adicionar_quebra_antes=(idx > 0))
        elif len(blocos) != self._qtde_blocos_renderizados or primeiro_cab != self._primeiro_cabecalho_renderizado:
            tb.delete("1.0", "end")
            for idx, bloco in enumerate(blocos):
                self._inserir_bloco(bloco, adicionar_quebra_antes=(idx > 0))

        self._qtde_blocos_renderizados = len(blocos)
        self._primeiro_cabecalho_renderizado = primeiro_cab
        self.txt_logs.see("end")
        self.txt_logs.configure(state="disabled")

    def _pode_anexar_incrementalmente(self, total_blocos: int, primeiro_cab: str) -> bool:
        """Indica se apenas novos ticks foram adicionados ao final da mesma simulação."""
        return (
            total_blocos > self._qtde_blocos_renderizados
            and self._qtde_blocos_renderizados > 0
            and primeiro_cab == self._primeiro_cabecalho_renderizado
        )

    def _inserir_bloco(self, bloco: BlocoLogTickDTO, adicionar_quebra_antes: bool) -> None:
        """Insere um bloco de chamadas de função do core formatado no console."""
        tb = self.txt_logs._textbox
        prefixo = "\n" if adicionar_quebra_antes else ""
        tb.insert("end", f"{prefixo}━━ {bloco.cabecalho_tick} ━━\n", "cabecalho")
        for ch in bloco.chamadas:
            tag_fn = f"fn_{ch.categoria}" if ch.categoria in self.PALETA_CATEGORIAS else "fn_INFO"
            tb.insert("end", f"▸ {ch.funcao}\n", tag_fn)
            tb.insert("end", f"{ch.detalhe}\n", "detalhe")

