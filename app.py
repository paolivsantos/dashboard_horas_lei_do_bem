import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Dashboard Lei do Bem", layout="wide")
st.title("📊 Centralizador Lei do Bem (JIRA -> Sheets)")

# --- CONFIGURAÇÃO ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/10Ju9R5RylNF6HHK_oV-NBZijjIVYVhrnACrctAycjzk/edit?gid=0#gid=0"

# Mapeamento consolidado
MAPEAMENTO_RR = {
    "Alescia Fernandes": "84654", "Anderson Batista Da Costa": "85236", "Anderson Lazaro Gomes Oliva": "78172",
    "Bruno Rafael Borges Beltrao Moiteiro": "84437", "Dyonathan Jordan": "86281", "Gabriel Shioda Lima": "86618",
    "Glaucia Hiromi Mekaru": "84452", "Guilherme Oliver Barreira": "85338", "Jorge Luiz dos Santos": "86238",
    "José Clailton Menezes Jorge": "85479", "Lucas De Maria Godinho": "85224", "Lucas Martinez": "84515",
    "Rafael Ferreira Da Silva": "85051", "Reinaldo Marques": "82927", "Ronaldo de Souza Maciel": "84162",
    "Vinicius Freire de Oliveira": "85499", "Vittor Strefezzi": "85335", "Willian Kenji Hira": "85217"
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

colunas_padrao = [
    "Chave do Item", "ID do Item", "Resumo", "Componentes", "Tempo gasto",
    "∑ de tempo gasto", "Responsável", "ID do responsável", "Criado", "Resolvido",
    "Status", "Horas", "Data", "Mes", "Arquivo_Origem"
]

# --- PROCESSAMENTO NO UPLOAD ---
uploaded_file = st.file_uploader("Suba o CSV do JIRA", type=["csv"])

if uploaded_file and conexao_ok:
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine='python')
        df['Horas'] = pd.to_numeric(df.get('Tempo gasto', 0), errors='coerce').fillna(0) / 3600
        
        # Tratamento rigoroso de data para garantir o mês correto
        if 'Criado' in df.columns:
            datas_convertidas = pd.to_datetime(df['Criado'], errors='coerce', format='mixed')
            df['Data'] = datas_convertidas.dt.strftime('%Y-%m-%d').fillna(df['Criado'].astype(str))
            
            # Dicionário para traduzir o mês numérico para abreviação em português
            meses_pt = {
                01/2026: 'JAN', 02/2026: 'FEV', 03/2026: 'MAR', 04/2026: 'ABR', 05/2026: 'MAI', 06/2026: 'JUN',
                07/2026: 'JUL', 08/2026: 'AGO', 09/2026: 'SET', 10/2026: 'OUT', 11/2026: 'NOV', 12/2026: 'DEZ'
            }
            num_mes = datas_convertidas.dt.month
            ano_mes = datas_convertidas.dt.year
            df['Mes'] = num_mes.map(meses_pt) + '/' + ano_mes.astype(str)
        else:
            df['Data'], df['Mes'] = "", ""
            
        df['Arquivo_Origem'] = uploaded_file.name
        df = df.reindex(columns=colunas_padrao).fillna("")
        df_envio = df.astype(str)
        
        if st.button("🚀 ENVIAR PARA PLANILHA"):
            sheet.append_rows(df_envio.values.tolist(), value_input_option="USER_ENTERED")
            st.success("Dados enviados com sucesso!")
            st.balloons()
    except Exception as e:
        st.error(f"Erro no processamento: {e}")

# --- RELATÓRIO MATRICIAL ---
st.write("---")
st.subheader("📅 Matriz de Horas por Componente, Responsável e Mês")

if conexao_ok:
    try:
        dados = sheet.get_all_values()
        if len(dados) > 1:
            cabecalhos_uteis = [c for c in dados[0] if c.strip() != '']
            dados_limpos = [linha[:len(cabecalhos_uteis)] for linha in dados[1:]]
            df_hist = pd.DataFrame(dados_limpos, columns=cabecalhos_uteis)
            
            # Limpeza
            df_hist['Horas'] = pd.to_numeric(df_hist['Horas'].str.replace(',', '.'), errors='coerce').fillna(0)
            df_hist['RR'] = df_hist['Responsável'].map(MAPEAMENTO_RR).fillna("N/A")
            
            # Remove linhas de cabeçalho duplicadas que possam ter vindo do histórico antigo
            df_hist = df_hist[df_hist['Chave do Item'] != 'Chave do Item']
            
            # Pivot table com os meses por extenso
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
            
            # Estilização visual atualizada (.map em vez de .applymap)
            def destacar_celulas(val):
                if isinstance(val, (int, float)) and val > 0:
                    return 'background-color: #e6f4ea; color: #137333; font-weight: bold;'
                return ''

            pivot_estilizado = pivot.style.format("{:.1f}").map(destacar_celulas)
            
            st.dataframe(pivot_estilizado, use_container_width=True)
        else:
            st.info("Planilha vazia.")
    except Exception as e:
        st.error(f"Erro na visualização: {e}")
