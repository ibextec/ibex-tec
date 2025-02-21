import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from rectpack import newPacker
from fpdf import FPDF
from io import BytesIO

# Função principal
def main():
    st.title("Otimização de Corte de Chapas")

    # Entradas do usuário
    st.sidebar.header("Configurações da Chapa")
    chapa_largura = st.sidebar.number_input("Largura da chapa (mm)", value=2750, min_value=1)
    chapa_altura = st.sidebar.number_input("Altura da chapa (mm)", value=1850, min_value=1)
    espessura_chapa = st.sidebar.selectbox("Espessura da chapa (mm)", [0.6, 1.5, 8, 25], index=1)
    maquina = st.sidebar.selectbox("Máquina", ["Rauter", "Seccionadora"])

    st.sidebar.header("Peças")
    num_pecas = st.sidebar.number_input("Número de tipos de peças", min_value=1, value=3)
    pecas = []
    for i in range(num_pecas):
        st.sidebar.subheader(f"Peça {i+1}")
        largura = st.sidebar.number_input(f"Largura da peça {i+1} (mm)", min_value=1, value=600)
        altura = st.sidebar.number_input(f"Altura da peça {i+1} (mm)", min_value=1, value=400)
        quantidade = st.sidebar.number_input(f"Quantidade da peça {i+1}", min_value=1, value=3)
        pecas.append((largura, altura, quantidade))

    if st.sidebar.button("Gerar Plano de Corte"):
        plano_corte, num_chapas = otimizar_corte_multiplas_chapas(chapa_largura, chapa_altura, pecas, maquina)
        processar_resultados(plano_corte, espessura_chapa, maquina, num_chapas)

# Função para otimizar o corte com múltiplas chapas
def otimizar_corte_multiplas_chapas(chapa_largura, chapa_altura, pecas, maquina):
    packer = newPacker(rotation=True)

    # Ajuste de margens e espaçamento com base na máquina
    if maquina == "Rauter":
        margem_lateral = 10  # Refilo nas laterais
        espacamento = 12     # Espaço entre peças
    elif maquina == "Seccionadora":
        margem_lateral = 10  # Refilo nas laterais
        espacamento = 4      # Espaço entre peças
    else:
        raise ValueError("Máquina não suportada. Escolha 'Rauter' ou 'Seccionadora'.")

    # Dimensões ajustadas da chapa considerando o refilo
    largura_ajustada = chapa_largura - 2 * margem_lateral
    altura_ajustada = chapa_altura - 2 * margem_lateral

    # Adicionar múltiplas chapas ao pacote
    num_chapas = 0
    while any(qtd > 0 for _, _, qtd in pecas):
        packer.add_bin(largura_ajustada, altura_ajustada)
        num_chapas += 1

        # Adicionar peças ao pacote com espaçamento
        for i, (largura, altura, qtd) in enumerate(pecas):
            if qtd > 0:
                packer.add_rect(largura + espacamento, altura + espacamento, rid=i)
                pecas[i] = (largura, altura, qtd - 1)

        # Executar o empacotamento
        packer.pack()

    # Extrair o plano de corte
    plano_corte = []
    for abin in packer:
        for rect in abin:
            x, y, largura, altura = rect.x + margem_lateral, rect.y + margem_lateral, rect.width - espacamento, rect.height - espacamento
            plano_corte.append((x, y, largura, altura))

    return plano_corte, num_chapas

# Função para processar resultados
def processar_resultados(plano_corte, espessura_chapa, maquina, num_chapas):
    st.subheader("Plano de Corte Otimizado")
    desenhar_plano(plano_corte, 2750, 1850)

    area_total_chapa = 2750 * 1850 * num_chapas
    area_utilizada = sum(largura * altura for _, _, largura, altura in plano_corte)
    aproveitamento = (area_utilizada / area_total_chapa) * 100
    st.write(f"Aproveitamento da chapa ({maquina}): {aproveitamento:.2f}%")

    relatorio_fitas_e_cortes(plano_corte, espessura_chapa)
    gerar_etiquetas(plano_corte, maquina)
    exportar_csv_pdf(plano_corte, espessura_chapa, maquina, num_chapas)

# Função para desenhar o plano de corte
def desenhar_plano(plano_corte, chapa_largura, chapa_altura):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_xlim([0, chapa_largura])
    ax.set_ylim([0, chapa_altura])
    colors = plt.cm.get_cmap("tab10", len(plano_corte))
    for i, (x, y, largura, altura) in enumerate(plano_corte):
        color = colors(i)
        rect = plt.Rectangle((x, y), largura, altura, edgecolor='black', facecolor=color, linewidth=2)
        ax.add_patch(rect)
        ax.text(x + largura/2, y + altura/2, f"{largura}x{altura}", fontsize=8, ha='center', va='center', color='white')
    plt.gca().invert_yaxis()
    plt.title("Plano de Corte Otimizado")
    st.pyplot(fig)

# Função para gerar relatório de fitas de borda e cortes
def relatorio_fitas_e_cortes(plano_corte, espessura_chapa):
    total_perimetro = 0
    total_cortes = 0

    for x, y, largura, altura in plano_corte:
        perimetro = 2 * (largura + altura)
        total_perimetro += perimetro
        total_cortes += 4  # 4 cortes por peça (um para cada lado)

    comprimento_fitas = total_perimetro / 1000  # Convertendo para metros

    st.subheader("Relatório de Fitas e Cortes")
    st.write(f"Espessura da chapa: {espessura_chapa} mm")
    st.write(f"Comprimento total de fitas de borda: {comprimento_fitas:.2f} metros")
    st.write(f"Número total de cortes: {total_cortes}")

# Função para gerar etiquetas para cada peça
def gerar_etiquetas(plano_corte, maquina):
    st.subheader("Etiquetas para Peças")
    for i, (x, y, largura, altura) in enumerate(plano_corte, start=1):
        st.write(f"Etiqueta {i}: Maquina={maquina}, Posição=({x}, {y}), Dimensões={largura}x{altura}")

# Função para exportar CSV e PDF
def exportar_csv_pdf(plano_corte, espessura_chapa, maquina, num_chapas):
    df = pd.DataFrame(plano_corte, columns=["Posição X", "Posição Y", "Largura", "Altura"])
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Baixar Plano de Corte (CSV)", data=csv, file_name=f"plano_corte_{maquina}.csv", mime="text/csv")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Plano de Corte Otimizado ({maquina})", ln=True, align='C')
    pdf.cell(200, 10, f"Espessura da chapa: {espessura_chapa} mm", ln=True)
    for x, y, largura, altura in plano_corte:
        pdf.cell(200, 10, f"Peça: {largura}x{altura}mm - Posição: ({x}, {y})", ln=True)
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    st.download_button("Baixar Plano de Corte (PDF)", data=pdf_bytes, file_name=f"plano_corte_{maquina}.pdf", mime="application/pdf")

# Executar o programa
if __name__ == "__main__":
    main()
