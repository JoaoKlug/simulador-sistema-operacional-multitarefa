from dataclasses import dataclass
from typing import Any, List
from PIL import Image, ImageDraw, ImageFont
from controlador.dtos import DadosGanttDTO, SegmentoGanttDTO, MarcadorEventoGanttDTO


@dataclass(frozen=True)
class ContextoPillowGantt:
    """Agrupa as dimensões escalonadas, fontes e superfície de desenho para exportação via Pillow."""
    draw: ImageDraw.ImageDraw
    escala: int
    margem_esq: int
    margem_sup: int
    largura_tick: int
    altura_tarefa: int
    passo_y: int
    y_eixo_x: int
    y_faixa_off: int
    y_legenda: int
    x_final_eixo: int
    fonte_rotulo: Any
    fonte_tick: Any


class DesenhistaGantt:
    """
    Renderizador do Gráfico de Gantt (100% Dummy / Passive View).
    Opera exclusivamente sobre o contrato tipado DadosGanttDTO para desenhar no Tkinter Canvas
    ou exportar em alta resolução via Pillow, sem nenhum acoplamento com o domínio do S.O.
    - Mantém o foco visual nas tarefas (T1 diretamente junto ao eixo X conforme Requisito 2.5).
    - Representa a ociosidade das CPUs sem retângulos preenchidos e sem criar N linhas no eixo Y,
      usando uma única faixa discreta de colchetes horizontais (├── C1 ──┤) + resumo acumulado.
    """
    MARGEM_ESQ: int = 85
    MARGEM_SUP: int = 30
    LARGURA_TICK: int = 28
    ALTURA_TAREFA: int = 32
    ESPACO_TAREFA: int = 16
    ALTURA_EIXO_X: int = 26
    ALTURA_FAIXA_OFF: int = 22
    ALTURA_LEGENDA: int = 85

    ITENS_LEGENDA_ESTADOS = [
        ("Cor Sólida: Executando", "#5DADE2", False, False),
        ("Branco: Pronta", "white", False, False),
        ("Pontilhado: Suspensa", "white", True, False),
        ("Colchete Tracejado: CPU OFF", "white", False, True),
    ]

    ITENS_LEGENDA_EVENTOS = [
        ("INGRESSO", "Ingresso"),
        ("TERMINO", "Término"),
        ("DEADLINE", "Perda de DeadLine"),
        ("SORTEIO", "Desempate por Sorteio"),
    ]

    # ------------------------------------------------------------------
    # Renderização em Tkinter Canvas
    # ------------------------------------------------------------------
    def desenhar_no_canvas(self, canvas, dados_gantt: DadosGanttDTO) -> None:
        """Desenha o Gráfico de Gantt mantendo as tarefas em destaque e a trilha discreta de CPU OFF."""
        canvas.delete("all")
        tarefas_eixo_y = dados_gantt.tarefas_eixo_y
        if not tarefas_eixo_y:
            return

        passo_y = self.ALTURA_TAREFA + self.ESPACO_TAREFA
        y_eixo_x = self.MARGEM_SUP + len(tarefas_eixo_y) * passo_y
        x_final_eixo = self.MARGEM_ESQ + dados_gantt.max_tick * self.LARGURA_TICK

        self._desenhar_eixos_canvas(canvas, tarefas_eixo_y, dados_gantt.max_tick, y_eixo_x, x_final_eixo)

        for seg in dados_gantt.segmentos:
            if seg.id_tarefa in tarefas_eixo_y:
                y_ini = self.MARGEM_SUP + tarefas_eixo_y.index(seg.id_tarefa) * passo_y
                self._desenhar_segmento_canvas(canvas, seg, y_ini)

        self._desenhar_eventos_canvas(canvas, dados_gantt.eventos, tarefas_eixo_y)

        y_faixa_off = y_eixo_x + self.ALTURA_EIXO_X + 10
        canvas.create_text(
            self.MARGEM_ESQ - 12, y_faixa_off, text="CPU OFF", anchor="e", font=("Arial", 8, "bold"), fill="#616161"
        )
        for seg_off in dados_gantt.segmentos_cpus_desligadas:
            self._desenhar_colchete_off_canvas(canvas, seg_off, y_faixa_off)

        y_legenda = y_faixa_off + self.ALTURA_FAIXA_OFF + 8
        self._desenhar_legenda_canvas(canvas, y_legenda, dados_gantt.resumo_cpus_desligadas)

        largura_total = max(x_final_eixo + 80, 920)
        altura_total = y_legenda + self.ALTURA_LEGENDA
        canvas.configure(scrollregion=(0, 0, largura_total, altura_total))

    def _desenhar_eixos_canvas(
        self,
        canvas,
        tarefas_eixo_y: List[int],
        max_tick: int,
        y_eixo_x: int,
        x_final_eixo: int,
    ) -> None:
        """Desenha os rótulos das tarefas no eixo Y e a grade temporal no eixo X."""
        passo_y = self.ALTURA_TAREFA + self.ESPACO_TAREFA
        for i, id_t in enumerate(tarefas_eixo_y):
            y = self.MARGEM_SUP + i * passo_y
            canvas.create_text(
                self.MARGEM_ESQ - 12,
                y + self.ALTURA_TAREFA / 2,
                text=f"T{id_t}",
                anchor="e",
                font=("Arial", 10, "bold"),
                fill="#111111",
            )

        canvas.create_line(self.MARGEM_ESQ, self.MARGEM_SUP - 6, self.MARGEM_ESQ, y_eixo_x, fill="#222222", width=2)
        canvas.create_line(self.MARGEM_ESQ, y_eixo_x, x_final_eixo, y_eixo_x, fill="#222222", width=2)

        for tck in range(0, max_tick + 1):
            x = self.MARGEM_ESQ + tck * self.LARGURA_TICK
            if tck > 0:
                canvas.create_line(x, self.MARGEM_SUP - 4, x, y_eixo_x, fill="#d4d4d4", dash=(2, 2))
            canvas.create_line(x, y_eixo_x, x, y_eixo_x + 5, fill="#222222", width=2)
            canvas.create_text(x, y_eixo_x + 14, text=str(tck), font=("Arial", 9, "bold"), fill="#222222")

    def _desenhar_colchete_off_canvas(self, canvas, seg: SegmentoGanttDTO, y_centro: int) -> None:
        """Desenha um colchete horizontal discreto ├── C1 ──┤ sem retângulo preenchido."""
        x_ini = self.MARGEM_ESQ + seg.tick_inicio * self.LARGURA_TICK + 1
        x_fim = self.MARGEM_ESQ + seg.tick_fim * self.LARGURA_TICK - 1
        if x_fim <= x_ini:
            return

        cor_linha = "#7F8C8D"
        canvas.create_line(x_ini, y_centro, x_fim, y_centro, fill=cor_linha, width=2, dash=(3, 2))
        canvas.create_line(x_ini, y_centro - 4, x_ini, y_centro + 4, fill=cor_linha, width=2)
        canvas.create_line(x_fim, y_centro - 4, x_fim, y_centro + 4, fill=cor_linha, width=2)

        if seg.texto:
            canvas.create_text(
                (x_ini + x_fim) / 2, y_centro - 8, text=seg.texto, font=("Arial", 8, "bold"), fill="#424949"
            )

    def _desenhar_segmento_canvas(self, canvas, seg: SegmentoGanttDTO, y_inicio: int) -> None:
        """Desenha o bloco retangular de uma tarefa em um intervalo contínuo no Canvas."""
        y_fim = y_inicio + self.ALTURA_TAREFA
        x_inicio = self.MARGEM_ESQ + seg.tick_inicio * self.LARGURA_TICK
        x_fim = self.MARGEM_ESQ + seg.tick_fim * self.LARGURA_TICK

        kwargs = {"outline": seg.cor_borda, "width": seg.largura_borda}
        if seg.cor_preenchimento:
            kwargs["fill"] = seg.cor_preenchimento
        canvas.create_rectangle(x_inicio, y_inicio, x_fim, y_fim, **kwargs)

        if seg.pontilhado:
            for px in range(int(x_inicio) + 3, int(x_fim) - 1, 6):
                for py in range(int(y_inicio) + 3, int(y_fim) - 1, 6):
                    canvas.create_oval(px, py, px + 2, py + 2, fill="black", outline="black")

        if seg.texto:
            canvas.create_text(
                (x_inicio + x_fim) / 2,
                (y_inicio + y_fim) / 2,
                text=seg.texto,
                font=("Arial", 8, "bold"),
                fill=seg.cor_texto,
            )

    def _desenhar_eventos_canvas(
        self,
        canvas,
        eventos: List[MarcadorEventoGanttDTO],
        tarefas_eixo_y: List[int],
    ) -> None:
        """Itera pelos marcadores de eventos e desenha cada ícone no Canvas."""
        passo_y = self.ALTURA_TAREFA + self.ESPACO_TAREFA
        for ev in eventos:
            if ev.id_tarefa in tarefas_eixo_y:
                y_topo = self.MARGEM_SUP + tarefas_eixo_y.index(ev.id_tarefa) * passo_y
                x = self.MARGEM_ESQ + ev.tick * self.LARGURA_TICK
                self._desenhar_marcador_evento_canvas(canvas, ev.tipo, x, y_topo)

    def _desenhar_marcador_evento_canvas(self, canvas, tipo: str, x: int, y_topo: int) -> None:
        """Desenha um marcador individual (INGRESSO, TERMINO, DEADLINE ou SORTEIO) no Canvas."""
        y_base = y_topo + self.ALTURA_TAREFA
        if tipo == "INGRESSO":
            canvas.create_line(x, y_topo - 11, x, y_topo, fill="#1E8449", width=2)
            canvas.create_polygon(x - 4, y_topo - 5, x + 4, y_topo - 5, x, y_topo, fill="#1E8449", outline="#1E8449")
        elif tipo == "TERMINO":
            canvas.create_line(x, y_base, x, y_base + 11, fill="#1F618D", width=2)
            canvas.create_polygon(x - 4, y_base + 5, x + 4, y_base + 5, x, y_base, fill="#1F618D", outline="#1F618D")
        elif tipo == "DEADLINE":
            canvas.create_polygon(x - 5, y_topo - 12, x + 5, y_topo - 12, x, y_topo - 2, fill="#C0392B", outline="black")
            canvas.create_text(x, y_topo - 16, text="!", font=("Arial", 8, "bold"), fill="#C0392B")
        elif tipo == "SORTEIO":
            cx, cy = x + 6, y_topo + 7
            canvas.create_polygon(cx, cy - 5, cx + 5, cy, cx, cy + 5, cx - 5, cy, fill="#F39C12", outline="black")

    def _desenhar_legenda_canvas(self, canvas, y_legenda: int, resumo_off: str) -> None:
        """Desenha as duas linhas de legenda e o resumo de ociosidade no Canvas."""
        self._desenhar_legenda_estados_canvas(canvas, y_legenda)
        y_linha2 = y_legenda + 24
        self._desenhar_legenda_eventos_canvas(canvas, y_linha2)

        if resumo_off:
            canvas.create_text(
                self.MARGEM_ESQ,
                y_linha2 + 22,
                text=f"TEMPO DE CPUS DESLIGADAS:   {resumo_off}",
                anchor="w",
                font=("Arial", 9, "bold"),
                fill="#444444",
            )

    def _desenhar_legenda_estados_canvas(self, canvas, y_legenda: int) -> None:
        """Desenha a primeira linha da legenda (estados de execução e colchete CPU OFF) no Canvas."""
        x_ini = self.MARGEM_ESQ
        canvas.create_text(x_ini, y_legenda, text="LEGENDA:", anchor="w", font=("Arial", 9, "bold"), fill="#111111")

        cursor_x = x_ini + 72
        for texto, cor, pontilhado, eh_colchete in self.ITENS_LEGENDA_ESTADOS:
            if eh_colchete:
                canvas.create_line(cursor_x, y_legenda, cursor_x + 18, y_legenda, fill="#7F8C8D", width=2, dash=(3, 2))
                canvas.create_line(cursor_x, y_legenda - 4, cursor_x, y_legenda + 4, fill="#7F8C8D", width=2)
                canvas.create_line(cursor_x + 18, y_legenda - 4, cursor_x + 18, y_legenda + 4, fill="#7F8C8D", width=2)
            else:
                canvas.create_rectangle(
                    cursor_x, y_legenda - 7, cursor_x + 16, y_legenda + 7, fill=cor, outline="black"
                )
                if pontilhado:
                    for px in range(cursor_x + 3, cursor_x + 15, 4):
                        for py in range(y_legenda - 4, y_legenda + 6, 4):
                            canvas.create_oval(px, py, px + 1, py + 1, fill="black", outline="black")
            canvas.create_text(cursor_x + 24, y_legenda, text=texto, anchor="w", font=("Arial", 8), fill="#222222")
            cursor_x += 178

    def _desenhar_legenda_eventos_canvas(self, canvas, y_linha2: int) -> None:
        """Desenha a segunda linha da legenda (ícones de eventos) no Canvas."""
        x_ini = self.MARGEM_ESQ
        canvas.create_text(x_ini, y_linha2, text="EVENTOS:", anchor="w", font=("Arial", 9, "bold"), fill="#111111")

        cursor_ev_x = x_ini + 72
        for tipo_ev, rotulo_ev in self.ITENS_LEGENDA_EVENTOS:
            self._desenhar_icone_legenda_evento_canvas(canvas, tipo_ev, cursor_ev_x + 8, y_linha2)
            canvas.create_text(
                cursor_ev_x + 22, y_linha2, text=rotulo_ev, anchor="w", font=("Arial", 8), fill="#222222"
            )
            cursor_ev_x += 178

    def _desenhar_icone_legenda_evento_canvas(self, canvas, tipo_ev: str, cx: int, y_linha2: int) -> None:
        """Desenha um ícone individual na barra de legenda de eventos do Canvas."""
        if tipo_ev == "INGRESSO":
            canvas.create_line(cx, y_linha2 - 6, cx, y_linha2 + 5, fill="#1E8449", width=2)
            canvas.create_polygon(cx - 4, y_linha2, cx + 4, y_linha2, cx, y_linha2 + 6, fill="#1E8449", outline="#1E8449")
        elif tipo_ev == "TERMINO":
            canvas.create_line(cx, y_linha2 + 6, cx, y_linha2 - 5, fill="#1F618D", width=2)
            canvas.create_polygon(cx - 4, y_linha2, cx + 4, y_linha2, cx, y_linha2 - 6, fill="#1F618D", outline="#1F618D")
        elif tipo_ev == "DEADLINE":
            canvas.create_polygon(cx - 5, y_linha2 - 2, cx + 5, y_linha2 - 2, cx, y_linha2 + 6, fill="#C0392B", outline="black")
            canvas.create_text(cx, y_linha2 - 6, text="!", font=("Arial", 8, "bold"), fill="#C0392B")
        elif tipo_ev == "SORTEIO":
            canvas.create_polygon(
                cx, y_linha2 - 5, cx + 5, y_linha2, cx, y_linha2 + 5, cx - 5, y_linha2, fill="#F39C12", outline="black"
            )

    # ------------------------------------------------------------------
    # Exportação de Imagem em Alta Resolução via Pillow
    # ------------------------------------------------------------------
    def exportar_para_arquivo(self, caminho_arquivo: str, dados_gantt: DadosGanttDTO) -> None:
        """Exporta o Gráfico de Gantt completo para imagem PNG/JPG em alta resolução via Pillow."""
        tarefas_eixo_y = dados_gantt.tarefas_eixo_y
        if not tarefas_eixo_y:
            return

        img, ctx = self._criar_contexto_pillow(dados_gantt)
        self._desenhar_eixos_pillow(ctx, tarefas_eixo_y, dados_gantt.max_tick)

        for seg in dados_gantt.segmentos:
            if seg.id_tarefa in tarefas_eixo_y:
                y_ini = ctx.margem_sup + tarefas_eixo_y.index(seg.id_tarefa) * ctx.passo_y
                self._desenhar_segmento_pillow(ctx, seg, y_ini)

        self._desenhar_eventos_pillow(ctx, dados_gantt.eventos, tarefas_eixo_y)
        self._desenhar_faixa_off_pillow(ctx, dados_gantt.segmentos_cpus_desligadas)
        self._desenhar_legenda_pillow(ctx, dados_gantt.resumo_cpus_desligadas)

        img.convert("RGB").save(caminho_arquivo)

    def _criar_contexto_pillow(self, dados_gantt: DadosGanttDTO) -> tuple[Image.Image, ContextoPillowGantt]:
        """Calcula as dimensões escalonadas e inicializa a imagem e o contexto de desenho Pillow."""
        escala = 2
        margem_esq = self.MARGEM_ESQ * escala
        margem_sup = self.MARGEM_SUP * escala
        largura_tick = self.LARGURA_TICK * escala
        altura_tarefa = self.ALTURA_TAREFA * escala
        passo_y = (self.ALTURA_TAREFA + self.ESPACO_TAREFA) * escala

        x_final_eixo = margem_esq + dados_gantt.max_tick * largura_tick
        largura_img = max(x_final_eixo + (80 * escala), 980 * escala)
        y_eixo_x = margem_sup + len(dados_gantt.tarefas_eixo_y) * passo_y
        y_faixa_off = y_eixo_x + (self.ALTURA_EIXO_X + 10) * escala
        y_legenda = y_faixa_off + (self.ALTURA_FAIXA_OFF + 8) * escala
        altura_img = y_legenda + (self.ALTURA_LEGENDA + 20) * escala

        img = Image.new("RGBA", (largura_img, altura_img), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)

        try:
            fonte_rotulo = ImageFont.truetype("arial.ttf", 10 * escala)
            fonte_tick = ImageFont.truetype("arial.ttf", 8 * escala)
        except Exception:
            fonte_rotulo = ImageFont.load_default()
            fonte_tick = ImageFont.load_default()

        ctx = ContextoPillowGantt(
            draw=draw,
            escala=escala,
            margem_esq=margem_esq,
            margem_sup=margem_sup,
            largura_tick=largura_tick,
            altura_tarefa=altura_tarefa,
            passo_y=passo_y,
            y_eixo_x=y_eixo_x,
            y_faixa_off=y_faixa_off,
            y_legenda=y_legenda,
            x_final_eixo=x_final_eixo,
            fonte_rotulo=fonte_rotulo,
            fonte_tick=fonte_tick,
        )
        return img, ctx

    def _desenhar_eixos_pillow(self, ctx: ContextoPillowGantt, tarefas_eixo_y: List[int], max_tick: int) -> None:
        """Desenha os eixos X e Y e as linhas de grade verticais na imagem Pillow."""
        e = ctx.escala
        for i, id_t in enumerate(tarefas_eixo_y):
            y = ctx.margem_sup + i * ctx.passo_y
            ctx.draw.text(
                (ctx.margem_esq - 30 * e, y + ctx.altura_tarefa // 4), f"T{id_t}", fill="black", font=ctx.fonte_rotulo
            )

        ctx.draw.line([(ctx.margem_esq, ctx.margem_sup - 6 * e), (ctx.margem_esq, ctx.y_eixo_x)], fill="#222222", width=2 * e)
        ctx.draw.line([(ctx.margem_esq, ctx.y_eixo_x), (ctx.x_final_eixo, ctx.y_eixo_x)], fill="#222222", width=2 * e)

        for tck in range(0, max_tick + 1):
            x = ctx.margem_esq + tck * ctx.largura_tick
            if tck > 0:
                ctx.draw.line([(x, ctx.margem_sup - 4 * e), (x, ctx.y_eixo_x)], fill="#d4d4d4", width=1)
            ctx.draw.line([(x, ctx.y_eixo_x), (x, ctx.y_eixo_x + 5 * e)], fill="#222222", width=2 * e)
            ctx.draw.text((x - 4 * e, ctx.y_eixo_x + 8 * e), str(tck), fill="black", font=ctx.fonte_tick)

    def _desenhar_segmento_pillow(self, ctx: ContextoPillowGantt, seg: SegmentoGanttDTO, y_ini: int) -> None:
        """Desenha um bloco retangular de tarefa na imagem Pillow usando o ContextoPillowGantt."""
        e = ctx.escala
        y_fim = y_ini + ctx.altura_tarefa
        x_ini = ctx.margem_esq + seg.tick_inicio * ctx.largura_tick
        x_fim = ctx.margem_esq + seg.tick_fim * ctx.largura_tick

        ctx.draw.rectangle(
            [x_ini, y_ini, x_fim, y_fim],
            fill=seg.cor_preenchimento,
            outline=seg.cor_borda,
            width=seg.largura_borda * e,
        )

        if seg.pontilhado:
            for px in range(int(x_ini) + 3 * e, int(x_fim) - 1, 6 * e):
                for py in range(int(y_ini) + 3 * e, int(y_fim) - 1, 6 * e):
                    ctx.draw.ellipse([px, py, px + 2 * e, py + 2 * e], fill="black")

        if seg.texto:
            ctx.draw.text(
                ((x_ini + x_fim) / 2 - 7 * e, (y_ini + y_fim) / 2 - 5 * e),
                seg.texto,
                fill=seg.cor_texto,
                font=ctx.fonte_tick,
            )

    def _desenhar_eventos_pillow(
        self,
        ctx: ContextoPillowGantt,
        eventos: List[MarcadorEventoGanttDTO],
        tarefas_eixo_y: List[int],
    ) -> None:
        """Itera pelos marcadores de eventos e desenha cada ícone na imagem Pillow."""
        for ev in eventos:
            if ev.id_tarefa in tarefas_eixo_y:
                y_topo = ctx.margem_sup + tarefas_eixo_y.index(ev.id_tarefa) * ctx.passo_y
                x = ctx.margem_esq + ev.tick * ctx.largura_tick
                self._desenhar_marcador_evento_pillow(ctx, ev.tipo, x, y_topo)

    def _desenhar_marcador_evento_pillow(self, ctx: ContextoPillowGantt, tipo: str, x: int, y_topo: int) -> None:
        """Desenha um marcador individual (INGRESSO, TERMINO, DEADLINE ou SORTEIO) via Pillow."""
        e = ctx.escala
        y_base = y_topo + ctx.altura_tarefa
        if tipo == "INGRESSO":
            ctx.draw.line([(x, y_topo - 10 * e), (x, y_topo)], fill="#1E8449", width=2 * e)
            ctx.draw.polygon([(x - 4 * e, y_topo - 5 * e), (x + 4 * e, y_topo - 5 * e), (x, y_topo)], fill="#1E8449")
        elif tipo == "TERMINO":
            ctx.draw.line([(x, y_base), (x, y_base + 10 * e)], fill="#1F618D", width=2 * e)
            ctx.draw.polygon([(x - 4 * e, y_base + 5 * e), (x + 4 * e, y_base + 5 * e), (x, y_base)], fill="#1F618D")
        elif tipo == "DEADLINE":
            ctx.draw.polygon(
                [(x - 5 * e, y_topo - 11 * e), (x + 5 * e, y_topo - 11 * e), (x, y_topo - 2 * e)], fill="#C0392B"
            )
        elif tipo == "SORTEIO":
            cx, cy = x + 6 * e, y_topo + 7 * e
            ctx.draw.polygon([(cx, cy - 5 * e), (cx + 5 * e, cy), (cx, cy + 5 * e), (cx - 5 * e, cy)], fill="#F39C12")

    def _desenhar_faixa_off_pillow(self, ctx: ContextoPillowGantt, segmentos_off: List[SegmentoGanttDTO]) -> None:
        """Desenha a faixa compacta de colchetes CPU OFF na imagem Pillow."""
        e = ctx.escala
        y_off = ctx.y_faixa_off
        ctx.draw.text((ctx.margem_esq - 56 * e, y_off - 5 * e), "CPU OFF", fill="#616161", font=ctx.fonte_tick)

        for seg_off in segmentos_off:
            x_ini = ctx.margem_esq + seg_off.tick_inicio * ctx.largura_tick + 1 * e
            x_fim = ctx.margem_esq + seg_off.tick_fim * ctx.largura_tick - 1 * e
            if x_fim <= x_ini:
                continue
            ctx.draw.line([(x_ini, y_off), (x_fim, y_off)], fill="#7F8C8D", width=2 * e)
            ctx.draw.line([(x_ini, y_off - 4 * e), (x_ini, y_off + 4 * e)], fill="#7F8C8D", width=2 * e)
            ctx.draw.line([(x_fim, y_off - 4 * e), (x_fim, y_off + 4 * e)], fill="#7F8C8D", width=2 * e)
            if seg_off.texto:
                ctx.draw.text(
                    ((x_ini + x_fim) / 2, y_off - 8 * e), seg_off.texto, fill="#424949", font=ctx.fonte_tick, anchor="mm"
                )

    def _desenhar_legenda_pillow(self, ctx: ContextoPillowGantt, resumo_off: str) -> None:
        """Desenha a legenda de estados, eventos e o resumo de ociosidade na imagem Pillow."""
        e = ctx.escala
        y_leg = ctx.y_legenda
        ctx.draw.text((ctx.margem_esq, y_leg - 5 * e), "LEGENDA:", fill="black", font=ctx.fonte_tick)

        cur_x = ctx.margem_esq + 72 * e
        for item in self.ITENS_LEGENDA_ESTADOS:
            self._desenhar_item_legenda_estado_pillow(ctx, cur_x, item)
            ctx.draw.text((cur_x + 24 * e, y_leg - 5 * e), item[0], fill="#222222", font=ctx.fonte_tick)
            cur_x += 178 * e

        y_leg_ev = y_leg + 22 * e
        ctx.draw.text((ctx.margem_esq, y_leg_ev - 5 * e), "EVENTOS:", fill="black", font=ctx.fonte_tick)
        cur_ev_x = ctx.margem_esq + 72 * e
        for tipo_ev, rotulo_ev in self.ITENS_LEGENDA_EVENTOS:
            self._desenhar_icone_legenda_evento_pillow(ctx, tipo_ev, cur_ev_x + 8 * e, y_leg_ev)
            ctx.draw.text((cur_ev_x + 22 * e, y_leg_ev - 5 * e), rotulo_ev, fill="#222222", font=ctx.fonte_tick)
            cur_ev_x += 178 * e

        if resumo_off:
            ctx.draw.text(
                (ctx.margem_esq, y_leg_ev + 18 * e),
                f"TEMPO DE CPUS DESLIGADAS:   {resumo_off}",
                fill="#333333",
                font=ctx.fonte_tick,
            )

    def _desenhar_item_legenda_estado_pillow(
        self,
        ctx: ContextoPillowGantt,
        cur_x: int,
        item_legenda: tuple[str, str, bool, bool],
    ) -> None:
        """Desenha o símbolo de um estado ou colchete na legenda da imagem Pillow."""
        _, cor_l, pont_l, col_l = item_legenda
        e = ctx.escala
        y_leg = ctx.y_legenda
        if col_l:
            ctx.draw.line([(cur_x, y_leg), (cur_x + 18 * e, y_leg)], fill="#7F8C8D", width=2 * e)
            ctx.draw.line([(cur_x, y_leg - 4 * e), (cur_x, y_leg + 4 * e)], fill="#7F8C8D", width=2 * e)
            ctx.draw.line([(cur_x + 18 * e, y_leg - 4 * e), (cur_x + 18 * e, y_leg + 4 * e)], fill="#7F8C8D", width=2 * e)
            return

        ctx.draw.rectangle([cur_x, y_leg - 6 * e, cur_x + 16 * e, y_leg + 6 * e], fill=cor_l, outline="black", width=e)
        if pont_l:
            for px in range(cur_x + 3 * e, cur_x + 15 * e, 4 * e):
                for py in range(y_leg - 3 * e, y_leg + 5 * e, 4 * e):
                    ctx.draw.ellipse([px, py, px + 2 * e, py + 2 * e], fill="black")

    def _desenhar_icone_legenda_evento_pillow(
        self,
        ctx: ContextoPillowGantt,
        tipo_ev: str,
        cx: int,
        y_leg_ev: int,
    ) -> None:
        """Desenha um ícone de evento na legenda da imagem Pillow."""
        e = ctx.escala
        if tipo_ev == "INGRESSO":
            ctx.draw.line([(cx, y_leg_ev - 6 * e), (cx, y_leg_ev + 5 * e)], fill="#1E8449", width=2 * e)
            ctx.draw.polygon([(cx - 4 * e, y_leg_ev), (cx + 4 * e, y_leg_ev), (cx, y_leg_ev + 6 * e)], fill="#1E8449")
        elif tipo_ev == "TERMINO":
            ctx.draw.line([(cx, y_leg_ev + 6 * e), (cx, y_leg_ev - 5 * e)], fill="#1F618D", width=2 * e)
            ctx.draw.polygon([(cx - 4 * e, y_leg_ev), (cx + 4 * e, y_leg_ev), (cx, y_leg_ev - 6 * e)], fill="#1F618D")
        elif tipo_ev == "DEADLINE":
            ctx.draw.polygon(
                [(cx - 5 * e, y_leg_ev - 2 * e), (cx + 5 * e, y_leg_ev - 2 * e), (cx, y_leg_ev + 6 * e)],
                fill="#C0392B",
            )
            ctx.draw.text((cx, y_leg_ev - 6 * e), "!", fill="#C0392B", font=ctx.fonte_tick, anchor="mm")
        elif tipo_ev == "SORTEIO":
            ctx.draw.polygon(
                [(cx, y_leg_ev - 5 * e), (cx + 5 * e, y_leg_ev), (cx, y_leg_ev + 5 * e), (cx - 5 * e, y_leg_ev)],
                fill="#F39C12",
            )
