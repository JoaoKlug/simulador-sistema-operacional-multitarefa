# Simulador de Sistema Operacional Multitarefa (Versão 0.6)

Simulador visual e interativo de um **Sistema Operacional Multitarefa Preemptivo de Tempo Compartilhado**, desenvolvido em **Python 3.12+ estritamente tipado** com interface gráfica em `CustomTkinter` e exportação completa de Gráficos de Gantt em alta resolução via `Pillow`.

O projeto implementa integralmente os requisitos do **Projeto A** especificados pelo **Prof. Dr. Marco Aurélio Wehrmeister** (`requisitos_funcionais.pdf`) e fundamenta toda a sua arquitetura nos conceitos clássicos do livro ***Sistemas Operacionais: Conceitos e Mecanismos*** do **Prof. Dr. Carlos Alberto Maziero** (`Sistemas Operacionais_ Conceitos e Mecanismos.pdf`).

> 📄 **Documentação Técnica Completa:** Para consultar o detalhamento de todos os requisitos funcionais, a fundamentação teórica capítulo a capítulo no livro do Prof. Maziero e a análise arquitetural das classes, consulte o arquivo `documentacao.md`.

---

## ✨ Principais Funcionalidades

* **Escalonadores Preemptivos de Tempo Real:**
  * **RM (*Rate Monotonic*):** Prioridade estática inversamente proporcional ao período da tarefa.
  * **EDF (*Earliest Deadline First*):** Prioridade dinâmica inversamente proporcional ao prazo absoluto (*deadline*) atual.
  * **5 Critérios Estritos de Desempate:** Continuidade na CPU, menor prazo, menor instante de ingresso, menor duração e sorteio (com indicador gráfico $\diamond$ no Gantt).
* **Hardware Físico com Temporizador, IVT e Interrupção (IRQ 0):**
  * A classe `Hardware` agrega os processadores (`CPU` $1 \dots N$) e o relógio físico, mantendo o registro da rotina de tratamento na Tabela de Interrupções (IVT) e disparando autonomamente a interrupção de *tick* (`gerar_interrupcao_tick`) para o `Kernel`.
  * Minimização de ociosidade com fila global de prontos, execução de ciclo de instrução pela própria `CPU` (`executar_ciclo`), desligamento automático de CPUs sem tarefas (`registrar_ociosidade`) e exibição do tempo desligado no Gráfico de Gantt (`CPU OFF`).
* **Modo *Debugger* (*Time-Travel*), Sidebar Direita `"Logs"` e Edição em Tempo Real:**
  * Avance e retroceda *ticks* livremente (Padrão *Memento*).
  * **Sidebar retrátil `"Logs"` à direita:** Exibe em ordem cronológica as chamadas das funções-chave de `src/core/` (`Hardware.gerar_interrupcao_tick`, `Kernel.tratar_interrupcao_relogio`, `GerenciadorTarefas.preparar_inicio_intervalo`, `Escalonador.eleger`, `Despachante.despachar` com `salvar_contexto`/`restaurar_contexto`, `CPU.executar_ciclo` e `GerenciadorTarefas.concluir_intervalo_tick`).
  * Modifique manualmente o **estado** (`NOVA`, `PRONTA`, `EXECUTANDO`, `SUSPENSA`, `AGUARDANDO`, `FINALIZADA`) ou os **parâmetros** de qualquer tarefa em qualquer passo da simulação, com validação semântica e mensagens claras de erro.
* **Gráfico de Gantt Completo, Barra Inferior de TCBs e Exportação PNG:**
  * O Gráfico de Gantt e a barra horizontal de cartões TCB ficam à esquerda, acompanhados pela sidebar retrátil **"Logs"** à direita.
  * Representação de tarefas em execução (cor sólida + CPU), prontas (branco/vazado), suspensas (preto pontilhado), marcadores exatos de ingresso ($\downarrow$), término ($\uparrow$), perda de *deadline* (`!`), sorteio ($\diamond$) e legenda integrada.
  * Exportação de toda a simulação em imagem `.png` de alta resolução via `Pillow`.

---

## 📁 Estrutura do Projeto

```text
simulador-sistema-operacional-multitarefa/
├── src/
│   ├── principal.py                        # Ponto de entrada da aplicação
│   ├── core/                               # Subsistema de S.O. e Hardware (Maziero)
│   │   ├── hardware/
│   │   │   ├── cpu.py                      # Unidade de processamento e contagem de ociosidade
│   │   │   └── hardware.py                 # Hardware físico (CPUs + Relógio + Geração de IRQ de Tick)
│   │   ├── processos/
│   │   │   └── estado_tarefa.py            # Enum EstadoTarefa (NOVA, PRONTA, EXECUTANDO, SUSPENSA, AGUARDANDO, FINALIZADA)
│   │   ├── kernel/
│   │   │   ├── tcb.py                      # @dataclass TCB unificada (Req. 1.3) e ParametrosTarefa
│   │   │   ├── escalonador.py              # Políticas RM e EDF + 5 regras de desempate e sorteio
│   │   │   ├── gerenciador_tarefas.py      # Ciclo de vida, períodos, durações e deadlines
│   │   │   ├── despachante.py              # Mecanismo de troca de contexto nas CPUs
│   │   │   └── kernel.py                   # Núcleo Monolítico (tratador da IRQ do relógio)
│   │   └── sistema_operacional.py          # Fachada principal e validação semântica de edições
│   ├── simulador/                          # Motor de Simulação e Time-Travel
│   │   ├── leitor_configuracao.py          # Parser e validador tolerante de arquivos .txt
│   │   ├── gerenciador_historico.py        # Pilhas de snapshots (Padrão Memento)
│   │   └── simulador.py                    # Orquestrador temporal e de edições em tempo real
│   ├── controlador/                        # Camada Presenter / Controller (MVP)
│   │   ├── dtos.py                         # Contratos @dataclass(frozen=True) fortemente tipados
│   │   └── controlador_app.py              # Conversão do domínio em DTOs para a GUI
│   └── gui/                                # Camada Visual 100% Dummy (Passive View)
│       ├── janela_app.py                   # Orquestrador da janela principal e barra de TCBs
│       ├── painel_logs.py                  # Sidebar direita retrátil 'Logs' (funções do core)
│       ├── modais_edicao.py                # Diálogos modais de configuração do sistema e tarefas
│       ├── utilitarios_gui.py              # Fábrica de ícones vetoriais e gerenciador de tooltips
│       └── desenhista_gantt.py             # Renderizador Canvas (tela) e Pillow (exportação PNG)
├── exemplos/                               # Arquivos .txt de exemplo (RM e EDF)
├── requisitos.txt                          # Dependências do projeto Python
├── compilar_windows.bat                    # Script de geração do executável standalone (.exe)
├── documentacao.md                         # Documentação técnica, requisitos e análise arquitetural
└── README.md                               # Guia rápido do repositório
```

---

## 🚀 Como Executar pelo Código-Fonte (Modo Desenvolvedor)

1. Instale as dependências no seu ambiente Python 3.12+:
   ```bash
   pip install -r requisitos.txt
   ```
2. Inicie o simulador:
   ```bash
   python src/principal.py
   ```

---

## 📦 Como Compilar o Executável Standalone (`.exe`)

Execute o script `compilar_windows.bat` ou rode manualmente no terminal:
```bash
pyinstaller --onefile --windowed src/principal.py
```
O executável independente será gerado na pasta `dist/principal.exe`.

---

## ⚙️ Formato do Arquivo de Configuração (`.txt`)

```text
algoritmo_escalonamento;quantum;qtde_cpus
id;cor_hex;ingresso;duracao;periodo;prazo;lista_eventos
```

**Exemplo (`exemplos/teste_basico_edf.txt`):**
```text
edf;0;1
1;FF0000;0;10;20;20;
2;00FF00;0;25;50;50;
```
