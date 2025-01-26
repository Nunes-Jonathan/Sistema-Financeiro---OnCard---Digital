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
        .container {
            display: flex;
            justify-content: space-between;
        }
        .graph {
            background-color: #ffffff;
            padding: 20px;
            margin: 10px;
            border-radius: 10px;
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
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

    # Verificar se as tabelas necessárias estão presentes
    if "Data_Conclusao" in lancamentos.columns and "ID_Cliente" in lancamentos.columns and "ID_Cliente" in clientes.columns:
        # Processar os dados da tabela LANCAMENTOS
        lancamentos['Data_Conclusao'] = pd.to_datetime(lancamentos['Data_Conclusao'], errors='coerce')
        lancamentos = lancamentos.dropna(subset=['Data_Conclusao', 'ID_Cliente'])

        # Garantir que as colunas estão no formato correto
        lancamentos['ID_Cliente'] = lancamentos['ID_Cliente'].astype(str)
        clientes['ID_Cliente'] = clientes['ID_Cliente'].astype(str)
        clientes['Card_do_sistema'] = clientes['Card_do_sistema'].astype(str)

        # Criar uma coluna com Mês/Ano
        lancamentos['Mês/Ano'] = lancamentos['Data_Conclusao'].dt.to_period('M')

        # Filtrar apenas os IDs válidos cruzando com a tabela CLIENTES
        lancamentos = lancamentos[lancamentos['ID_Cliente'].isin(clientes['ID_Cliente'])]

        # Criar um dicionário de mapeamento entre Card_do_sistema e ID_Cliente
        card_to_id = clientes.set_index('Card_do_sistema')['ID_Cliente'].to_dict()

        # Filtro de Mês/Ano (seleção única ou múltipla)
        st.sidebar.write("### Filtros")
        meses_disponiveis = lancamentos['Mês/Ano'].dt.strftime('%b/%Y').unique()
        filtro_mes = st.sidebar.multiselect("Selecione o(s) Mês(es):", options=meses_disponiveis, default=meses_disponiveis)

        # Filtro de Clientes (Card_do_sistema no lugar de ID_Cliente)
        cards_disponiveis = list(card_to_id.keys())
        filtro_cards = st.sidebar.multiselect("Selecione o(s) Card(s) do Sistema:", options=cards_disponiveis, default=cards_disponiveis)

        # Mapear os cards selecionados para os IDs correspondentes
        clientes_filtrados = [card_to_id[card] for card in filtro_cards]

        # Aplicar filtros nos dados
        lancamentos_filtrados = lancamentos[
            (lancamentos['Mês/Ano'].dt.strftime('%b/%Y').isin(filtro_mes)) &
            (lancamentos['ID_Cliente'].isin(clientes_filtrados))
        ]

        # Verificar se a tabela DESPESAS está presente
        if "Valor" in despesas.columns and "Status" in despesas.columns:
            # Garantir que a coluna Valor é numérica
            despesas['Valor'] = pd.to_numeric(despesas['Valor'], errors='coerce')

            # Somar os valores para cada Status
            total_pago = despesas[despesas['Status'] == "Pago"]['Valor'].sum()
            total_pendente = despesas[despesas['Status'] == "Pendente"]['Valor'].sum()

            # Exibir os valores em cards
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(
                    f"""
                    <div class="card">
                        <h4>Despesas Pagas (R$)</h4>
                        <h2>{total_pago:,.2f}</h2>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f"""
                    <div class="card">
                        <h4>Despesas Pendentes (R$)</h4>
                        <h2>{total_pendente:,.2f}</h2>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error("As colunas 'Valor' e 'Status' não foram encontradas na tabela DESPESAS.")

        if not lancamentos_filtrados.empty:
            # Contar clientes únicos por Mês/Ano nos dados filtrados
            clientes_por_mes = lancamentos_filtrados.groupby('Mês/Ano')['ID_Cliente'].nunique().reset_index()
            clientes_por_mes.columns = ['Mês/Ano', 'Quantidade_Clientes']

            # Gerar um intervalo completo de meses com base nos dados filtrados
            meses_completos = pd.period_range(
                start=lancamentos_filtrados['Data_Conclusao'].min(),
                end=lancamentos_filtrados['Data_Conclusao'].max(),
                freq='M'
            )
            clientes_por_mes = clientes_por_mes.set_index('Mês/Ano').reindex(meses_completos, fill_value=0).reset_index()
            clientes_por_mes.columns = ['Mês/Ano', 'Quantidade_Clientes']

            # Converter Mês/Ano para string para exibição
            clientes_por_mes['Mês/Ano'] = clientes_por_mes['Mês/Ano'].dt.strftime('%b/%Y')

            # Exibir gráficos lado a lado
            col1, col2 = st.columns(2)

            with col1:
                st.write("### Gráfico de Clientes por Mês")
                fig1 = px.bar(
                    clientes_por_mes,
                    x='Mês/Ano',
                    y='Quantidade_Clientes',
                    title="Quantidade de Clientes por Mês",
                    labels={'Mês/Ano': 'Mês', 'Quantidade_Clientes': 'Quantidade de Clientes'},
                    text_auto=True,
                )
                fig1.update_layout(
                    xaxis_title="Mês",
                    yaxis_title="Quantidade de Clientes"
                )
                st.plotly_chart(fig1, use_container_width=True)

            with col2:
                st.write("### Gráfico de Fechamento Mensal")
                fechamento_mensal = lancamentos_filtrados.groupby('Mês/Ano')['Valor_Total'].sum().reset_index()
                fechamento_mensal.columns = ['Mês/Ano', 'Valor_Total']
                fechamento_mensal['Mês/Ano'] = fechamento_mensal['Mês/Ano'].dt.strftime('%b/%Y')
                fig2 = px.bar(
                    fechamento_mensal,
                    x='Mês/Ano',
                    y='Valor_Total',
                    title="Fechamento Mensal",
                    labels={'Mês/Ano': 'Mês', 'Valor_Total': 'Valor Total (R$)'},
                    text_auto=True,
                )
                fig2.update_layout(
                    xaxis_title="Mês",
                    yaxis_title="Valor Total (R$)"
                )
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível com os filtros selecionados.")
    
    
