import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Dashboard Lei do Bem", layout="wide")
st.title("📊 Centralizador Lei do Bem (JIRA -> Sheets)")

# --- CONFIGURAÇÃO ---
# URL direta da sua planilha
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1LKu-e1vVlTZ6NxMXO0MmTt-WqC2_iCRYF1mN8M0WIK8/edit?gid=0#gid=0"

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
    st.error(f"Erro na conexão com o Google Sheets: {e}")
    conexao_ok = False

# Colunas padrão para garantir que o envio sempre fique organizado
colunas_padrao = [
    "Chave do Item", "ID do Item", "Resumo", "Componentes", "Tempo gasto",
    "∑ de tempo gasto", "Responsável", "ID do responsável", "Criado", "Resolvido",
    "Status", "Horas", "Data", "Mes", "Arquivo_Origem"
]

# --- PROCESSAMENTO E ENVIO ---
uploaded_file = st.file_uploader("Suba o CSV do JIRA", type=["csv"])

if uploaded_file and conexao_ok:
    try:
        # Lê o arquivo
        df = pd.read_csv(uploaded_file, sep=None, engine='python')
        
        # Faz os cálculos de Horas e Datas
        if 'Tempo gasto' in df.columns:
            df['Horas'] = pd.to_numeric(df['Tempo gasto'], errors='coerce').fillna(0) / 3600
        else:
            df['Horas'] = 0
            
        if 'Criado' in df.columns:
            datas_convertidas = pd.to_datetime(df['Criado'], errors='coerce', format='mixed')
            df['Data'] = datas_convertidas.fillna(df['Criado']).astype(str)
            df['Mes'] = datas_convertidas.dt.strftime('%m/%Y').fillna(df['Criado'].astype(str).str[3:10])
        else:
            df['Data'], df['Mes'] = "", ""
            
        df['Arquivo_Origem'] = uploaded_file.name
        
        # Filtra e organiza as colunas
        df = df.reindex(columns=colunas_padrao).fillna("")
        df = df.astype(str)
        
        st.write(f"✅ Arquivo pronto para envio: {len(df)} linhas.")
        
        if st.button("🚀 ENVIAR PARA PLANILHA"):
            with st.spinner("Gravando no Google Sheets..."):
                sheet.append_rows(df.values.tolist(), value_input_option="USER_ENTERED")
                st.success("Dados enviados com sucesso!")
                st.balloons()
            
    except Exception as e:
        st.error(f"Erro no processamento do arquivo: {e}")

# --- RELATÓRIO E AUDITORIA (BLINDADO CONTRA COLUNAS VAZIAS) ---
st.write("---")
st.subheader("🔍 Histórico de Dados na Planilha")

if conexao_ok:
    try:
        # Busca tudo o que está na planilha
        dados = sheet.get_all_values()
        
        if len(dados) > 1:
            # 1. Pega os cabeçalhos originais (linha 1)
            cabecalhos_originais = dados[0]
            
            # 2. Mantém APENAS as colunas que têm um nome escrito (ignora os vazios '')
            colunas_uteis = [c for c in cabecalhos_originais if c.strip() != '']
            num_colunas = len(colunas_uteis)
            
            # 3. Corta os dados da tabela para terem exatamente o mesmo número de colunas úteis
            dados_limpos = [linha[:num_colunas] for linha in dados[1:]]
            
            # 4. Cria o DataFrame sem perigo de nomes duplicados
            df_hist = pd.DataFrame(dados_limpos, columns=colunas_uteis)
            
            # Mostra as últimas linhas para confirmar o que está lá
            st.dataframe(df_hist.tail(10), use_container_width=True)
            
            # --- Seção de Resumo de Horas ---
            if 'Componentes' in df_hist.columns and 'Horas' in df_hist.columns and 'Responsável' in df_hist.columns:
                st.write("### ⏱️ Resumo de Horas por Responsável")
                
                # Prepara os dados para o cálculo
                df_hist['Horas'] = pd.to_numeric(df_hist['Horas'].str.replace(',', '.'), errors='coerce').fillna(0)
                df_hist = df_hist[df_hist['Chave do Item'] != 'Chave do Item'] # Remove cabeçalhos duplicados no meio
                
                resumo = df_hist.groupby(['Componentes', 'Responsável', 'Mes'])['Horas'].sum().reset_index()
                
                def formatar_horas(decimal):
                    horas = int(decimal)
                    minutos = int(round((decimal - horas) * 60, 0))
                    if minutos == 60:
                        horas += 1
                        minutos = 0
                    return f"{horas}h {minutos}m"
                    
                resumo['Tempo Total'] = resumo['Horas'].apply(formatar_horas)
                st.dataframe(resumo[['Componentes', 'Responsável', 'Mes', 'Tempo Total']], use_container_width=True)
                
        else:
            st.info("Planilha vazia ou com cabeçalho ausente.")
            
    except Exception as e:
        st.error(f"Erro ao ler histórico: {e}")
