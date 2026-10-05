# Simulador de Sistema Operacional Multitarefa

Este projeto é um simulador funcional e visual de um Sistema Operacional Multitarefa preemptivo de tempo compartilhado. Ele permite simular a execução de tarefas periódicas através de algoritmos baseados em prioridade: **Rate Monotonic (RM)** e **Earliest Deadline First (EDF)**.

A aplicação conta com um "debugger temporal" (*Time Travel*), no qual você pode avançar ou retroceder (*ticks*) livremente, e observar a geração do Gráfico de Gantt em tempo real usando uma interface moderna baseada em `CustomTkinter`.

---

## 📋 Pré-requisitos

O sistema foi desenvolvido de maneira enxuta em Python puro (3.12+), com foco em evitar configurações globais complexas. Para rodar a partir do código-fonte ou compilar, você precisa do Python instalado e das seguintes bibliotecas:

* `customtkinter` (Interface Gráfica)
* `pillow` (Exportação e manipulação de imagens)
* `pyinstaller` (Empacotamento)

## 🚀 Como Rodar o Projeto pelo Código-Fonte (Modo Desenvolvedor)

1. Abra o terminal na pasta raiz do projeto.
2. Instale as dependências (caso não possua):
   ```bash
   pip install customtkinter pillow
   ```
3. Inicie o simulador rodando o ponto de entrada principal:
   ```bash
   python src/principal.py
   ```

### 📁 Estrutura do Projeto (Clean OOP)
```text
📦 simulador-sistema-operacional-multitarefa
 ┣ 📂 src
 ┃ ┣ 📂 core/          # Componentes reais de SO (Hardware, Kernel, TCB)
 ┃ ┣ 📂 gui/           # Visão burra (CustomTkinter + Renderizador Pillow)
 ┃ ┣ 📜 principal.py   # Main
 ┃ ┗ 📜 simulador.py   # Controller I/O e Memento (Time-Travel)
 ┣ 📜 compilar_windows.bat
 ┣ 📜 documentacao.md
 ┗ 📜 README.md
```

## 📦 Como Compilar o Executável (.exe) para Usuário Final

Um dos objetivos do projeto é que o usuário possa rodá-lo sem instalar o Python. Para gerar um arquivo `.exe` isolado (*standalone*) no Windows 11:

### Método 1: Pelo Script Automático
Basta dar dois cliques no arquivo `compilar_windows.bat` localizado na raiz do projeto. Ele executará o processo automaticamente.

### Método 2: Pelo Terminal
Se preferir compilar manualmente pelo terminal (Powershell ou CMD), digite:
```bash
pyinstaller --onefile --windowed src/principal.py
```

### Onde encontro o arquivo compilado?
Após o processo terminar, uma nova pasta chamada `dist/` será criada na raiz do projeto. O seu executável estará lá dentro com o nome `principal.exe`. Você pode movê-lo e executá-lo de qualquer lugar.

---

## ⚙️ Formato do Arquivo de Configuração

O simulador espera um arquivo simples em `.txt` com os dados das tarefas, separado por ponto e vírgula (`;`). Os espaços não importam e letras maiúsculas/minúsculas são ignoradas na leitura. 

**Primeira Linha (Sistema):**
`algoritmo_escalonamento ; quantum ; qtde_cpus`

**Linhas Subsequentes (Tarefas):**
`id ; cor_hexadecimal ; instante_ingresso ; duracao ; periodo ; prazo_deadline ; lista_eventos`

**Exemplo Prático (EDF com 1 CPU):**
```text
edf;0;1
1;FF0000;0;10;20;20;
2;00FF00;0;25;50;50;
```
*(As tarefas aperiódicas, com período 0, são sumariamente informadas mas descartadas em prol da estabilidade desta versão).*
