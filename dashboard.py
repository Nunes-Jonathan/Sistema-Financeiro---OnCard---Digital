import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Financeiro", layout="wide")

st.markdown(
    """
    <style>
        .titulo-dash {
        font-size: 32px;
        font-weight: bold;
        text-align: center;
        color: #333333;
        padding: 20px;
        border-bottom: 2px solid #f0f0f0;
        }
        .card {
            background-color: #ffffff;
            padding: 20px;
            margin: 10px;
            border-radius: 10px;
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

upload_file = st.file_uploader("Carregar Arquivo Excel", type=["xlsx"])
if upload_file:
    data = pd.ExcelFile(upload_file)
    lancamentos = data.parse("LANCAMENTOS")
    clientes = data.parse("CLIENTES")
    despesas = data.parse("DESPESAS")

    st.markdown('<div class="titulo-dash"> Dashboard Financeiro - Sistema OnCard - Digital</div>', unsafe_allow_html=True)

    lancamentos['Data_Conclusao'] = pd.to_datetime(lancamentos['Data_Conclusao'], errors='coerce')
    lancamentos['Data_Cancelamento'] = pd.to_datetime(lancamentos['Data_Cancelamento'], errors='coerce')
    lancamentos['Data_Pagamento'] = pd.to_datetime(lancamentos['Data_Pagamento'], errors='coerce')
    lancamentos = lancamentos.dropna(subset=['Data_Conclusao', 'ID_Cliente'])

    lancamentos['ID_Cliente'] = lancamentos['ID_Cliente'].astype(str)
    clientes['ID_Cliente'] = clientes['ID_Cliente'].astype(str)
    clientes['Card_do_sistema'] = clientes['Card_do_sistema'].astype(str)

    lancamentos['Mês/Ano'] = lancamentos['Data_Conclusao'].dt.to_period('M')
    lancamentos = lancamentos[lancamentos['ID_Cliente'].isin(clientes['ID_Cliente'])]

    card_to_id = clientes.set_index('Card_do_sistema')['ID_Cliente'].to_dict()

    st.sidebar.write("### Filtros")
    meses_disponiveis = lancamentos['Mês/Ano'].dt.strftime('%b/%Y').unique()
    filtro_mes = st.sidebar.multiselect("Selecione o(s) Mês(es):", options=meses_disponiveis, default=meses_disponiveis)
    cards_disponiveis = list(card_to_id.keys())
    filtro_cards = st.sidebar.multiselect("Selecione o(s) Card(s) do Sistema:", options=cards_disponiveis, default=cards_disponiveis)
    clientes_filtrados = [card_to_id[card] for card in filtro_cards]

    lancamentos_filtrados = lancamentos[
        (lancamentos['Mês/Ano'].dt.strftime('%b/%Y').isin(filtro_mes)) &
        (lancamentos['ID_Cliente'].isin(clientes_filtrados))
    ].copy()

    # Conversões numéricas
    lancamentos_filtrados['Valor_Pago'] = pd.to_numeric(lancamentos_filtrados['Valor_Pago'], errors='coerce')
    lancamentos_filtrados['Taxa'] = pd.to_numeric(lancamentos_filtrados['Taxa'], errors='coerce')
    lancamentos_filtrados['Valor_Liquido'] = pd.to_numeric(lancamentos_filtrados['Valor_Liquido'], errors='coerce')

    despesas['Valor'] = pd.to_numeric(despesas['Valor'], errors='coerce')
    despesas['Vencim.'] = pd.to_datetime(despesas['Vencim.'], errors='coerce')
    despesas['Mês/Ano'] = despesas['Vencim.'].dt.to_period('M')

    # Cálculos principais
    faturamento_bruto = lancamentos_filtrados['Valor_Pago'].sum()
    valor_total_taxas = lancamentos_filtrados['Taxa'].sum()
    valor_liquido = lancamentos_filtrados['Valor_Liquido'].sum()
    qtd_clientes = lancamentos_filtrados['ID_Cliente'].nunique()
    ticket_medio = faturamento_bruto / qtd_clientes if qtd_clientes > 0 else 0
    total_pago_despesas = despesas[despesas['Status'].str.upper() == "PAGO"]['Valor'].sum()
    total_pendente_despesas = despesas[despesas['Status'].str.upper() == "PENDENTE"]['Valor'].sum()
    fechamento_apos_despesas = faturamento_bruto - total_pago_despesas

    # Cards principais
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="card"><h4>Faturamento Bruto</h4><h2>R$ {faturamento_bruto:,.2f}</h2></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="card"><h4>Taxas Totais</h4><h2>R$ {valor_total_taxas:,.2f}</h2></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="card"><h4>Valor Líquido</h4><h2>R$ {valor_liquido:,.2f}</h2></div>""", unsafe_allow_html=True)

    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown(f"""<div class="card"><h4>Ticket Médio</h4><h2>R$ {ticket_medio:,.2f}</h2></div>""", unsafe_allow_html=True)
    with col5:
        st.markdown(f"""<div class="card"><h4>Despesas Pagas</h4><h2>R$ {total_pago_despesas:,.2f}</h2></div>""", unsafe_allow_html=True)
    with col6:
        st.markdown(f"""<div class="card"><h4>Fechamento Pós-Despesas</h4><h2>R$ {fechamento_apos_despesas:,.2f}</h2></div>""", unsafe_allow_html=True)

    # Gráfico: Evolução mensal (%)
    evolucao = lancamentos_filtrados.groupby('Mês/Ano')['Valor_Liquido'].sum().reset_index().sort_values('Mês/Ano')
    evolucao['Evolução %'] = evolucao['Valor_Liquido'].pct_change() * 100
    evolucao['Mês/Ano'] = evolucao['Mês/Ano'].dt.strftime('%b/%Y')

    fig_evolucao = px.line(evolucao, x='Mês/Ano', y='Evolução %', title='Evolução Mensal (%)')
    st.plotly_chart(fig_evolucao, use_container_width=True)

    # Gráfico: Despesas x Receitas
    receitas_mensais = lancamentos_filtrados.groupby('Mês/Ano')['Valor_Pago'].sum().reset_index()
    despesas_mensais = despesas.groupby('Mês/Ano')['Valor'].sum().reset_index()
    comparativo = pd.merge(receitas_mensais, despesas_mensais, on='Mês/Ano', how='outer').fillna(0)
    comparativo['Mês/Ano'] = comparativo['Mês/Ano'].dt.strftime('%b/%Y')

    fig_comparativo = px.bar(comparativo, x='Mês/Ano', y=['Valor_Pago', 'Valor'], barmode='group',
                             title='Receitas x Despesas', labels={'value': 'Valor (R$)', 'variable': 'Categoria'})
    st.plotly_chart(fig_comparativo, use_container_width=True)

    # Gráfico: Cancelamentos por mês
    cancelamentos = lancamentos_filtrados.dropna(subset=['Data_Cancelamento'])
    cancelamentos['Mês_Cancelamento'] = cancelamentos['Data_Cancelamento'].dt.to_period('M')
    cancelamentos_por_mes = cancelamentos.groupby('Mês_Cancelamento')['ID_Cliente'].nunique().reset_index()
    cancelamentos_por_mes.columns = ['Mês/Ano', 'Cancelamentos']
    cancelamentos_por_mes['Mês/Ano'] = cancelamentos_por_mes['Mês/Ano'].dt.strftime('%b/%Y')

    fig_cancel = px.bar(cancelamentos_por_mes, x='Mês/Ano', y='Cancelamentos',
                        title="Clientes que Cancelaram por Mês")
    st.plotly_chart(fig_cancel, use_container_width=True)

    # Tabela: Nome e telefone
    clientes_info = lancamentos_filtrados[['ID_Cliente']].drop_duplicates().merge(
        clientes[['ID_Cliente', 'Nome_Completo', 'Telefone_Principal']],
        on='ID_Cliente', how='left'
    )
    st.write("### Lista de Clientes com Telefone")
    st.dataframe(clientes_info)
