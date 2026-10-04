import sys
import os

# Adiciona o diretório src ao path do Python para facilitar imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.janela_app import JanelaApp

if __name__ == "__main__":
    app = JanelaApp()
    app.mainloop()
