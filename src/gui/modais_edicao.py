from typing import Callable, Dict, List, Tuple
import customtkinter as ctk
from tkinter import messagebox
from controlador.controlador_app import ControladorApp
from controlador.dtos import CardTCBDTO, DadosEdicaoTarefaDTO


class ModaisConfiguracao:
    """
    Construtor dos diálogos modais de configuração do sistema e de adição/edição de tarefas.
    Mantém o padrão 100% Passive View (Dummy GUI), repassando entradas como DTOs ao ControladorApp.
    """

    @classmethod
    def abrir_modal_sistema(
        cls,
        janela_pai: ctk.CTk,
        controlador: ControladorApp,
        ao_atualizar: Callable[[], None],
    ) -> None:
        """Abre modal para editar Escalonador, Quantum e Quantidade de Processadores."""
        cabecalho = controlador.obter_dados_cabecalho()
        modal, frame = cls._criar_janela_modal(
            janela_pai, "Editar Configuração do Sistema", "500x350", "Configurações do Sistema Operacional"
        )

        combo_algo = cls._criar_linha_combo(frame, "Escalonador:", ["RM", "EDF"], cabecalho.algoritmo_atual)
        entry_quantum = cls._criar_linha_entrada(frame, "Quantum:", str(cabecalho.quantum_atual))
        entry_cpus = cls._criar_linha_entrada(frame, "Processadores:", str(cabecalho.qtde_cpus_atual))

        def salvar_sistema() -> None:
            try:
                q = int(entry_quantum.get().strip())
                cpus = int(entry_cpus.get().strip())
                controlador.configurar_sistema(combo_algo.get(), q, cpus)
                ao_atualizar()
                modal.destroy()
            except Exception as e:
                messagebox.showerror("Erro de Configuração", str(e), parent=modal)

        ctk.CTkButton(
            frame,
            text="Salvar Configuração",
            height=40,
            fg_color="#2E86C1",
            font=("Arial", 13, "bold"),
            command=salvar_sistema,
        ).pack(fill="x", padx=14, pady=(22, 12))

    @classmethod
    def abrir_modal_adicionar_tarefa(
        cls,
        janela_pai: ctk.CTk,
        controlador: ControladorApp,
        ao_atualizar: Callable[[], None],
    ) -> None:
        """Abre modal para adicionar uma nova tarefa periódica."""
        cabecalho = controlador.obter_dados_cabecalho()
        modal, frame = cls._criar_janela_modal(
            janela_pai, "Adicionar Tarefa", "500x450", "Nova Tarefa Periódica"
        )

        especificacoes = [
            ("ID da Tarefa:", str(cabecalho.proximo_id_sugerido)),
            ("Cor Hexadecimal:", "2ECC71"),
            ("Ingresso:", "0"),
            ("Duração:", "2"),
            ("Período:", "8"),
            ("DeadLine Relativo:", "8"),
        ]
        entradas = cls._criar_multiplas_entradas(frame, especificacoes)

        def confirmar_nova_tarefa() -> None:
            try:
                dados = DadosEdicaoTarefaDTO(
                    id_tarefa=int(entradas["ID da Tarefa:"].get().strip()),
                    cor_hex=entradas["Cor Hexadecimal:"].get().strip(),
                    instante_ingresso=int(entradas["Ingresso:"].get().strip()),
                    duracao=int(entradas["Duração:"].get().strip()),
                    periodo=int(entradas["Período:"].get().strip()),
                    prazo_relativo=int(entradas["DeadLine Relativo:"].get().strip()),
                )
                controlador.adicionar_tarefa(dados)
                ao_atualizar()
                modal.destroy()
            except Exception as e:
                messagebox.showerror("Modificação Inválida", str(e), parent=modal)

        ctk.CTkButton(
            frame,
            text="Adicionar Tarefa",
            height=40,
            fg_color="#27AE60",
            font=("Arial", 13, "bold"),
            command=confirmar_nova_tarefa,
        ).pack(fill="x", padx=14, pady=(20, 12))

    @classmethod
    def abrir_modal_editar_tarefa(
        cls,
        janela_pai: ctk.CTk,
        controlador: ControladorApp,
        card: CardTCBDTO,
        ao_atualizar: Callable[[], None],
    ) -> None:
        """Abre modal para editar estado ou parâmetros temporais de uma tarefa existente."""
        modal, frame = cls._criar_janela_modal(
            janela_pai, f"Editar Tarefa {card.id_tarefa}", "500x500", f"Editar Tarefa {card.id_tarefa}"
        )

        estado_inicial = (
            "AGUARDANDO" if card.nome_estado.startswith("AGUARDANDO") else card.nome_estado
        )
        opcoes_estado = ["NOVA", "PRONTA", "EXECUTANDO", "SUSPENSA", "AGUARDANDO", "FINALIZADA"]
        combo_estado = cls._criar_linha_combo(frame, "Estado:", opcoes_estado, estado_inicial)

        especificacoes = [
            ("Cor Hexadecimal:", card.cor_hex),
            ("Ingresso:", str(card.instante_ingresso)),
            ("Duração:", str(card.duracao)),
            ("Período:", str(card.periodo)),
            ("DeadLine Relativo:", str(card.prazo_relativo)),
            ("Execução Atual:", str(card.tempo_ja_executado)),
        ]
        entradas = cls._criar_multiplas_entradas(frame, especificacoes)

        def aplicar_edicao() -> None:
            try:
                dados = DadosEdicaoTarefaDTO(
                    id_tarefa=card.id_tarefa,
                    novo_estado=combo_estado.get(),
                    cor_hex=entradas["Cor Hexadecimal:"].get().strip(),
                    instante_ingresso=int(entradas["Ingresso:"].get().strip()),
                    duracao=int(entradas["Duração:"].get().strip()),
                    periodo=int(entradas["Período:"].get().strip()),
                    prazo_relativo=int(entradas["DeadLine Relativo:"].get().strip()),
                    tempo_ja_executado=int(entradas["Execução Atual:"].get().strip()),
                )
                controlador.modificar_tarefa(dados)
                ao_atualizar()
                modal.destroy()
            except Exception as e:
                messagebox.showerror("Modificação Semanticamente Inválida", str(e), parent=modal)

        ctk.CTkButton(
            frame,
            text="Salvar Alterações",
            height=40,
            fg_color="#E67E22",
            font=("Arial", 13, "bold"),
            command=aplicar_edicao,
        ).pack(fill="x", padx=14, pady=(20, 12))

    @staticmethod
    def _criar_janela_modal(
        janela_pai: ctk.CTk,
        titulo_janela: str,
        geometria: str,
        titulo_interno: str,
    ) -> Tuple[ctk.CTkToplevel, ctk.CTkFrame]:
        """Cria a estrutura base padronizada e não redimensionável de um diálogo modal."""
        modal = ctk.CTkToplevel(janela_pai)
        modal.title(titulo_janela)
        modal.geometry(geometria)
        modal.resizable(False, False)
        modal.grab_set()

        frame = ctk.CTkFrame(modal)
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            frame,
            text=titulo_interno,
            font=("Arial", 15, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 12))
        return modal, frame

    @staticmethod
    def _criar_linha_entrada(container: ctk.CTkFrame, rotulo: str, valor_inicial: str) -> ctk.CTkEntry:
        """Adiciona uma linha horizontal com rótulo à esquerda e campo de texto à direita."""
        linha = ctk.CTkFrame(container, fg_color="transparent")
        linha.pack(fill="x", padx=14, pady=6)
        ctk.CTkLabel(linha, text=rotulo, width=210, anchor="w", font=("Arial", 12, "bold")).pack(side="left")
        entrada = ctk.CTkEntry(linha, height=32)
        entrada.insert(0, valor_inicial)
        entrada.pack(side="right", fill="x", expand=True)
        return entrada

    @staticmethod
    def _criar_linha_combo(
        container: ctk.CTkFrame,
        rotulo: str,
        opcoes: List[str],
        valor_inicial: str,
    ) -> ctk.CTkOptionMenu:
        """Adiciona uma linha horizontal com rótulo à esquerda e menu seletor à direita."""
        linha = ctk.CTkFrame(container, fg_color="transparent")
        linha.pack(fill="x", padx=14, pady=6)
        ctk.CTkLabel(linha, text=rotulo, width=210, anchor="w", font=("Arial", 12, "bold")).pack(side="left")
        combo = ctk.CTkOptionMenu(linha, values=opcoes, height=32)
        combo.set(valor_inicial)
        combo.pack(side="right", fill="x", expand=True)
        return combo

    @classmethod
    def _criar_multiplas_entradas(
        cls,
        container: ctk.CTkFrame,
        especificacoes: List[Tuple[str, str]],
    ) -> Dict[str, ctk.CTkEntry]:
        """Cria múltiplos campos rotulados em sequência e retorna o dicionário de entradas."""
        return {
            rotulo: cls._criar_linha_entrada(container, rotulo, valor_padrao)
            for rotulo, valor_padrao in especificacoes
        }

