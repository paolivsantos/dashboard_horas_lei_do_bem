import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Dashboard Lei do Bem", layout="wide")
st.title("📊 Centralizador Lei do Bem (JIRA -> Sheets)")

# Conexão nativa com o Google Sheets utilizando os Secrets salvos
conn = st.connection("gsheets", type=GSheetsConnection)

# Upload do CSV mensal exportado do JIRA
uploaded_file = st.file_uploader("Suba o CSV de um Componente do JIRA", type=["csv"])

if uploaded_file:
    # Lendo o arquivo do JIRA
    df_novo = pd.read_csv(uploaded_file)
    
    # Tratamento dos dados e criação das colunas extras calculadas
    df_novo['Horas'] = df_novo['Tempo gasto'] / 3600
    df_novo['Data'] = pd.to_datetime(df_novo['Criado'], dayfirst=True)
    df_novo['Mes'] = df_novo['Data'].dt.strftime('%m/%Y')
    df_novo['Arquivo_Origem'] = uploaded_file.name
    
    st.success(f"Arquivo '{uploaded_file.name}' carregado! {len(df_novo)} linhas processadas.")
    
    # Botão para salvar no Google Sheets de forma acumulada
    if st.button("🚀 Enviar e Acumular no Google Sheets"):
        try:
            # Tenta ler o histórico para empilhar
            base_existente = conn.read(worksheet="Dados_Acumulados")
            base_atualizada = pd.concat([base_existente, df_novo], ignore_index=True)
        except:
            # Caso a planilha esteja limpa/vazia
            base_atualizada = df_novo
            
        # Atualiza a planilha mestra
        conn.update(worksheet="Dados_Acumulados", data=base_atualizada)
        st.balloons()
        st.success("Dados integrados à Planilha Mestra com sucesso!")

# --- VISUALIZAÇÃO DOS DADOS ACUMULADOS ---
st.write("---")
st.subheader("🔍 Filtros e Relatórios de Auditoria")

try:
    # Sempre busca a versão em tempo real do Sheets para montar os gráficos
    df_historico = conn.read(worksheet="Dados_Acumulados")
    
    # Filtros na tela
    lista_componentes = df_historico['Componentes'].dropna().unique()
    comp_selecionado = st.multiselect("Filtrar por Componente:", lista_componentes, default=lista_componentes)
    
    # Aplicando filtros
    df_filtrado = df_historico[df_historico['Componentes'].isin(comp_selecionado)]
    
    # Exibição do resumo consolidado em horas para a Lei do Bem
    resumo = df_filtrado.groupby(['Componentes', 'Responsável', 'Mes'])['Horas'].sum().reset_index()
    
    # Formatação amigável de horas decimais para HH:MM
    def formatar_horas(decimal):
        horas = int(decimal)
        minutos = int((decimal - horas) * 60)
        return f"{horas}h {minutos}m"
        
    resumo['Tempo Total'] = resumo['Horas'].apply(formatar_horas)
    
    # Mostra a tabela na tela
    st.dataframe(resumo[['Componentes', 'Responsável', 'Mes', 'Tempo Total']], use_container_width=True)
    
except Exception as e:
    st.info("Aguardando o primeiro upload para exibir o histórico consolidado.")
