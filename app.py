import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Dashboard Lei do Bem", layout="wide")
st.title("📊 Centralizador Lei do Bem (JIRA -> Sheets)")

# Conexão nativa com o Google Sheets utilizando os Secrets salvos
conn = st.connection("gsheets", type=GSheetsConnection)

# Upload do CSV mensal exportado do JIRA
uploaded_file = st.file_uploader("Suba o CSV de um Componente do JIRA", type=["csv"])

if uploaded_file:
    # Lendo o arquivo do JIRA
    df_novo = pd.read_csv(uploaded_file)
    
    # Tratamento dos dados e criação das colunas extras calculadas
    df_novo['Horas'] = df_novo['Tempo gasto'] / 3600
    
    # Conversão robusta da data para evitar o DateParseError
    df_novo['Data'] = pd.to_datetime(df_novo['Criado'], errors='coerce', format='mixed')
    
    # Criação do campo de Mês formatado (MM/AAAA) - Remove linhas onde a data falhou completamente
    df_novo = df_novo.dropna(subset=['Data']).copy()
    df_novo['Mes'] = df_novo['Data'].dt.strftime('%m/%Y')
    
    # Registra o nome do arquivo de origem para rastreabilidade na auditoria
    df_novo['Arquivo_Origem'] = uploaded_file.name
    
    st.success(f"Arquivo '{uploaded_file.name}' carregado! {len(df_novo)} linhas processadas com sucesso.")
    
    # Botão para salvar no Google Sheets de forma acumulada
    if st.button("🚀 Enviar e Acumular no Google Sheets"):
        try:
            # Tenta ler o histórico para empilhar os novos dados
            base_existente = conn.read(worksheet="Dados_Acumulados")
            base_atualizada = pd.concat([base_existente, df_novo], ignore_index=True)
        except:
            # Caso a planilha esteja limpa/vazia ou seja o primeiro upload
            base_atualizada = df_novo

        # BLINDAGEM: Converte tipos complexos de data/timestamp para texto simples antes do envio.
        # O Google Sheets não aceita objetos de data puros do Python através desse conector básico.
        if 'Data' in base_atualizada.columns:
            base_atualizada['Data'] = base_atualizada['Data'].astype(str)
            
        # Garante que todos os dados nulos sejam strings vazias para não quebrar a serialização JSON
        base_atualizada = base_atualizada.fillna("")
            
        # Atualiza a planilha mestra no Google Drive
        conn.update(worksheet="Dados_Acumulados", data=base_atualizada)
        st.balloons()
        st.success("Dados integrados à Planilha Mestra com sucesso!")

# --- VISUALIZAÇÃO DOS DADOS ACUMULADOS ---
st.write("---")
st.subheader("🔍 Filtros e Relatórios de Auditoria")

try:
    # Sempre busca a versão em tempo real do Sheets para montar os gráficos e tabelas
    df_historico = conn.read(worksheet="Dados_Acumulados")
    
    if not df_historico.empty:
        # Filtros na tela dinâmicos
        lista_componentes = df_historico['Componentes'].dropna().unique()
        comp_selecionado = st.multiselect("Filtrar por Componente:", lista_componentes, default=lista_componentes)
        
        # Aplicando filtros selecionados pelo usuário
        df_filtrado = df_historico[df_historico['Componentes'].isin(comp_selecionado)]
        
        # Garante que a coluna Horas seja numérica para o agrupamento funcionar caso tenha voltado como texto
        df_filtrado['Horas'] = pd.to_numeric(df_filtrado['Horas'], errors='coerce').fillna(0)
        
        # Exibição do resumo consolidado em horas para a Lei do Bem
        resumo = df_filtrado.groupby(['Componentes', 'Responsável', 'Mes'])['Horas'].sum().reset_index()
        
        # Formatação amigável de horas decimais para o formato Xh Ym
        def formatar_horas(decimal):
            horas = int(decimal)
            minutos = int((decimal - horas) * 60)
            return f"{horas}h {minutos}m"
            
        resumo['Tempo Total'] = resumo['Horas'].apply(formatar_horas)
        
        # Mostra a tabela final estruturada na tela
        st.dataframe(resumo[['Componentes', 'Responsável', 'Mes', 'Tempo Total']], use_container_width=True)
    else:
        st.info("A planilha no Google Sheets está vazia. Faça o primeiro upload acima!")
    
except Exception as e:
    st.info("Aguardando o primeiro upload para estruturar e exibir o histórico consolidado.")
