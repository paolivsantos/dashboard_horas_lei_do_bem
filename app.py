import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Dashboard Lei do Bem", layout="wide")
st.title("📊 Centralizador Lei do Bem (JIRA -> Sheets)")

# Inicializa as variáveis de memória do Streamlit se elas não existirem
if 'df_processado' not in st.session_state:
    st.session_state.df_processado = None
if 'nome_arquivo' not in st.session_state:
    st.session_state.nome_arquivo = ""

# Configuração de Autenticação
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
    sheet = client.open("Base_Dados_Lei_do_Bem").worksheet("Dados_Acumulados")
    conexao_ok = True
except Exception as e:
    st.error(f"Erro na conexão com o Google Sheets: {e}")
    conexao_ok = False

# Definição das colunas padrão esperadas pelo Sheets
colunas_padrao = [
    "Chave do Item", "ID do Item", "Resumo", "Componentes", "Tempo gasto",
    "∑ de tempo gasto", "Responsável", "ID do responsável", "Criado", "Resolvido",
    "Status", "Horas", "Data", "Mes", "Arquivo_Origem"
]

uploaded_file = st.file_uploader("Suba o CSV de um Componente do JIRA", type=["csv"])

# Se o usuário subiu um arquivo novo, processa e guarda na memória estável (session_state)
if uploaded_file:
    if st.session_state.nome_arquivo != uploaded_file.name:
        try:
            # Detecta o separador de forma automática
            df_novo = pd.read_csv(uploaded_file, sep=None, engine='python')
            
            # Cálculos de tempo e conversões de datas seguras
            df_novo['Horas'] = pd.to_numeric(df_novo['Tempo gasto'], errors='coerce').fillna(0) / 3600
            datas_convertidas = pd.to_datetime(df_novo['Criado'], errors='coerce', format='mixed')
            df_novo['Data'] = datas_convertidas.fillna(df_novo['Criado']).astype(str)
            df_novo['Mes'] = datas_convertidas.dt.strftime('%m/%Y').fillna(df_novo['Criado'].astype(str).str[3:10])
            df_novo['Arquivo_Origem'] = uploaded_file.name
            
            # Padronização de colunas
            df_novo = df_novo.reindex(columns=colunas_padrao).fillna("")
            
            # Salva na memória persistente
            st.session_state.df_processado = df_novo
            st.session_state.nome_arquivo = uploaded_file.name
        except Exception as e:
            st.error(f"Erro ao processar o CSV: {e}")

# Se houver dados processados na memória, exibe a interface de envio de forma estável
if st.session_state.df_processado is not None and conexao_ok:
    df_atual = st.session_state.df_processado
    st.success(f"Arquivo '{st.session_state.nome_arquivo}' pronto! {len(df_atual)} linhas identificadas na memória.")
    
    if st.button("🚀 Enviar e Acumular no Google Sheets"):
        try:
            # Verifica se a planilha precisa de cabeçalhos
            valores_atuais = sheet.get_all_values()
            if len(valores_atuais) == 0:
                sheet.append_row(colunas_padrao)
            
            dados_para_enviar = df_atual.values.tolist()
            
            if len(dados_para_enviar) > 0:
                sheet.append_rows(dados_para_enviar, value_input_option="USER_ENTERED")
                st.balloons()
                st.success(f"Sucesso real! {len(dados_para_enviar)} linhas enviadas à Planilha Mestra.")
                
                # Limpa a memória pós-envio com sucesso para evitar cliques duplos acidentais
                st.session_state.df_processado = None
                st.session_state.nome_arquivo = ""
            else:
                st.warning("Nenhum dado válido para envio.")
        except Exception as e:
            st.error(f"Erro ao enviar dados para o Google Sheets: {e}")

# --- VISUALIZAÇÃO DOS DADOS ACUMULADOS ---
st.write("---")
st.subheader("🔍 Filtros e Relatórios de Auditoria")

if conexao_ok:
    try:
        todas_linhas = sheet.get_all_records()
        if todas_linhas:
            df_historico = pd.DataFrame(todas_linhas)
            df_historico = df_historico[df_historico['Chave do Item'] != 'Chave do Item']
            
            lista_componentes = df_historico['Componentes'].dropna().unique()
            lista_componentes = [c for c in lista_componentes if str(c).strip() != ""]
            
            if len(lista_componentes) > 0:
                comp_selecionado = st.multiselect("Filtrar por Componente:", lista_componentes, default=lista_componentes)
                df_filtrado = df_historico[df_historico['Componentes'].isin(comp_selecionado)]
            else:
                df_filtrado = df_historico
                
            df_filtrado['Horas'] = pd.to_numeric(df_filtrado['Horas'], errors='coerce').fillna(0)
            
            if not df_filtrado.empty and 'Responsável' in df_filtrado.columns:
                resumo = df_filtrado.groupby(['Componentes', 'Responsável', 'Mes'])['Horas'].sum().reset_index()
                
                def formatar_horas(decimal):
                    horas = int(decimal)
                    minutos = int((decimal - horas) * 60)
                    return f"{horas}h {minutos}m"
                    
                resumo['Tempo Total'] = resumo['Horas'].apply(formatar_horas)
                st.dataframe(resumo[['Componentes', 'Responsável', 'Mes', 'Tempo Total']], use_container_width=True)
            else:
                st.info("Dados estruturados encontrados, mas sem registros filtráveis.")
        else:
            st.info("A planilha no Google Sheets está vazia ou sem cabeçalhos válidos.")
    except Exception as e:
        st.info("Aguardando uploads válidos para renderizar o histórico.")
