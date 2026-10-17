from typing import Optional, Tuple
import customtkinter as ctk
from PIL import Image, ImageDraw


def obter_cor_fundo_card() -> str:
    """Retorna a cor hexadecimal unificada para os cards e painéis conforme o tema atual."""
    modo = ctk.get_appearance_mode().lower()
    return "#262626" if modo == "dark" else "#F2F3F4"


class FabricaIcones:
    """Fábrica de ícones vetoriais nítidos renderizados com anti-aliasing via Pillow."""

    @staticmethod
    def criar_icone_editar(tamanho: Tuple[int, int]) -> ctk.CTkImage:
        """Gera um ícone vetorial de edição (quadro de nota + caneta diagonal)."""
        n = 64
        img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cor = (255, 255, 255, 255)

        draw.line([(10, 16), (34, 16)], fill=cor, width=5)
        draw.line([(10, 16), (10, 54)], fill=cor, width=5)
        draw.line([(10, 54), (48, 54)], fill=cor, width=5)
        draw.line([(48, 54), (48, 30)], fill=cor, width=5)

        corpo = [(48, 8), (56, 16), (31, 41), (23, 33)]
        draw.polygon(corpo, fill=cor)

        ponta = [(21, 35), (29, 43), (17, 47)]
        draw.polygon(ponta, fill=cor)

        img_suave = img.resize(tamanho, Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=img_suave, dark_image=img_suave, size=tamanho)

    @staticmethod
    def criar_icone_adicionar(tamanho: Tuple[int, int]) -> ctk.CTkImage:
        """Gera um ícone vetorial de adição (+) com cantos arredondados."""
        n = 64
        img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cor = (255, 255, 255, 255)

        draw.rounded_rectangle([27, 10, 37, 54], radius=3, fill=cor)
        draw.rounded_rectangle([10, 27, 54, 37], radius=3, fill=cor)

        img_suave = img.resize(tamanho, Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=img_suave, dark_image=img_suave, size=tamanho)


class GerenciadorTooltip:
    """Gerencia o overlay interno de tooltips sem criar janelas Toplevel órfãs."""

    def __init__(self, janela_raiz: ctk.CTk) -> None:
        self.janela: ctk.CTk = janela_raiz
        self._widget_ativo: Optional[ctk.CTkBaseClass] = None
        self._id_monitor: Optional[str] = None

        self._frame = ctk.CTkFrame(
            self.janela,
            fg_color="#1C2833",
            border_width=1,
            border_color="#5DADE2",
            corner_radius=6,
        )
        self._label = ctk.CTkLabel(
            self._frame,
            text="",
            font=("Arial", 11, "bold"),
            text_color="#FFFFFF",
            padx=8,
            pady=3,
        )
        self._label.pack()

    def esconder(self, _evento=None) -> None:
        """Oculta imediatamente o overlay de tooltip e cancela o monitoramento ativo."""
        if self._id_monitor is not None:
            try:
                self.janela.after_cancel(self._id_monitor)
            except Exception:
                pass
            self._id_monitor = None
        self._widget_ativo = None
        self._frame.place_forget()

    def associar(self, widget: ctk.CTkBaseClass, texto: str) -> None:
        """Registra eventos de hover e clique no widget para exibir/ocultar o tooltip."""
        widget.bind("<Enter>", lambda _e: self._mostrar(widget, texto), add="+")
        widget.bind("<Leave>", self.esconder, add="+")
        widget.bind("<ButtonPress>", self.esconder, add="+")

    def _mostrar(self, widget: ctk.CTkBaseClass, texto: str) -> None:
        """Posiciona e exibe o tooltip próximo ao widget alvo."""
        if not widget.winfo_exists():
            return
        self.esconder()
        self._widget_ativo = widget
        self._label.configure(text=texto)
        self._frame.update_idletasks()

        larg_tip = self._frame.winfo_reqwidth()
        alt_tip = self._frame.winfo_reqheight()

        rel_x = widget.winfo_rootx() - self.janela.winfo_rootx() + (widget.winfo_width() // 2) - (larg_tip // 2)
        rel_y = widget.winfo_rooty() - self.janela.winfo_rooty() - alt_tip - 6
        if rel_y < 6:
            rel_y = widget.winfo_rooty() - self.janela.winfo_rooty() + widget.winfo_height() + 6

        max_x = max(10, self.janela.winfo_width() - larg_tip - 10)
        rel_x = max(8, min(rel_x, max_x))

        self._frame.place(x=rel_x, y=rel_y)
        self._frame.lift()
        self._id_monitor = self.janela.after(80, self._monitorar_cursor)

    def _monitorar_cursor(self) -> None:
        """Verifica periodicamente se o cursor permanece sobre o widget ativo."""
        if not self._cursor_sobre_widget_ativo():
            self.esconder()
            return
        self._id_monitor = self.janela.after(80, self._monitorar_cursor)

    def _cursor_sobre_widget_ativo(self) -> bool:
        """Retorna True se o widget ativo ainda existe e contém a posição atual do mouse."""
        w = self._widget_ativo
        if w is None:
            return False
        try:
            if not w.winfo_exists() or not w.winfo_viewable():
                return False
            px, py = self.janela.winfo_pointerxy()
            wx, wy = w.winfo_rootx(), w.winfo_rooty()
            return wx <= px <= wx + w.winfo_width() and wy <= py <= wy + w.winfo_height()
        except Exception:
            return False

