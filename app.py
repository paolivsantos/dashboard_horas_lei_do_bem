import streamlit as st
import pandas as pd

st.set_page_config(page_title="Dashboard Lei do Bem", layout="wide")

st.title("📊 Análise de Horas - Lei do Bem (JIRA)")

uploaded_file = st.file_uploader("Suba o arquivo CSV do JIRA", type=["csv"])

if uploaded_file:
    # 1. Carregamento e Conversão
    df = pd.read_csv(uploaded_file)
    
    # Converter segundos para horas decimais (JIRA exporta em segundos)
    df['Horas'] = df['Tempo gasto'] / 3600
    
    # Converter 'Criado' para formato de data
    df['Data'] = pd.to_datetime(df['Criado'], dayfirst=True)
    df['Mes'] = df['Data'].dt.to_period('M')
    
    # 2. Agrupamento e Cálculo
    # Agrupa por Componente, Responsável e Mês
    resumo = df.groupby(['Componentes', 'Responsável', 'Mes'])['Horas'].sum().reset_index()
    
    # Formatação para exibir HH:MM (ex: 8.5 -> 8h 30m)
    def formatar_horas(decimal):
        horas = int(decimal)
        minutos = int((decimal - horas) * 60)
        return f"{horas}h {minutos}m"
    
    resumo['Tempo Formatado'] = resumo['Horas'].apply(formatar_horas)
    
    # 3. Exibição
    st.subheader("Resumo Consolidado")
    st.dataframe(resumo[['Componentes', 'Responsável', 'Mes', 'Tempo Formatado']], use_container_width=True)
    
    # Download para facilitar a auditoria
    csv_final = resumo.to_csv(index=False).encode('utf-8')
    st.download_button("Baixar Relatório Final", data=csv_final, file_name="relatorio_lei_do_bem.csv")
