import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Dashboard Lei do Bem", layout="wide")
st.title("📊 Centralizador Lei do Bem (JIRA -> Sheets)")

# Autenticação
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

colunas_padrao = [
    "Chave do Item", "ID do Item", "Resumo", "Componentes", "Tempo gasto",
    "∑ de tempo gasto", "Responsável", "ID do responsável", "Criado", "Resolvido",
    "Status", "Horas", "Data", "Mes", "Arquivo_Origem"
]

uploaded_file = st.file_uploader("Suba o CSV exportado do JIRA", type=["csv"])

if uploaded_file and conexao_ok:
    try:
        # Lê o CSV detectando automaticamente o separador
        df_novo = pd.read_csv(uploaded_file, sep=None, engine='python')
        
        # MODO DIAGNÓSTICO: Mostra na tela o que o Python enxergou
        st.write("👀 **Prévia dos dados lidos do arquivo bruto:**")
        st.dataframe(df_novo.head(2))
        
        # Verifica se as colunas essenciais existem antes de calcular
        if 'Tempo gasto' not in df_novo.columns:
            st.error("⚠️ Erro: A coluna 'Tempo gasto' não foi encontrada. Verifique os cabeçalhos exportados pelo JIRA.")
        
        # Cálculos com segurança extra
        df_novo['Horas'] = pd.to_numeric(df_novo.get('Tempo gasto', 0), errors='coerce').fillna(0) / 3600
        
        if 'Criado' in df_novo.columns:
            datas_convertidas = pd.to_datetime(df_novo['Criado'], errors='coerce', format='mixed')
            df_novo['Data'] = datas_convertidas.fillna(df_novo['Criado']).astype(str)
            df_novo['Mes'] = datas_convertidas.dt.strftime('%m/%Y').fillna(df_novo['Criado'].astype(str).str[3:10])
        else:
            df_novo['Data'] = ""
            df_novo['Mes'] = ""
            st.error("⚠️ Erro: A coluna 'Criado' não foi encontrada.")
            
        df_novo['Arquivo_Origem'] = uploaded_file.name
        
        # Filtra apenas as colunas necessárias e preenche vazios
        df_novo = df_novo.reindex(columns=colunas_padrao).fillna("")
        
        st.info(f"Arquivo processado: {len(df_novo)} linhas prontas para envio.")
        
        if st.button("🚀 Enviar e Acumular no Google Sheets"):
            with st.spinner("Enviando para a nuvem..."):
                valores_atuais = sheet.get_all_values()
                
                # Se a planilha estiver limpa, injeta a linha de títulos primeiro
                if len(valores_atuais) == 0:
                    sheet.append_row(colunas_padrao)
                
                dados_para_enviar = df_novo.values.tolist()
                
                if len(dados_para_enviar) > 0:
                    sheet.append_rows(dados_para_enviar, value_input_option="USER_ENTERED")
                    st.balloons()
                    st.success(f"✅ Sucesso! {len(dados_para_enviar)} linhas enviadas à Planilha Mestra.")
                else:
                    st.warning("O arquivo não continha dados válidos para enviar.")
                    
    except Exception as e:
        st.error(f"❌ Erro crítico ao processar o CSV: {e}")

# --- VISUALIZAÇÃO DOS DADOS ACUMULADOS ---
st.write("---")
st.subheader("🔍 Filtros e Relatórios de Auditoria")

if conexao_ok:
    try:
        # Usa um método mais forte para buscar dados que ignora falhas de cabeçalho
        todas_linhas = sheet.get_all_values()
        
        # Checa se existe mais do que apenas a linha de cabeçalho (Linha 1)
        if len(todas_linhas) > 1:
            # Transforma as linhas brutas em tabela usando a linha 0 como títulos
            df_historico = pd.DataFrame(todas_linhas[1:], columns=todas_linhas[0])
            
            # Limpa caso os títulos tenham se duplicado no meio dos dados
            df_historico = df_historico[df_historico['Chave do Item'] != 'Chave do Item']
            
            # Filtros dinâmicos
            if 'Componentes' in df_historico.columns:
                lista_componentes = df_historico['Componentes'].dropna().unique()
                lista_componentes = [c for c in lista_componentes if str(c).strip() != ""]
                
                if len(lista_componentes) > 0:
                    comp_selecionado = st.multiselect("Filtrar por Componente:", lista_componentes, default=lista_componentes)
                    df_filtrado = df_historico[df_historico['Componentes'].isin(comp_selecionado)].copy()
                else:
                    df_filtrado = df_historico.copy()
            else:
                df_filtrado = df_historico.copy()
                
            # Agrupamentos para o relatório
            if 'Horas' in df_filtrado.columns and 'Responsável' in df_filtrado.columns:
                df_filtrado['Horas'] = pd.to_numeric(df_filtrado['Horas'], errors='coerce').fillna(0)
                resumo = df_filtrado.groupby(['Componentes', 'Responsável', 'Mes'])['Horas'].sum().reset_index()
                
                def formatar_horas(decimal):
                    horas = int(decimal)
                    minutos = int((decimal - horas) * 60)
                    return f"{horas}h {minutos}m"
                    
                resumo['Tempo Total'] = resumo['Horas'].apply(formatar_horas)
                st.dataframe(resumo[['Componentes', 'Responsável', 'Mes', 'Tempo Total']], use_container_width=True)
            else:
                st.warning("A planilha do Google Sheets perdeu as colunas de 'Horas' ou 'Responsável'.")
        else:
            st.info("A planilha no Google Sheets está limpa. Faça o primeiro upload acima!")
            
    except Exception as e:
        # Mostra o erro real em vez de esconder!
        st.error(f"❌ Erro ao tentar renderizar o histórico na tela: {e}")
