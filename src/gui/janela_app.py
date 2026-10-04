import customtkinter as ctk
from tkinter import filedialog, messagebox
from leitor_arquivo import ler_estado_inicial
from modelos import EstadoSistema, Processador, EstadoTarefa
from historico import GerenciadorHistorico
from escalonador import obter_escalonador
from simulacao import avancar_um_tick, executar_simulacao_completa
from gui.desenhista_gantt import desenhar_gantt, exportar_imagem
class JanelaApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Simulador de SO Multitarefa")
        self.geometry("1000x600")
        
        self.historico = GerenciadorHistorico()
        self.escalonador = None
        
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

        # Frame do Gráfico
        self.frame_grafico = ctk.CTkFrame(self)
        self.frame_grafico.pack(side="bottom", fill="both", expand=True, padx=10, pady=10)
        
        self.canvas = ctk.CTkCanvas(self.frame_grafico, bg="white", scrollregion=(0,0,2000,1000))
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
            estado_inicial = ler_estado_inicial(caminho)
            self.historico.iniciar(estado_inicial)
            self.escalonador = obter_escalonador(estado_inicial.nome_algoritmo)
            
            self.btn_avancar.configure(state="normal")
            self.btn_exec_completa.configure(state="normal")
            self.atualizar_interface()
            
        except Exception as e:
            messagebox.showerror("Erro ao carregar", str(e))

    def avancar(self):
        if not self.historico.estado_atual: return
        
        # Tenta pegar do futuro (time travel)
        if not self.historico.avancar_do_historico():
            # Senão, calcula novo tick
            novo_est = avancar_um_tick(self.historico.estado_atual, self.escalonador)
            self.historico.avancar(novo_est)
            
        self.atualizar_interface()

    def retroceder(self):
        if self.historico.retroceder():
            self.atualizar_interface()

    def executar_completo(self):
        if not self.historico.estado_atual: return
        
        sucesso = executar_simulacao_completa(self.historico, self.escalonador)
        
        if not sucesso:
            messagebox.showwarning("Limite", "Limite de simulação excedido (possível loop infinito).")
            
        self.atualizar_interface()

    def atualizar_interface(self):
        est = self.historico.estado_atual
        if est:
            self.lbl_info.configure(text=f"Tick: {est.tick_atual} | Algo: {est.nome_algoritmo.upper()} | CPUs: {est.qtde_cpus}")
            self.btn_retroceder.configure(state="normal" if len(self.historico.pilha_passado) > 0 else "disabled")
            
            # Passa a lista completa de histórico para desenhar o fluxo de tempo até agora
            todos_estados = self.historico.pilha_passado + [est]
            desenhar_gantt(self.canvas, todos_estados)
            
    def exportar(self):
        caminho = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if caminho:
            exportar_imagem(self.canvas, caminho)
            messagebox.showinfo("Sucesso", "Imagem exportada.")
