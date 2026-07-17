import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Dashboard Lei do Bem", layout="wide")
st.title("📊 Centralizador Lei do Bem (JIRA -> Sheets)")

# Conexão com o Google Sheets (configurada nos Secrets do Streamlit)
conn = st.connection("gsheets", type=GSheetsConnection)

# 1. Upload do CSV mensal/individual
uploaded_file = st.file_uploader("Suba o CSV de um Componente do JIRA", type=["csv"])

if uploaded_file:
    # Lendo o arquivo que você acabou de baixar do JIRA
    df_novo = pd.read_csv(uploaded_file)
    
    # Tratamento dos dados (Conversão de segundos para horas e datas)
    df_novo['Horas'] = df_novo['Tempo gasto'] / 3600
    df_novo['Data'] = pd.to_datetime(df_novo['Criado'], dayfirst=True)
    df_novo['Mes'] = df_novo['Data'].dt.strftime('%m/%Y') # Formato MM/AAAA
    
    # Pegando o nome do arquivo para registrar como metadado
    df_novo['Arquivo_Origem'] = uploaded_file.name
    
    st.success(f"Arquivo '{uploaded_file.name}' carregado com sucesso! {len(df_novo)} linhas encontradas.")
    
    # Botão para persistir os dados no Google Sheets
    if st.button("🚀 Enviar e Acumular no Google Sheets"):
        try:
            # Busca o que já existe salvo no Sheets para não apagar o histórico
            base_existente = conn.read(worksheet="Dados_Acumulados")
            
            # Une os dados antigos com os novos (Empilhamento)
            base_atualizada = pd.concat([base_existente, df_novo], ignore_index=True)
        except:
            # Se for a primeiríssima vez e o Sheets estiver vazio
            base_atualizada = df_novo
            
        # Salva a nova base gigante de volta no Google Sheets
        conn.update(worksheet="Dados_Acumulados", data=base_atualizada)
        st.balloons()
        st.sidebar.success("Dados integrados ao histórico com sucesso!")

# --- PARTE DE VISUALIZAÇÃO DO HISTÓRICO ---
st.write("---")
st.subheader("🔍 Visualização do Histórico Acumulado")

try:
    # O Dashboard sempre lê a versão atualizada do Sheets para te mostrar os gráficos
    df_historico = conn.read(worksheet="Dados_Acumulados")
    
    # Criação dos Filtros Dinâmicos na Tela baseados no histórico real
    lista_componentes = df_historico['Componentes'].unique()
    comp_selecionado = st.multiselect("Filtrar por Componente/Projeto:", lista_componentes, default=lista_componentes)
    
    # Aplica o filtro
    df_filtrado = df_historico[df_historico['Componentes'].isin(comp_selecionado)]
    
    # Agrupamento final para auditoria (Ex: Horas por colaborador por Mês)
    resumo = df_filtrado.groupby(['Componentes', 'Responsável', 'Mes'])['Horas'].sum().reset_index()
    st.dataframe(resumo, use_container_width=True)
    
except:
    st.info("Nenhum dado histórico encontrado no Google Sheets ainda. Faça o primeiro upload acima!")
