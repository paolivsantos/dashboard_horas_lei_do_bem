import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Dashboard Lei do Bem", layout="wide")
st.title("📊 Centralizador Lei do Bem (JIRA -> Sheets)")

# --- CONFIGURAÇÃO ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1LKu-e1vVlTZ6NxMXO0MmTt-WqC2_iCRYF1mN8M0WIK8/edit?gid=0#gid=0"

# Mapeamento consolidado
MAPEAMENTO_RR = {
    "Alescia Fernandes": "84654", "Anderson Batista": "85236", "Anderson Oliva": "78172",
    "Bruno Moiteiro": "84437", "Dyonathan Jordan": "86281", "Gabriel Shioda": "86618",
    "Glaucia Mekaru": "84452", "Guilherme Barreira": "85338", "Jorge Luiz": "86238",
    "José Clailton": "85479", "Lucas Godinho": "85224", "Lucas Martinez": "84515",
    "Rafael Ferreira": "85051", "Reinaldo Marques": "82927", "Ronaldo Maciel": "84162",
    "Vinicius Freire": "85499", "Vittor Strefezzi": "85335", "Willian Kenji": "85217"
}

# --- AUTENTICAÇÃO ---
try:
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    client = gspread.authorize(creds)
    sheet = client.open_by_url(URL_PLANILHA).get_worksheet(0)
    conexao_ok = True
except Exception as e:
    st.error(f"Erro na conexão: {e}")
    conexao_ok = False

# --- PROCESSAMENTO ---
uploaded_file = st.file_uploader("Suba o CSV do JIRA", type=["csv"])

if uploaded_file and conexao_ok:
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine='python')
        df['Horas'] = pd.to_numeric(df.get('Tempo gasto', 0), errors='coerce').fillna(0) / 3600
        df['Arquivo_Origem'] = uploaded_file.name
        
        # Converte para string para envio
        df_envio = df.astype(str)
        
        if st.button("🚀 ENVIAR PARA PLANILHA"):
            sheet.append_rows(df_envio.values.tolist(), value_input_option="USER_ENTERED")
            st.success("Dados enviados!")
            st.balloons()
    except Exception as e:
        st.error(f"Erro: {e}")

# --- RELATÓRIO MATRICIAL ---
st.write("---")
st.subheader("📅 Matriz de Horas por Componente, Responsável e Mês")

if conexao_ok:
    try:
        dados = sheet.get_all_values()
        if len(dados) > 1:
            # Limpeza das colunas vazias
            cabecalhos_uteis = [c for c in dados[0] if c.strip() != '']
            dados_limpos = [linha[:len(cabecalhos_uteis)] for linha in dados[1:]]
            df_hist = pd.DataFrame(dados_limpos, columns=cabecalhos_uteis)
            
            # Formatação
            df_hist['Horas'] = pd.to_numeric(df_hist['Horas'].str.replace(',', '.'), errors='coerce').fillna(0)
            df_hist['RR'] = df_hist['Responsável'].map(MAPEAMENTO_RR).fillna("N/A")
            
            # Pivot table com meses como colunas
            # Ordena meses cronologicamente (assume formato MM/YYYY)
            df_hist['Mes_Dt'] = pd.to_datetime(df_hist['Mes'], format='%m/%Y', errors='coerce')
            df_hist = df_hist.sort_values('Mes_Dt')
            
            pivot = pd.pivot_table(
                df_hist, 
                values='Horas', 
                index=['Componentes', 'Responsável', 'RR'], 
                columns='Mes', 
                aggfunc='sum', 
                fill_value=0
            )
            
            # Adiciona totalizador
            pivot['Total'] = pivot.sum(axis=1)
            
            st.dataframe(pivot.style.format("{:.1f}"), use_container_width=True)
        else:
            st.info("Planilha vazia.")
    except Exception as e:
        st.error(f"Erro na visualização: {e}")
