import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Dashboard Lei do Bem", layout="wide")
st.title("📊 Centralizador Lei do Bem (JIRA -> Sheets)")

# Configuração de Autenticação com o Google Sheets usando Secrets
# O Streamlit irá coletar as credenciais diretamente do painel de controle
try:
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # Criando dicionário de credenciais a partir dos Secrets do Streamlit
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
    
    # Abre a planilha pelo nome exato que você criou no Drive
    # IMPORTANTE: A planilha deve estar compartilhada com o e-mail da Service Account (passo abaixo)
    sheet = client.open("Base_Dados_Lei_do_Bem").worksheet("Dados_Acumulados")
    conexao_ok = True
except Exception as e:
    st.error(f"Erro na conexão com o Google Sheets. Certifique-se de configurar os Secrets corretamente. Detalhes: {e}")
    conexao_ok = False

# Upload do CSV mensal exportado do JIRA
uploaded_file = st.file_uploader("Suba o CSV de um Componente do JIRA", type=["csv"])

if uploaded_file and conexao_ok:
    df_novo = pd.read_csv(uploaded_file)
    
    # Tratamento dos dados e criação das colunas extras calculadas
    df_novo['Horas'] = df_novo['Tempo gasto'] / 3600
    df_novo['Data'] = pd.to_datetime(df_novo['Criado'], errors='coerce', format='mixed')
    
    df_novo = df_novo.dropna(subset=['Data']).copy()
    df_novo['Mes'] = df_novo['Data'].dt.strftime('%m/%Y')
    df_novo['Arquivo_Origem'] = uploaded_file.name
    
    st.success(f"Arquivo '{uploaded_file.name}' carregado! {len(df_novo)} linhas processadas com sucesso.")
    
    if st.button("🚀 Enviar e Acumular no Google Sheets"):
        try:
            # Converte todo o dataframe novo para texto (padrão aceito sem erro pelo Sheets)
            df_novo = df_novo.fillna("")
            df_novo['Data'] = df_novo['Data'].astype(str)
            
            # Transforma o DataFrame em uma lista de listas para enviar ao gspread
            dados_para_enviar = df_novo.values.tolist()
            
            # Adiciona as linhas no final da planilha de forma incremental
            sheet.append_rows(dados_para_enviar, value_input_option="USER_ENTERED")
            
            st.balloons()
            st.success("Dados integrados à Planilha Mestra com sucesso!")
        except Exception as err:
            st.error(f"Falha ao enviar dados para a planilha: {err}")

# --- VISUALIZAÇÃO DOS DADOS ACUMULADOS ---
st.write("---")
st.subheader("🔍 Filtros e Relatórios de Auditoria")

if conexao_ok:
    try:
        # Busca todas as linhas da planilha para gerar o dashboard em tempo real
        todas_linhas = sheet.get_all_records()
        
        if todas_linhas:
            df_historico = pd.DataFrame(todas_linhas)
            
            # Filtros dinâmicos na tela
            lista_componentes = df_historico['Componentes'].dropna().unique()
            comp_selecionado = st.multiselect("Filtrar por Componente:", lista_componentes, default=lista_componentes)
            
            df_filtrado = df_historico[df_historico['Componentes'].isin(comp_selecionado)]
            df_filtrado['Horas'] = pd.to_numeric(df_filtrado['Horas'], errors='coerce').fillna(0)
            
            # Exibição do resumo consolidado em horas para a Lei do Bem
            resumo = df_filtrado.groupby(['Componentes', 'Responsável', 'Mes'])['Horas'].sum().reset_index()
            
            def formatar_horas(decimal):
                horas = int(decimal)
                minutos = int((decimal - horas) * 60)
                return f"{horas}h {minutos}m"
                
            resumo['Tempo Total'] = resumo['Horas'].apply(formatar_horas)
            st.dataframe(resumo[['Componentes', 'Responsável', 'Mes', 'Tempo Total']], use_container_width=True)
        else:
            st.info("A planilha no Google Sheets está vazia. Faça o primeiro upload acima!")
            
    except Exception as e:
        st.info("Aguardando o primeiro upload para estruturar e exibir o histórico consolidado.")
