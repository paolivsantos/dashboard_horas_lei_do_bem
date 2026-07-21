import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Dashboard Lei do Bem", layout="wide")
st.title("📊 Centralizador Lei do Bem (JIRA -> Sheets)")

# --- CONFIGURAÇÃO ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/10Ju9R5RylNF6HHK_oV-NBZijjIVYVhrnACrctAycjzk/edit?gid=0#gid=0"

# Mapeamento consolidado de RR
MAPEAMENTO_RR = {
    "Alescia Fernandes": "84654", "Anderson Batista Da Costa": "85236", "Anderson Lazaro Gomes Oliva": "78172",
    "Bruno Rafael Borges Beltrao Moiteiro": "84437", "Dyonathan Jordan": "86281", "Gabriel Shioda Lima": "86618",
    "Glaucia Hiromi Mekaru": "84452", "Guilherme Oliver Barreira": "85338", "Jorge Luiz dos Santos": "86238",
    "José Clailton Menezes Jorge": "85479", "Lucas De Maria Godinho": "85224", "Lucas Martinez": "84515",
    "Rafael Ferreira Da Silva": "85051", "Reinaldo Marques": "82927", "Ronaldo de Souza Maciel": "84162",
    "Vinicius Freire de Oliveira": "85499", "Vittor Strefezzi": "85335", "Willian Kenji Hira": "85217"
}

# Mapeamento de Descrição da Atividade
MAPEAMENTO_DESCRICAO = {
    "Alescia Fernandes": "Desenvolvedora Front-end",
    "Anderson Batista Da Costa": "Desenvolvedor Front-end",
    "Anderson Lazaro Gomes Oliva": "Analista de Testes",
    "Bruno Rafael Borges Beltrao Moiteiro": "Arquiteto de Sistemas",
    "Dyonathan Jordan": "Analista de Testes",
    "Gabriel Shioda Lima": "Desenvolvedor Front-end",
    "Glaucia Hiromi Mekaru": "Desenvolvedora Back-end",
    "Guilherme Oliver Barreira": "Analista de Testes",
    "Jorge Luiz dos Santos": "Desenvolvedor Front-end",
    "José Clailton Menezes Jorge": "Desenvolvedor Back-end",
    "Lucas De Maria Godinho": "UX/UI Designer",
    "Lucas Martinez": "UX/UI Designer",
    "Rafael Ferreira Da Silva": "Desenvolvedor Front-end",
    "Reinaldo Marques": "Analista de Testes",
    "Ronaldo de Souza Maciel": "Especialista Front-end",
    "Vinicius Freire de Oliveira": "Desenvolvedor Back-end",
    "Vittor Strefezzi": "Desenvolvedor Back-end",
    "Willian Kenji Hira": "Desenvolvedor Front-end"
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

# Função para converter datas do JIRA em português (ex: '09/fev/26')
def converter_data_jira(serie_datas):
    if serie_datas is None:
        return pd.Series([pd.NaT] * len(serie_datas)) if hasattr(serie_datas, '__len__') else pd.NaT
    
    meses_pt_to_en = {
        'jan': 'Jan', 'fev': 'Feb', 'mar': 'Mar', 'abr': 'Apr', 
        'mai': 'May', 'jun': 'Jun', 'jul': 'Jul', 'ago': 'Aug', 
        'set': 'Sep', 'out': 'Oct', 'nov': 'Nov', 'dez': 'Dec'
    }
    
    def parse_unico(val):
        if pd.isna(val) or str(val).strip() == "":
            return pd.NaT
        s = str(val).strip().lower()
        for pt, en in meses_pt_to_en.items():
            s = s.replace(pt, en)
        return pd.to_datetime(s, errors='coerce', format='mixed')

    return serie_datas.apply(parse_unico)

# --- PROCESSAMENTO NO UPLOAD ---
uploaded_file = st.file_uploader("Suba o CSV do JIRA", type=["csv"])

if uploaded_file and conexao_ok:
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine='python')
        
        # Normaliza nomes de colunas
        df.columns = [c.strip() for c in df.columns]
        if 'Σ de Tempo Gasto' in df.columns and '∑ de tempo gasto' not in df.columns:
            df['∑ de tempo gasto'] = df['Σ de Tempo Gasto']
            
        # Calcula as horas aplicando o arredondamento para inteiro
        df['Horas'] = (pd.to_numeric(df.get('Tempo gasto', 0), errors='coerce').fillna(0) / 3600.0).round().astype(int)
        
        # Data de criação para referência
        if 'Criado' in df.columns:
            dt_criado_conv = converter_data_jira(df['Criado'])
            df['Data'] = dt_criado_conv.dt.strftime('%Y-%m-%d').fillna(df['Criado'].astype(str))
        else:
            df['Data'] = ""

        # Regra do Mês baseada estritamente em 'Resolvido' (com 'Criado' de fallback)
        meses_pt = {
            1: 'JAN', 2: 'FEV', 3: 'MAR', 4: 'ABR', 5: 'MAI', 6: 'JUN',
            7: 'JUL', 8: 'AGO', 9: 'SET', 10: 'OUT', 11: 'NOV', 12: 'DEZ'
        }
        
        datas_base = pd.Series([pd.NaT] * len(df))
        if 'Resolvido' in df.columns:
            datas_base = converter_data_jira(df['Resolvido'])
            
        if 'Criado' in df.columns:
            datas_criado_alt = converter_data_jira(df['Criado'])
            datas_base = datas_base.fillna(datas_criado_alt)

        num_mes = datas_base.dt.month
        df['Mes'] = [meses_pt[int(m)] if pd.notnull(m) else "" for m in num_mes]
            
        df['Arquivo_Origem'] = uploaded_file.name
        
        rename_map = {}
        if 'Chave da item' in df.columns:
            rename_map['Chave da item'] = 'Chave do Item'
        if 'ID da item' in df.columns:
            rename_map['ID da item'] = 'ID do Item'
        df = df.rename(columns=rename_map)

        for col in colunas_padrao:
            if col not in df.columns:
                df[col] = ""
                
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
            
            # Limpeza e arredondamento das horas lidas da planilha
            if 'Horas' in df_hist.columns:
                df_hist['Horas'] = (
                    df_hist['Horas']
                    .astype(str)
                    .str.replace('.', '', regex=False)
                    .str.replace(',', '.', regex=False)
                )
                df_hist['Horas'] = pd.to_numeric(df_hist['Horas'], errors='coerce').fillna(0).round()
            else:
                df_hist['Horas'] = 0

            df_hist['RR'] = df_hist['Responsável'].map(MAPEAMENTO_RR).fillna("N/A")
            df_hist['Descrição de Atividade'] = df_hist['Responsável'].map(MAPEAMENTO_DESCRICAO).fillna("Outros")
            df_hist = df_hist[df_hist['Chave do Item'] != 'Chave do Item']
            
            # Recalcula e normaliza dinamicamente o mês de cada linha
            def normalizar_mes(row):
                for col in ['Resolvido', 'Criado', 'Data']:
                    if col in row and str(row[col]).strip() != "":
                        dt = converter_data_jira(pd.Series([row[col]]))[0]
                        if pd.notnull(dt):
                            m_map = {1: 'JAN', 2: 'FEV', 3: 'MAR', 4: 'ABR', 5: 'MAI', 6: 'JUN',
                                     7: 'JUL', 8: 'AGO', 9: 'SET', 10: 'OUT', 11: 'NOV', 12: 'DEZ'}
                            return m_map.get(dt.month, "")
                val_atual = str(row.get('Mes', '')).upper()
                for m in ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']:
                    if m in val_atual:
                        return m
                return ""

            df_hist['Mes_Normalizado'] = df_hist.apply(normalizar_mes, axis=1)
            df_hist = df_hist[df_hist['Mes_Normalizado'].isin(['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ'])]

            if not df_hist.empty:
                pivot = pd.pivot_table(
                    df_hist, 
                    values='Horas', 
                    index=['Componentes', 'Responsável', 'RR', 'Descrição de Atividade'], 
                    columns='Mes_Normalizado', 
                    aggfunc='sum', 
                    fill_value=0
                )
                
                # Garante os 12 meses em ordem exata
                ordem_meses_fixa = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
                pivot = pivot.reindex(columns=ordem_meses_fixa, fill_value=0)

                # Adiciona totalizador por linha
                pivot['Total'] = pivot.sum(axis=1)
                
                # Estilização visual (cores nas células com horas inteiras)
                def destacar_celulas(val):
                    if isinstance(val, (int, float)) and val > 0:
                        return 'background-color: #e6f4ea; color: #137333; font-weight: bold;'
                    return ''

                pivot_estilizado = pivot.style.format("{:.0f}").map(destacar_celulas)
                
                st.dataframe(pivot_estilizado, use_container_width=True)
            else:
                st.info("Nenhum dado válido para exibição na matriz.")
        else:
            st.info("Planilha vazia.")
    except Exception as e:
        st.error(f"Erro na visualização: {e}")
