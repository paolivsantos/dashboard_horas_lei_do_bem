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
    "Alescia Bezerra Fernandes": "84654", "Anderson Batista Da Costa": "85236", "Anderson Lazaro Gomes Oliva": "78172",
    "Bruno Rafael Borges Beltrao Moiteiro": "84437", "Dyonathan Jordan Do Nascimento Araujo": "86281", "Gabriel Shioda Lima": "86618",
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
        
        # Tratamento de Data de Criação (para manter o campo Data preenchido)
        if 'Criado' in df.columns:
            datas_criado = pd.to_datetime(df['Criado'], errors='coerce', format='mixed')
            df['Data'] = datas_criado.dt.strftime('%Y-%m-%d').fillna(df['Criado'].astype(str))
        else:
            df['Data'] = ""

        # Tratamento de Mês baseado primariamente na coluna 'Resolvido' 
        # (Se estiver em branco, usa a data 'Criado' como plano B)
        coluna_base_data = 'Resolvido' if 'Resolvido' in df.columns else 'Criado'
        if coluna_base_data in df.columns:
            datas_base = pd.to_datetime(df[coluna_base_data], errors='coerce', format='mixed')
            
            # Se 'Resolvido' estiver vazio para algum item, tenta preencher com 'Criado'
            if 'Resolvido' in df.columns and 'Criado' in df.columns:
                datas_criado_alt = pd.to_datetime(df['Criado'], errors='coerce', format='mixed')
                datas_base = datas_base.fillna(datas_criado_alt)

            meses_pt = {
                1: 'JAN', 2: 'FEV', 3: 'MAR', 4: 'ABR', 5: 'MAI', 6: 'JUN',
                7: 'JUL', 8: 'AGO', 9: 'SET', 10: 'OUT', 11: 'NOV', 12: 'DEZ'
            }
            num_mes = datas_base.dt.month
            ano_mes = datas_base.dt.year
            
            # Formata explicitamente como 'JAN/2026', 'FEV/2026', etc.
            df['Mes'] = [f"{meses_pt[int(m)]}/{int(a)}" if pd.notnull(m) and pd.notnull(a) else "" for m, a in zip(num_mes, ano_mes)]
        else:
            df['Mes'] = ""
            
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
            
            # Remove linhas onde a coluna Mes está vazia ou inválida
            df_hist = df_hist[df_hist['Mes'].str.contains('/', na=False)]
            
            if not df_hist.empty:
                # Cria colunas auxiliares de Ano e Mês numérico para ordenação correta na Pivot Table
                def extrair_ordenacao(val):
                    try:
                        partes = val.split('/')
                        mes_str, ano_str = partes[0], partes[1]
                        inv_meses = {'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6,
                                     'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12}
                        return int(ano_str) * 100 + inv_meses.get(mes_str, 0)
                    except:
                        return 0

                df_hist['Ord_Mes'] = df_hist['Mes'].apply(extrair_ordenacao)
                
                # Ordena o DataFrame base pelas colunas auxiliares para garantir a ordem cronológica nas colunas da tabela
                df_hist = df_hist.sort_values('Ord_Mes')
                
                # Pivot table utilizando a coluna 'Mes' formatada por extenso
                pivot = pd.pivot_table(
                    df_hist, 
                    values='Horas', 
                    index=['Componentes', 'Responsável', 'RR'], 
                    columns='Mes', 
                    aggfunc='sum', 
                    fill_value=0
                )
                
                # Reorganiza as colunas da pivot table em ordem cronológica estritamente correta
                colunas_ordenadas = sorted([c for c in pivot.columns if c != 'Total'], key=extrair_ordenacao)
                pivot = pivot[colunas_ordenadas]

                # Adiciona totalizador
                pivot['Total'] = pivot.sum(axis=1)
                
                # Estilização visual (mantendo as cores nas células com horas)
                def destacar_celulas(val):
                    if isinstance(val, (int, float)) and val > 0:
                        return 'background-color: #e6f4ea; color: #137333; font-weight: bold;'
                    return ''

                pivot_estilizado = pivot.style.format("{:.1f}").map(destacar_celulas)
                
                st.dataframe(pivot_estilizado, use_container_width=True)
            else:
                st.info("Nenhum dado com mês válido encontrado na planilha.")
        else:
            st.info("Planilha vazia.")
    except Exception as e:
        st.error(f"Erro na visualização: {e}")
