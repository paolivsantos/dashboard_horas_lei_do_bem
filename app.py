import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Dashboard Lei do Bem", layout="wide")
st.title("📊 Centralizador Lei do Bem (JIRA -> Sheets)")

# --- CONFIGURAÇÃO ---
# COLE O LINK DA SUA PLANILHA ABAIXO
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1LKu-e1vVlTZ6NxMXO0MmTt-WqC2_iCRYF1mN8M0WIK8/edit?gid=0#gid=0"

if URL_PLANILHA == "https://docs.google.com/spreadsheets/d/1LKu-e1vVlTZ6NxMXO0MmTt-WqC2_iCRYF1mN8M0WIK8/edit?gid=0#gid=0":
    st.error("⚠️ Edite o app.py e cole o link da sua planilha na variável URL_PLANILHA.")
    st.stop()

# --- AUTENTICAÇÃO ---
try:
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = {
        "type": st.secrets["gcp_service_account"]["type"],
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"],
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
    }
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    # Abre a planilha pelo URL e pega a primeira aba (índice 0)
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
        
        # Cria colunas de controle se não existirem
        if 'Tempo gasto' not in df.columns:
            st.error("Coluna 'Tempo gasto' não encontrada no CSV.")
            st.stop()
            
        df['Horas'] = pd.to_numeric(df['Tempo gasto'], errors='coerce').fillna(0) / 3600
        df['Arquivo_Origem'] = uploaded_file.name
        
        # Converte tudo para string para evitar erros de tipo do Google
        df = df.astype(str)
        
        st.write(f"✅ Arquivo lido: {len(df)} linhas.")
        
        if st.button("🚀 ENVIAR PARA PLANILHA"):
            with st.spinner("Gravando..."):
                # Verifica se precisamos adicionar cabeçalho
                valores = sheet.get_all_values()
                if not valores:
                    sheet.append_row(df.columns.tolist())
                
                # Envia
                sheet.append_rows(df.values.tolist(), value_input_option="USER_ENTERED")
                st.success("Dados enviados!")
                
                # Debug na tela
                st.write("Últimas 2 linhas detectadas na planilha:")
                st.write(sheet.get_all_values()[-2:])
                st.balloons()
                
    except Exception as e:
        st.error(f"Erro no processamento: {e}")

# --- RELATÓRIO ---
st.write("---")
if conexao_ok:
    try:
        dados = sheet.get_all_values()
        if len(dados) > 1:
            df_hist = pd.DataFrame(dados[1:], columns=dados[0])
            st.write("### Auditoria dos Dados na Planilha:")
            st.dataframe(df_hist.tail(10))
        else:
            st.info("Planilha vazia.")
    except Exception as e:
        st.error(f"Erro ao ler histórico: {e}")
