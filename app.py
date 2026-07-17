import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Dashboard Lei do Bem", layout="wide")
st.title("📊 Centralizador Lei do Bem (JIRA -> Sheets)")

# 👇👇👇 COLE O LINK DA SUA PLANILHA AQUI DENTRO DAS ASPAS 👇👇👇
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1LKu-e1vVlTZ6NxMXO0MmTt-WqC2_iCRYF1mN8M0WIK8/edit?gid=0#gid=0"

# Trava de segurança para garantir que você colou o link
if URL_PLANILHA == "COLE_AQUI_A_URL_DA_SUA_PLANILHA":
    st.error("⚠️ PARE! Edite o arquivo app.py e coloque o link real da sua planilha na variável URL_PLANILHA.")
    st.stop()

# --- Autenticação ---
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
    
    # Agora a conexão é cirúrgica e não tem como errar de arquivo
    sheet = client.open_by_url(URL_PLANILHA).worksheet("Dados_Acumulados")
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
        df_novo = pd.read_csv(uploaded_file, sep=None, engine='python')
        
        if 'Tempo gasto' not in df_novo.columns:
            st.error("⚠️ A coluna 'Tempo gasto' não existe no CSV.")
        else:
            df_novo['Horas'] = pd.to_numeric(df_novo['Tempo gasto'], errors='coerce').fillna(0) / 3600
            
            if 'Criado' in df_novo.columns:
                datas_convertidas = pd.to_datetime(df_novo['Criado'], errors='coerce', format='mixed')
                df_novo['Data'] = datas_convertidas.fillna(df_novo['Criado']).astype(str)
                df_novo['Mes'] = datas_convertidas.dt.strftime('%m/%Y').fillna(df_novo['Criado'].astype(str).str[3:10])
            else:
                df_novo['Data'], df_novo['Mes'] = "", ""
            
            df_novo['Arquivo_Origem'] = uploaded_file.name
            df_novo = df_novo.reindex(columns=colunas_padrao).fillna("")
            
            # BLINDAGEM DE TIPO: Converte absolutamente tudo para string pura antes de ir para o JSON do Sheets
            df_novo = df_novo.astype(str)
            dados_para_enviar = df_novo.values.tolist()
            
            st.info(f"Pré-processamento concluído: {len(dados_para_enviar)} linhas prontas para envio.")
            
            # Botão fora de formulários para garantir disparo limpo
            if st.button("🚀 CLIQUE AQUI PARA ENVIAR AO GOOGLE SHEETS"):
                with st.spinner("Conectando na URL da planilha e salvando dados..."):
                    
                    todas_linhas = sheet.get_all_values()
                    linhas_com_conteudo = [linha for linha in todas_linhas if any(str(c).strip() for c in linha)]
                    
                    if len(linhas_com_conteudo) == 0 or "Componentes" not in linhas_com_conteudo[0]:
                        sheet.clear()
                        sheet.append_row(colunas_padrao)
                        
                    if len(dados_para_enviar) > 0:
                        sheet.append_rows(dados_para_enviar, value_input_option="USER_ENTERED")
                        st.success(f"✅ DADOS ENVIADOS COM SUCESSO! ({len(dados_para_enviar)} linhas)")
                        st.balloons()
                    else:
                        st.warning("O arquivo não possuía dados após o tratamento.")
                        
    except Exception as e:
        st.error(f"❌ Erro crítico: {e}")

# --- VISUALIZAÇÃO DOS DADOS ACUMULADOS ---
st.write("---")
st.subheader("🔍 Filtros e Relatórios de Auditoria")

if conexao_ok:
    try:
        todas_linhas = sheet.get_all_values()
        linhas_validas = [linha for linha in todas_linhas if any(str(c).strip() for c in linha)]
        
        if len(linhas_validas) > 1:
            cabecalhos = linhas_validas[0]
            dados_tabela = linhas_validas[1:]
            
            df_historico = pd.DataFrame(dados_tabela, columns=cabecalhos)
            df_historico = df_historico[df_historico['Chave do Item'] != 'Chave do Item']
            
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
            
            if 'Horas' in df_filtrado.columns and 'Responsável' in df_filtrado.columns:
                df_filtrado['Horas'] = pd.to_numeric(df_filtrado['Horas'].str.replace(',', '.'), errors='coerce').fillna(0)
                resumo = df_filtrado.groupby(['Componentes', 'Responsável', 'Mes'])['Horas'].sum().reset_index()
                
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
                st.warning("⚠️ As colunas 'Horas' ou 'Responsável' não foram detectadas na leitura.")
        else:
            st.info("📊 A planilha no Google Sheets está vazia.")
            
    except Exception as e:
        st.error(f"❌ Erro ao ler a planilha: {e}")
