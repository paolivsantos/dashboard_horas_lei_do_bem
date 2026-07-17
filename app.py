import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Gestão de Horas", layout="wide")

st.title("📊 Dashboard de Apontamento de Horas")

# 1. Upload
uploaded_file = st.file_uploader("Suba seu arquivo CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # 2. Sidebar de Filtros
    st.sidebar.header("Filtros")
    colaborador = st.sidebar.multiselect("Colaborador", options=df['colaborador'].unique())
    
    if colaborador:
        df = df[df['colaborador'].isin(colaborador)]
        
    # 3. Análise de Somatória
    # Agrupamento: Soma de horas por colaborador e projeto
    resumo = df.groupby(['colaborador', 'projeto'])['horas'].sum().reset_index()
    
    # KPIs
    c1, c2 = st.columns(2)
    c1.metric("Total de Horas", f"{df['horas'].sum()}h")
    c2.metric("Projetos distintos", df['projeto'].nunique())
    
    # 4. Visualização
    fig = px.bar(resumo, x='colaborador', y='horas', color='projeto', 
                 title="Horas por Colaborador", barmode='group')
    st.plotly_chart(fig, use_container_width=True)
    
    # 5. Tabela
    st.subheader("Dados Detalhados")
    st.dataframe(df, use_container_width=True)
    
    # Download do Resumo
    csv = resumo.to_csv(index=False).encode('utf-8')
    st.download_button("Baixar Resumo (CSV)", data=csv, file_name="resumo_horas.csv")