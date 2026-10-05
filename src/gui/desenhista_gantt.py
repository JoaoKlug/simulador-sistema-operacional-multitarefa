from PIL import ImageGrab, Image
import customtkinter as ctk
from PIL import ImageDraw, ImageFont
from core.sistema_operacional import SistemaOperacional
from core.tarefas import EstadoTarefa

def desenhar_gantt(canvas: ctk.CTkCanvas, historico_estados: list[SistemaOperacional], formatador_visual):
    """
    Desenha o Gráfico de Gantt baseado no histórico de estados.
    Usa o formatador_visual injetado pelo Presenter para não acoplar lógica condicional.
    """
    canvas.delete("all")
    if not historico_estados:
        return

    # Encontrar todas as tarefas que já existiram para definir eixo Y
    todas_tarefas_ids = set()
    max_tick = 0
    for est in historico_estados:
        max_tick = max(max_tick, est.tick_atual)
        for t in est.tarefas:
            todas_tarefas_ids.add(t.id_tarefa)

    ids_ordenados = sorted(list(todas_tarefas_ids), reverse=True) # Decrescente (menor ID mais embaixo)
    
    # Configurações visuais
    margem_esq = 50
    margem_sup = 30
    largura_tick = 20
    altura_tarefa = 30
    espaco_tarefa = 10
    
    # Desenhar Eixo Y (Rótulos)
    for i, id_t in enumerate(ids_ordenados):
        y = margem_sup + i * (altura_tarefa + espaco_tarefa)
        canvas.create_text(margem_esq - 10, y + altura_tarefa/2, text=f"T{id_t}", anchor="e", font=("Arial", 10, "bold"))

    # Desenhar Eixo X (Ticks)
    for tck in range(0, max_tick + 2):
        x = margem_esq + tck * largura_tick
        canvas.create_line(x, margem_sup, x, margem_sup + len(ids_ordenados) * (altura_tarefa + espaco_tarefa), fill="#d3d3d3", dash=(2, 2))
        canvas.create_text(x, margem_sup - 10, text=str(tck), font=("Arial", 8))

    # Desenhar Blocos de Execução (agrupando ticks contínuos)
    for id_t in ids_ordenados:
        idx_y = ids_ordenados.index(id_t)
        y_inicio = margem_sup + idx_y * (altura_tarefa + espaco_tarefa)
        y_fim = y_inicio + altura_tarefa
        
        # Encontrar segmentos contínuos para a tarefa
        tick_inicio_segmento = None
        estado_atual_segmento = None
        cor_atual = ""
        cpu_atual = None
        sofreu_atraso_atual = False
        
        def desenhar_segmento(t_inicio, t_fim, estado, cor, cpu, sofreu_atraso):
            estilo = formatador_visual(estado.name, cor, sofreu_atraso, cpu, False)
            if estilo is None:
                return # Não desenha nada
                
            x_ini = margem_esq + (t_inicio - 1) * largura_tick
            x_f = margem_esq + t_fim * largura_tick
            
            fill_color = estilo["fill"]
            outline_color = estilo["outline"]
            width = estilo["width"]
                
            if fill_color is not None:
                canvas.create_rectangle(x_ini, y_inicio, x_f, y_fim, fill=fill_color, outline=outline_color, width=width)
                
            if estilo["text"]:
                meio_x = (x_ini + x_f) / 2
                canvas.create_text(meio_x, y_inicio + altura_tarefa/2, text=estilo["text"], fill=estilo["text_color"], font=("Arial", 8))

        # Varre do tick 1 até o max_tick
        for tick in range(1, max_tick + 1):
            est = historico_estados[tick]
            # Achar a tarefa neste tick
            t_obj = next((t for t in est.tarefas if t.id_tarefa == id_t), None)
            
            if not t_obj:
                # Se não existe, quebra o segmento
                if tick_inicio_segmento is not None:
                    desenhar_segmento(tick_inicio_segmento, tick - 1, estado_atual_segmento, cor_atual, cpu_atual, sofreu_atraso_atual)
                    tick_inicio_segmento = None
                continue
                
            # Verifica se continua o mesmo segmento
            mesmo_segmento = (
                tick_inicio_segmento is not None and
                estado_atual_segmento == t_obj.estado and
                cpu_atual == t_obj.id_cpu_alocada and
                sofreu_atraso_atual == t_obj.sofreu_atraso
            )
            
            if mesmo_segmento:
                continue # Apenas deixa o tick avançar para esticar a barra
            else:
                # Mudou o estado ou cpu, desenha o anterior e inicia novo
                if tick_inicio_segmento is not None:
                    desenhar_segmento(tick_inicio_segmento, tick - 1, estado_atual_segmento, cor_atual, cpu_atual, sofreu_atraso_atual)
                
                tick_inicio_segmento = tick
                estado_atual_segmento = t_obj.estado
                cor_atual = t_obj.cor_hex
                cpu_atual = t_obj.id_cpu_alocada
                sofreu_atraso_atual = t_obj.sofreu_atraso
                
        # Desenha o último segmento pendente
        if tick_inicio_segmento is not None:
            desenhar_segmento(tick_inicio_segmento, max_tick, estado_atual_segmento, cor_atual, cpu_atual, sofreu_atraso_atual)
            
    # Auto-ajuste da área de rolagem baseada no que foi desenhado
    bbox = canvas.bbox("all")
    if bbox:
        # Dar um respiro (margem) de 50px no final
        canvas.configure(scrollregion=(0, 0, bbox[2] + 50, bbox[3] + 50))
                
from PIL import ImageDraw, ImageFont

def exportar_imagem(historico_estados: list[SistemaOperacional], nome_arquivo: str, formatador_visual):
    """
    Salva o conteúdo gráfico em um PNG gerando a imagem na memória com Pillow,
    resolvendo dependências de Ghostscript e limitação de tela.
    Usa o formatador_visual injetado pelo Presenter.
    """
    if not historico_estados:
        return

    todas_tarefas_ids = set()
    max_tick = 0
    for est in historico_estados:
        max_tick = max(max_tick, est.tick_atual)
        for t in est.tarefas:
            todas_tarefas_ids.add(t.id_tarefa)

    ids_ordenados = sorted(list(todas_tarefas_ids), reverse=True)
    
    margem_esq = 50
    margem_sup = 30
    largura_tick = 20
    altura_tarefa = 30
    espaco_tarefa = 10
    
    img_width = margem_esq + (max_tick + 2) * largura_tick
    img_height = margem_sup + len(ids_ordenados) * (altura_tarefa + espaco_tarefa) + 50
    
    img = Image.new("RGB", (img_width, img_height), "white")
    draw = ImageDraw.Draw(img)
    
    # Eixo Y
    for i, id_t in enumerate(ids_ordenados):
        y = margem_sup + i * (altura_tarefa + espaco_tarefa)
        draw.text((10, y + 10), f"T{id_t}", fill="black")

    # Eixo X
    for tck in range(0, max_tick + 2):
        x = margem_esq + tck * largura_tick
        draw.line([(x, margem_sup), (x, img_height - 50)], fill="#d3d3d3", width=1)
        draw.text((x - 5, margem_sup - 20), str(tck), fill="black")

    # Segmentos
    for id_t in ids_ordenados:
        idx_y = ids_ordenados.index(id_t)
        y_inicio = margem_sup + idx_y * (altura_tarefa + espaco_tarefa)
        y_fim = y_inicio + altura_tarefa
        
        tick_inicio_segmento = None
        estado_atual_segmento = None
        cor_atual = ""
        cpu_atual = None
        sofreu_atraso_atual = False
        
        def desenhar_segmento(t_inicio, t_fim, estado, cor, cpu, sofreu_atraso):
            estilo = formatador_visual(estado.name, cor, sofreu_atraso, cpu, True)
            if estilo is None:
                return
                
            x_ini = margem_esq + (t_inicio - 1) * largura_tick
            x_f = margem_esq + t_fim * largura_tick
            
            draw.rectangle([x_ini, y_inicio, x_f, y_fim], fill=estilo["fill"], outline=estilo["outline"], width=estilo["width"])
                
            if estilo["text"]:
                meio_x = (x_ini + x_f) / 2
                draw.text((meio_x - 5, y_inicio + 10), estilo["text"], fill=estilo["text_color"])

        for tick in range(1, max_tick + 1):
            est = historico_estados[tick]
            t_obj = next((t for t in est.tarefas if t.id_tarefa == id_t), None)
            
            if not t_obj:
                if tick_inicio_segmento is not None:
                    desenhar_segmento(tick_inicio_segmento, tick - 1, estado_atual_segmento, cor_atual, cpu_atual, sofreu_atraso_atual)
                    tick_inicio_segmento = None
                continue
                
            mesmo_segmento = (
                tick_inicio_segmento is not None and
                estado_atual_segmento == t_obj.estado and
                cpu_atual == t_obj.id_cpu_alocada and
                sofreu_atraso_atual == t_obj.sofreu_atraso
            )
            
            if mesmo_segmento:
                continue
            else:
                if tick_inicio_segmento is not None:
                    desenhar_segmento(tick_inicio_segmento, tick - 1, estado_atual_segmento, cor_atual, cpu_atual, sofreu_atraso_atual)
                
                tick_inicio_segmento = tick
                estado_atual_segmento = t_obj.estado
                cor_atual = t_obj.cor_hex
                cpu_atual = t_obj.id_cpu_alocada
                sofreu_atraso_atual = t_obj.sofreu_atraso
                
        if tick_inicio_segmento is not None:
            desenhar_segmento(tick_inicio_segmento, max_tick, estado_atual_segmento, cor_atual, cpu_atual, sofreu_atraso_atual)

    try:
        img.save(nome_arquivo, "PNG")
    except Exception as e:
        print(f"Erro ao exportar imagem nativa: {e}")
