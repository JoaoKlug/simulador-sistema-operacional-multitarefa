from PIL import ImageGrab, Image
import customtkinter as ctk
from modelos import EstadoSistema, EstadoTarefa

def desenhar_gantt(canvas: ctk.CTkCanvas, historico_estados: list[EstadoSistema]):
    """
    Desenha o Gráfico de Gantt baseado no histórico de estados.
    Eixo X: Ticks de tempo
    Eixo Y: Tarefas ordenadas por ID decrescente
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

    # Desenhar Blocos de Execução
    for est in historico_estados:
        tick = est.tick_atual
        if tick == 0:
            continue # Tick 0 é o estado inicial (antes de rodar)
            
        x_inicio = margem_esq + (tick - 1) * largura_tick
        x_fim = margem_esq + tick * largura_tick
        
        for t in est.tarefas:
            if t.id_tarefa in ids_ordenados:
                idx_y = ids_ordenados.index(t.id_tarefa)
                y_inicio = margem_sup + idx_y * (altura_tarefa + espaco_tarefa)
                y_fim = y_inicio + altura_tarefa
                
                # Cores baseadas no estado da tarefa NAQUELE tick
                cor_fill = ""
                stipple = ""
                outline = "black"
                
                if t.estado == EstadoTarefa.EXECUTANDO:
                    cor_fill = f"#{t.cor_hex}"
                elif t.estado == EstadoTarefa.SUSPENSA:
                    cor_fill = "black"
                    stipple = "gray50" # Tkinter canvas stipple pattern
                elif t.estado == EstadoTarefa.PRONTA:
                    cor_fill = "" # Ausencia de cor
                
                # Se sofreu atraso, destaca
                if t.sofreu_atraso:
                    outline = "red"
                
                if cor_fill or stipple or t.estado == EstadoTarefa.PRONTA:
                    if cor_fill:
                        # tk não suporta stipple bem com fill no windows, mas vamos simplificar
                        canvas.create_rectangle(x_inicio, y_inicio, x_fim, y_fim, fill=cor_fill, outline=outline, width=2 if t.sofreu_atraso else 1)
                    else:
                        # Apenas borda para PRONTA
                        canvas.create_rectangle(x_inicio, y_inicio, x_fim, y_fim, fill="", outline="black")

                # Indicar CPU se executando
                if t.estado == EstadoTarefa.EXECUTANDO and t.id_cpu_alocada is not None:
                    canvas.create_text(x_inicio + largura_tick/2, y_inicio + altura_tarefa/2, text=f"C{t.id_cpu_alocada}", fill="white" if cor_fill=="black" else "black", font=("Arial", 8))

                # Eventos de Início/Fim (setas ou ícones)
                # Se no tick anterior não existia ou estava FINALIZADA e agora PRONTA/NOVA
                # Simplificação: Desenhar setas com base na comparação com o estado anterior pode ser feito aqui ou na janela.
                
def exportar_imagem(canvas: ctk.CTkCanvas, nome_arquivo: str):
    """
    Salva o conteúdo visível do Canvas em um arquivo de imagem.
    Idealmente, usar Postscript e converter com Pillow.
    """
    try:
        # Tkinter canvas postscript export
        canvas.update()
        canvas.postscript(file=nome_arquivo + ".eps", colormode='color')
        img = Image.open(nome_arquivo + ".eps")
        img.save(nome_arquivo, "PNG")
        import os
        os.remove(nome_arquivo + ".eps")
    except Exception as e:
        print(f"Erro ao exportar imagem: {e}")
