import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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
    st.sidebar.markdown("### Filtro por Período")

    data_min = lancamentos['Data_Conclusao'].min()
    data_max = lancamentos['Data_Conclusao'].max()

    data_inicial, data_final = st.sidebar.date_input(
        "Selecione o intervalo:",
        value=(data_min, data_max),
        min_value=data_min,
        max_value=data_max
    )
    cards_disponiveis = list(card_to_id.keys())
    filtro_cards = st.sidebar.multiselect("Selecione o(s) Card(s) do Sistema:", options=cards_disponiveis)

    # Se nada for selecionado, considerar todos
    if not filtro_cards:
        clientes_filtrados = list(card_to_id.values())
    else:
        clientes_filtrados = [card_to_id[card] for card in filtro_cards]

    lancamentos_filtrados = lancamentos[
        (lancamentos['Data_Conclusao'] >= pd.to_datetime(data_inicial)) &
        (lancamentos['Data_Conclusao'] <= pd.to_datetime(data_final)) &
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
    fechamento_apos_despesas = valor_liquido - total_pago_despesas

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

    fig_evolucao = go.Figure()
    fig_evolucao.add_trace(go.Scatter(
        x=evolucao['Mês/Ano'],
        y=evolucao['Evolução %'],
        mode='lines+markers+text',
        text=[f"{v:.2f}%" if pd.notnull(v) else "" for v in evolucao['Evolução %']],
        textposition='top center',
        line=dict(color='blue'),
        name='Evolução %'
    ))

    fig_evolucao.update_layout(
        title="Evolução Mensal (%)",
        xaxis_title="Mês",
        yaxis_title="Variação (%)",
        legend_title="Legenda"
    )

    st.plotly_chart(fig_evolucao, use_container_width=True)

    # Gráfico: Despesas x Receitas
    receitas_mensais = lancamentos_filtrados.groupby('Mês/Ano')['Valor_Pago'].sum().reset_index()
    despesas_mensais = despesas.groupby('Mês/Ano')['Valor'].sum().reset_index()
    comparativo = pd.merge(receitas_mensais, despesas_mensais, on='Mês/Ano', how='outer').fillna(0)
    comparativo = comparativo.rename(columns={
        'Valor_Pago': 'Receitas',
        'Valor': 'Despesas'
    })
    comparativo['Mês/Ano'] = comparativo['Mês/Ano'].dt.strftime('%b/%Y')

    fig_comparativo = go.Figure()

    # Adiciona a barra de Receitas
    fig_comparativo.add_trace(go.Bar(
        x=comparativo['Mês/Ano'],
        y=comparativo['Receitas'],
        name='Receitas',
        text=[f"R$ {v:,.2f}" for v in comparativo['Receitas']],
        textposition='auto',
        marker_color='green'
    ))

    # Adiciona a barra de Despesas
    fig_comparativo.add_trace(go.Bar(
        x=comparativo['Mês/Ano'],
        y=comparativo['Despesas'],
        name='Despesas',
        text=[f"R$ {v:,.2f}" for v in comparativo['Despesas']],
        textposition='auto',
        marker_color='red'
    ))

    fig_comparativo.update_layout(
        title="Receitas x Despesas",
        barmode='group',
        xaxis_title="Mês",
        yaxis_title="Valor (R$)",
        legend_title="Categoria"
    )

    st.plotly_chart(fig_comparativo, use_container_width=True)

    #Gráfico: Clientes por Mês
    clientes_por_mes = (
        lancamentos_filtrados
        .groupby(lancamentos_filtrados['Data_Conclusao'].dt.to_period('M'))['ID_Cliente']
        .nunique()
        .reset_index()
    )
    clientes_por_mes.columns = ['Mês/Ano', 'Quantidade_Clientes']
    clientes_por_mes['Mês/Ano'] = clientes_por_mes['Mês/Ano'].dt.strftime('%b/%Y')

    fig_clientes_mes = go.Figure()
    fig_clientes_mes.add_trace(go.Bar(
        x=clientes_por_mes['Mês/Ano'],
        y=clientes_por_mes['Quantidade_Clientes'],
        text=[f"{int(v)}" for v in clientes_por_mes['Quantidade_Clientes']],
        textposition='auto',
        marker_color='steelblue',
        name='Clientes'
    ))
    fig_clientes_mes.update_layout(
        title="Quantidade de Clientes por Mês",
        xaxis_title="Mês",
        yaxis_title="Nº de Clientes"
    )
    st.plotly_chart(fig_clientes_mes, use_container_width=True)

    #Gráfico: Fechamento Mensal
    fechamento_mensal = (
        lancamentos_filtrados
        .groupby(lancamentos_filtrados['Data_Conclusao'].dt.to_period('M'))['Valor_Liquido']
        .sum()
        .reset_index()
    )
    fechamento_mensal.columns = ['Mês/Ano', 'Valor_Total']
    fechamento_mensal['Mês/Ano'] = fechamento_mensal['Mês/Ano'].dt.strftime('%b/%Y')

    fig_fechamento = go.Figure()
    fig_fechamento.add_trace(go.Bar(
        x=fechamento_mensal['Mês/Ano'],
        y=fechamento_mensal['Valor_Total'],
        text=[f"R$ {v:,.2f}" for v in fechamento_mensal['Valor_Total']],
        textposition='auto',
        marker_color='teal',
        name='Fechamento'
    ))
    fig_fechamento.update_layout(
        title="Fechamento Mensal (Valor Líquido)",
        xaxis_title="Mês",
        yaxis_title="Valor Total (R$)"
    )
    st.plotly_chart(fig_fechamento, use_container_width=True)


    # Gráfico: Cancelamentos por mês
    cancelamentos = lancamentos_filtrados.dropna(subset=['Data_Cancelamento'])
    cancelamentos['Mês_Cancelamento'] = cancelamentos['Data_Cancelamento'].dt.to_period('M')
    cancelamentos_por_mes = cancelamentos.groupby('Mês_Cancelamento')['ID_Cliente'].nunique().reset_index()
    cancelamentos_por_mes.columns = ['Mês/Ano', 'Cancelamentos']
    cancelamentos_por_mes['Mês/Ano'] = cancelamentos_por_mes['Mês/Ano'].dt.strftime('%b/%Y')

    fig_cancel = go.Figure()
    fig_cancel.add_trace(go.Bar(
        x=cancelamentos_por_mes['Mês/Ano'],
        y=cancelamentos_por_mes['Cancelamentos'],
        text=[f"{int(v)}" for v in cancelamentos_por_mes['Cancelamentos']],
        textposition='auto',
        marker_color='orange',
        name='Cancelamentos'
    ))

    fig_cancel.update_layout(
        title="Clientes que Cancelaram por Mês",
        xaxis_title="Mês",
        yaxis_title="Quantidade de Cancelamentos",
        legend_title="Legenda"
    )

    st.plotly_chart(fig_cancel, use_container_width=True)

    # Tabela: Nome e telefone
    clientes_info = lancamentos_filtrados[['ID_Cliente']].drop_duplicates().merge(
        clientes[['ID_Cliente', 'Nome_Completo', 'Telefone_Principal']],
        on='ID_Cliente', how='left'
    )
    st.write("### Lista de Clientes com Telefone")
    st.dataframe(clientes_info)
