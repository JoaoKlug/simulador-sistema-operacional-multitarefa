import customtkinter as ctk
from tkinter import filedialog, messagebox
from simulador import Simulador
from core.tarefas import EstadoTarefa
from gui.desenhista_gantt import desenhar_gantt, exportar_imagem

class JanelaApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Simulador de SO Multitarefa")
        self.geometry("1000x600")
        
        self.simulador = Simulador()
        
        self.setup_ui()
        
    def setup_ui(self):
        # Frame de Controles
        self.frame_controles = ctk.CTkFrame(self, height=100)
        self.frame_controles.pack(side="top", fill="x", padx=10, pady=10)
        
        self.btn_carregar = ctk.CTkButton(self.frame_controles, text="Carregar Arquivo", command=self.carregar_arquivo)
        self.btn_carregar.pack(side="left", padx=5)
        
        self.btn_avancar = ctk.CTkButton(self.frame_controles, text="Avancar Tick (->)", command=self.avancar, state="disabled")
        self.btn_avancar.pack(side="left", padx=5)

        self.btn_retroceder = ctk.CTkButton(self.frame_controles, text="Retroceder Tick (<-)", command=self.retroceder, state="disabled")
        self.btn_retroceder.pack(side="left", padx=5)
        
        self.btn_exec_completa = ctk.CTkButton(self.frame_controles, text="Execução Completa", command=self.executar_completo, state="disabled")
        self.btn_exec_completa.pack(side="left", padx=5)
        
        self.btn_exportar = ctk.CTkButton(self.frame_controles, text="Exportar Imagem", command=self.exportar)
        self.btn_exportar.pack(side="left", padx=5)

        # Informações
        self.lbl_info = ctk.CTkLabel(self.frame_controles, text="Tick: 0 | CPU: - | Algo: -")
        self.lbl_info.pack(side="right", padx=10)

        # Frame de Conteúdo Principal (Dividido entre Gráfico e TCB)
        self.frame_conteudo = ctk.CTkFrame(self)
        self.frame_conteudo.pack(side="bottom", fill="both", expand=True, padx=10, pady=10)
        
        # Barra lateral (Sidebar) para TCB
        self.frame_tcb = ctk.CTkScrollableFrame(self.frame_conteudo, width=250, label_text="TCBs das Tarefas")
        self.frame_tcb.pack(side="right", fill="y", padx=(10, 0))
        
        self.labels_tcb = {} # Dicionário para guardar as referências dos cards de tarefas

        # Frame do Gráfico (Ocupa o resto do espaço à esquerda)
        self.frame_grafico = ctk.CTkFrame(self.frame_conteudo)
        self.frame_grafico.pack(side="left", fill="both", expand=True)
        
        self.canvas = ctk.CTkCanvas(self.frame_grafico, bg="#f5f5f5")
        self.scroll_x = ctk.CTkScrollbar(self.frame_grafico, orientation="horizontal", command=self.canvas.xview)
        self.scroll_y = ctk.CTkScrollbar(self.frame_grafico, orientation="vertical", command=self.canvas.yview)
        
        self.canvas.configure(xscrollcommand=self.scroll_x.set, yscrollcommand=self.scroll_y.set)
        
        self.scroll_y.pack(side="right", fill="y")
        self.scroll_x.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

    def carregar_arquivo(self):
        caminho = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not caminho:
            return
            
        try:
            self.simulador.carregar_arquivo(caminho)
            self.atualizar_interface()
        except Exception as e:
            messagebox.showerror("Erro ao carregar", str(e))

    def avancar(self):
        self.simulador.avancar_tick()
        self.atualizar_interface()

    def retroceder(self):
        if self.simulador.retroceder_tick():
            self.atualizar_interface()

    def executar_completo(self):
        sucesso = self.simulador.executar_completo()
        if not sucesso:
            messagebox.showwarning("Limite", "Limite de simulação excedido (possível loop infinito).")
        self.atualizar_interface()

    def atualizar_interface(self):
        est = self.simulador.so_atual
        if est:
            print(f"[GUI] Atualizando interface para Tick {est.tick_atual}. Qtde Tarefas: {len(est.tarefas)}")
            self.lbl_info.configure(text=f"Tick: {est.tick_atual} | Algo: {est.nome_algoritmo.upper()} | CPUs: {est.qtde_cpus}")
            
            # Controle de botões baseado nos estados da simulação
            pode_retroceder = len(self.simulador.historico.pilha_passado) > 0
            finalizou = est.finalizado()
            
            self.btn_retroceder.configure(state="normal" if pode_retroceder else "disabled")
            self.btn_avancar.configure(state="disabled" if finalizou else "normal")
            self.btn_exec_completa.configure(state="disabled" if finalizou else "normal")
            
            # Passa a lista completa de histórico para desenhar o fluxo de tempo até agora
            todos_estados = self.simulador.historico.pilha_passado + [est]
            desenhar_gantt(self.canvas, todos_estados, self.simulador.obter_estilo_segmento_gantt)
            
            # Atualizar Barra Lateral de TCBs
            self._atualizar_sidebar_tcb(est.tarefas)
            
    def _atualizar_sidebar_tcb(self, tarefas):
        # Limpar widgets antigos
        for widget in self.frame_tcb.winfo_children():
            widget.destroy()
            
        for t in tarefas:
            cor_indicador = self.simulador.obter_cor_cartao_tcb(t)
            card = ctk.CTkFrame(self.frame_tcb, fg_color=("gray85", "gray25"))
            card.pack(fill="x", pady=5, padx=5)
            
            titulo = self.simulador.obter_titulo_cartao_tcb(t)
                
            lbl_title = ctk.CTkLabel(card, text=titulo, font=("Arial", 12, "bold"))
            lbl_title.pack(anchor="w", padx=5, pady=(5, 0))
            
            # Linha de estado com corzinha
            frame_estado = ctk.CTkFrame(card, fg_color="transparent")
            frame_estado.pack(fill="x", padx=5)
            indicador = ctk.CTkFrame(frame_estado, width=10, height=10, fg_color=cor_indicador, border_color="black", border_width=1)
            indicador.pack(side="left", padx=(0, 5))
            ctk.CTkLabel(frame_estado, text=f"Estado: {t.estado.value}", font=("Arial", 11)).pack(side="left")
            
            # Textos
            info = f"Progresso: {t.tempo_ja_executado}/{t.duracao_original} ticks\n"
            info += f"Período: {t.periodo} | Prazo: {t.prazo_relativo}\n"
            info += f"Prazo Absoluto: {t.prazo_absoluto_atual}"
            if t.sofreu_atraso:
                info += " (ATRASADA!)"
                
            lbl_info = ctk.CTkLabel(card, text=info, font=("Arial", 11), justify="left")
            lbl_info.pack(anchor="w", padx=5, pady=(0, 5))
            
    def exportar(self):
        caminho = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if caminho:
            est = self.simulador.so_atual
            if not est: return
            todos_estados = self.simulador.historico.pilha_passado + [est]
            exportar_imagem(todos_estados, caminho, self.simulador.obter_estilo_segmento_gantt)
            messagebox.showinfo("Sucesso", "Imagem exportada com sucesso em alta resolução.")
