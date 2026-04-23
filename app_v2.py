import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import base64
import json

# =========================
# CONFIGURAÇÕES E ESTILO
# =========================
st.set_page_config(
    page_title="Viveiro Pro V2 - Gestão Inteligente",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Customizado para um visual moderno
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #2e7d32; color: white; font-weight: bold; }
    .stMetric { background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #eee; }
    [data-testid="stSidebar"] { background-color: #1b5e20; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: white; color: #6c757d; text-align: center; padding: 10px; font-size: 12px; border-top: 1px solid #dee2e6; z-index: 100; }
    .card { background-color: white; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# =========================
# CONEXÃO SUPABASE
# =========================
url = "https://qkjukxdnufuvrzezrxue.supabase.co"
key = "sb_publishable_OYkUUp3VGWDWL3ztH8zqig_sZrkIY8R"

@st.cache_resource
def get_supabase():
    try: return create_client(URL, KEY)
    except: return None

supabase = get_supabase()

# =========================
# FUNÇÕES AUXILIARES
# =========================
def format_currency(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_date_br(date_obj):
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.fromisoformat(date_obj.split('T')[0])
        except:
            return date_obj
    return date_obj.strftime("%d/%m/%Y")

def generate_pdf(df_est, df_ven, resumo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 15, "RELATORIO DE GESTAO - VIVEIRO PRO", 0, 1, "C")
    pdf.ln(5)
    
    # Resumo Financeiro
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(190, 10, " RESUMO FINANCEIRO", 1, 1, "L", fill=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(63, 10, f"Investimento: {format_currency(resumo['total_custo'])}", 1, 0)
    pdf.cell(63, 10, f"Vendas: {format_currency(resumo['total_venda'])}", 1, 0)
    pdf.cell(64, 10, f"Lucro: {format_currency(resumo['lucro'])}", 1, 1)
    pdf.ln(10)
    
    # Estoque
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, " INVENTARIO ATUAL", 1, 1, "L", fill=True)
    pdf.set_font("Arial", "B", 9)
    cols = [("Planta", 60), ("Qtd", 20), ("Data Plantio", 35), ("Custo Total", 75)]
    for name, width in cols: pdf.cell(width, 10, name, 1, 0, "C")
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    for _, row in df_est.iterrows():
        pdf.cell(60, 10, str(row['planta']), 1, 0)
        pdf.cell(20, 10, str(row['quantidade']), 1, 0, "C")
        pdf.cell(35, 10, format_date_br(row.get('data_plantio', '')), 1, 0, "C")
        
        # Cálculo de custo total (soma todos os campos de custo)
        custos_detalhe = row.get('custos_detalhados', {})
        if isinstance(custos_detalhe, str): custos_detalhe = json.loads(custos_detalhe)
        custo_total_unit = sum(custos_detalhe.values()) if custos_detalhe else 0
        pdf.cell(75, 10, format_currency(custo_total_unit * row['quantidade']), 1, 1, "R")
        
    return pdf.output(dest="S").encode("latin-1")

# =========================
# GESTÃO DE ESTADO (SESSION)
# =========================
if "user" not in st.session_state: st.session_state.user = None
if "tipos_custo" not in st.session_state: st.session_state.tipos_custo = ["Muda", "Adubagem", "Mão de Obra", "Irrigação"]

# =========================
# LOGIN
# =========================
if st.session_state.user is None:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center; color: #2e7d32;'>🌱 Viveiro Pro V2</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                # MOCK PARA TESTE (O usuário deve usar as credenciais do Supabase)
                if email and senha:
                    st.session_state.user = "demo_user"
                    st.rerun()

# =========================
# SISTEMA PRINCIPAL
# =========================
else:
    user_id = st.session_state.user
    
    with st.sidebar:
        st.markdown("<h2 style='color: white;'>🌱 Navegação</h2>", unsafe_allow_html=True)
        menu = st.radio("", ["📊 Dashboard", "📦 Produção & Estoque", "💰 Vendas & Clientes"])
        st.divider()
        if st.button("Sair"):
            st.session_state.user = None
            st.rerun()

    # --- DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("Painel de Controle")
        
        try:
            # Buscar dados
            res_est = supabase.table("estoque").select("*").eq("user_id", user_id).execute()
            res_ven = supabase.table("vendas").select("*").eq("user_id", user_id).execute()
            
            df_est = pd.DataFrame(res_est.data) if res_est.data else pd.DataFrame()
            df_ven = pd.DataFrame(res_ven.data) if res_ven.data else pd.DataFrame()
            
            # Cálculos Financeiros
            total_investido = 0
            if not df_est.empty:
                for _, row in df_est.iterrows():
                    custos = row.get('custos_detalhados', {})
                    if isinstance(custos, str): custos = json.loads(custos)
                    unit_cost = sum(custos.values()) if custos else 0
                    total_investido += (unit_cost * row['quantidade'])
            
            total_vendas = (df_ven['quantidade'] * df_ven['preco']).sum() if not df_ven.empty else 0
            lucro = total_vendas - total_investido
            
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("Investimento Total", format_currency(total_investido))
            with m2: st.metric("Receita Bruta", format_currency(total_vendas))
            with m3: st.metric("Lucro Líquido", format_currency(lucro), delta=f"{lucro:.2f}")
            
            st.divider()
            
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("Estoque por Espécie")
                if not df_est.empty:
                    st.bar_chart(df_est.set_index('planta')['quantidade'])
                else: st.info("Nenhum dado para exibir.")
            
            with c2:
                st.subheader("Relatório PDF")
                if not df_est.empty:
                    resumo_data = {"total_custo": total_investido, "total_venda": total_vendas, "lucro": lucro}
                    pdf_bytes = generate_pdf(df_est, df_ven, resumo_data)
                    st.download_button(
                        label="📥 Baixar Resumo Completo",
                        data=pdf_bytes,
                        file_name=f"relatorio_viveiro_{datetime.now().strftime('%d_%m_%Y')}.pdf",
                        mime="application/pdf"
                    )
                else: st.warning("Adicione dados para gerar o PDF.")
                
        except Exception as e:
            st.error(f"Erro ao carregar dashboard. Verifique as tabelas no Supabase.")

    # --- PRODUÇÃO ---
    elif menu == "📦 Produção & Estoque":
        st.title("Gestão de Lotes")
        
        with st.expander("➕ Cadastrar Novo Lote de Produção", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                planta = st.text_input("Nome da Planta/Espécie")
                qtd = st.number_input("Quantidade de Mudas", min_value=1, step=1)
                data_p = st.date_input("Data de Plantio", datetime.now(), format="DD/MM/YYYY")
            
            with col2:
                st.write("**Detalhamento de Custos (Unitário)**")
                
                # Sistema de Custos Dinâmicos
                custos_input = {}
                for tipo in st.session_state.tipos_custo:
                    custos_input[tipo] = st.number_input(f"Custo: {tipo} (R$)", min_value=0.0, format="%.2f", key=f"cost_{tipo}")
                
                # Adicionar novo tipo de custo
                new_cost_type = st.text_input("➕ Adicionar outro tipo de custo (ex: Frete, Embalagem)")
                if st.button("Incluir este tipo"):
                    if new_cost_type and new_cost_type not in st.session_state.tipos_custo:
                        st.session_state.tipos_custo.append(new_cost_type)
                        st.rerun()

            if st.button("Salvar Produção"):
                try:
                    supabase.table("estoque").insert({
                        "user_id": user_id,
                        "planta": planta,
                        "quantidade": qtd,
                        "data_plantio": data_p.isoformat(),
                        "custos_detalhados": json.dumps(custos_input)
                    }).execute()
                    st.success("Lote registrado com sucesso!")
                    st.rerun()
                except: st.error("Erro ao salvar. Certifique-se que a coluna 'custos_detalhados' (JSONB) existe no Supabase.")

        st.subheader("Inventário Atual")
        try:
            dados = supabase.table("estoque").select("*").eq("user_id", user_id).execute()
            if dados.data:
                df = pd.DataFrame(dados.data)
                df['Data'] = df['data_plantio'].apply(lambda x: format_date_br(x))
                st.dataframe(df[['planta', 'quantidade', 'Data']], use_container_width=True)
            else: st.info("Estoque vazio.")
        except: pass

    # --- VENDAS ---
    elif menu == "💰 Vendas & Clientes":
        st.title("Registro de Vendas")
        
        with st.container(border=True):
            st.subheader("Dados da Venda")
            c1, c2, c3 = st.columns(3)
            with c1: v_planta = st.text_input("Planta Vendida")
            with c2: v_qtd = st.number_input("Qtd", min_value=1)
            with c3: v_preco = st.number_input("Preço Unitário (R$)", min_value=0.0, format="%.2f")
            
            st.divider()
            st.subheader("Dados do Comprador")
            cc1, cc2, cc3 = st.columns(3)
            with cc1: c_nome = st.text_input("Nome do Cliente")
            with cc2: c_doc = st.text_input("CPF / CNPJ")
            with cc3: c_contato = st.text_input("Telefone / E-mail")
            
            if st.button("Finalizar Venda"):
                try:
                    supabase.table("vendas").insert({
                        "user_id": user_id,
                        "planta": v_planta,
                        "quantidade": v_qtd,
                        "preco": v_preco,
                        "cliente_nome": c_nome,
                        "cliente_documento": c_doc,
                        "cliente_contato": c_contato,
                        "data_venda": datetime.now().isoformat()
                    }).execute()
                    st.success(f"Venda para {c_nome} registrada!")
                    st.rerun()
                except: st.error("Erro ao salvar venda. Verifique as colunas de cliente no banco de dados.")

        st.subheader("Histórico de Vendas Recentes")
        try:
            vendas = supabase.table("vendas").select("*").eq("user_id", user_id).execute()
            if vendas.data:
                df_v = pd.DataFrame(vendas.data)
                df_v['Data'] = df_v['data_venda'].apply(lambda x: format_date_br(x))
                df_v['Total'] = (df_v['quantidade'] * df_v['preco']).apply(format_currency)
                st.dataframe(df_v[['Data', 'planta', 'quantidade', 'Total', 'cliente_nome', 'cliente_documento']], use_container_width=True)
            else: st.info("Sem vendas registradas.")
        except: pass

st.markdown("<div class='footer'>Viveiro Pro V2 © 2026 - Gestão de Mudas Profissional</div>", unsafe_allow_html=True)
