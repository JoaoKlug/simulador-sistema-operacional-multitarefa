"""
Utilitário de pré-compilação para gerar o ícone (.ico) da aplicação.
Evita que o executável utilize o ícone padrão do PyInstaller, reduzindo falsos positivos no Windows Defender.
"""
import os
from PIL import Image, ImageDraw


def gerar_icone_aplicacao(caminho_destino: str = "assets/icone_app.ico") -> None:
    """Gera um ícone multi-resolução (.ico) representando um gráfico de escalonamento de CPU."""
    os.makedirs(os.path.dirname(caminho_destino), exist_ok=True)

    tamanho = 256
    img = Image.new("RGBA", (tamanho, tamanho), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fundo arredondado azul escuro moderno
    draw.rounded_rectangle([12, 12, 244, 244], radius=42, fill=(30, 41, 59, 255), outline=(56, 189, 248, 255), width=6)

    # Barras horizontais estilizadas simulando o Gráfico de Gantt de tarefas
    barras = [
        (44, 54, 156, 86, (46, 204, 113, 255)),   # Verde
        (44, 102, 208, 134, (52, 152, 219, 255)), # Azul
        (92, 150, 212, 182, (241, 196, 15, 255)), # Amarelo
        (44, 194, 140, 214, (231, 76, 60, 255)),  # Vermelho
    ]
    for x1, y1, x2, y2, cor in barras:
        draw.rounded_rectangle([x1, y1, x2, y2], radius=8, fill=cor)

    img.save(
        caminho_destino,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )


if __name__ == "__main__":
    gerar_icone_aplicacao()
