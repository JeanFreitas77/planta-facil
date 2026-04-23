import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import base64

# =========================
# CONFIGURAÇÕES E ESTILO
# =========================
st.set_page_config(
    page_title="Viveiro Pro - Gestão Inteligente",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Customizado para um visual moderno
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #2e7d32;
        color: white;
    }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stSidebarNav"] {
        background-image: linear-gradient(#1b5e20, #2e7d32);
        color: white;
    }
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: white;
        color: #6c757d;
        text-align: center;
        padding: 10px;
        font-size: 12px;
        border-top: 1px solid #dee2e6;
    }
    </style>
    """, unsafe_allow_html=True)

# =========================
# CONEXÃO SUPABASE
# =========================
# Nota: O usuário deve manter suas credenciais reais aqui
URL = "https://qkjukxdnufuvrzezrxue.supabase.co"
KEY = "sb_publishable_OYkUUp3VGWDWL3ztH8zqig_sZrkIY8R"

@st.cache_resource
def get_supabase():
    try:
        return create_client(URL, KEY)
    except:
        return None

supabase = get_supabase()

# =========================
# FUNÇÕES AUXILIARES
# =========================
def format_currency(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_date(date_str):
    if not date_str: return "-"
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%d/%m/%Y")
    except:
        return date_str

def generate_pdf(estoque_df, vendas_df, resumo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "Relatório de Gestão - Viveiro Pro", 0, 1, "C")
    pdf.ln(10)
    
    # Resumo Financeiro
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "Resumo Financeiro", 1, 1, "L")
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 10, f"Total Investido: {format_currency(resumo['total_custo'])}", 1, 0)
    pdf.cell(95, 10, f"Total em Vendas: {format_currency(resumo['total_venda'])}", 1, 1)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(190, 10, f"Lucro Estimado: {format_currency(resumo['lucro'])}", 1, 1)
    pdf.ln(10)
    
    # Tabela de Estoque
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "Inventário Atual", 1, 1, "L")
    pdf.set_font("Arial", "B", 10)
    pdf.cell(60, 10, "Planta", 1, 0)
    pdf.cell(30, 10, "Qtd", 1, 0)
    pdf.cell(40, 10, "Data Plantio", 1, 0)
    pdf.cell(60, 10, "Custo Total", 1, 1)
    
    pdf.set_font("Arial", "", 10)
    for _, row in estoque_df.iterrows():
        pdf.cell(60, 10, str(row['planta']), 1, 0)
        pdf.cell(30, 10, str(row['quantidade']), 1, 0)
        pdf.cell(40, 10, format_date(row.get('data_plantio', '')), 1, 0)
        total_item = row['quantidade'] * (row.get('custo_muda', 0) + row.get('custo_adubo', 0) + row.get('custo_mao_obra', 0))
        pdf.cell(60, 10, format_currency(total_item), 1, 1)
        
    return pdf.output(dest="S").encode("latin-1")

# =========================
# AUTENTICAÇÃO
# =========================
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🌱 Viveiro Pro</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Gestão profissional para o seu negócio</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            if st.button("Acessar Painel"):
                if supabase:
                    try:
                        resposta = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                        if resposta and resposta.user:
                            st.session_state.user = resposta.user.id
                            st.rerun()
                        else:
                            st.error("Credenciais inválidas.")
                    except Exception as e:
                        st.error(f"Erro ao conectar: {e}")
                else:
                    st.warning("Configuração do Supabase pendente.")
                    # Mock para demonstração se necessário
                    if email == "admin" and senha == "admin":
                        st.session_state.user = "demo_user"
                        st.rerun()

# =========================
# DASHBOARD PRINCIPAL
# =========================
else:
    user_id = st.session_state.user
    
    # Sidebar
    with st.sidebar:
        st.title("🌱 Menu")
        menu = st.radio("Navegação", ["Dashboard", "Estoque & Produção", "Vendas", "Configurações"])
        st.divider()
        if st.button("Sair do Sistema"):
            st.session_state.user = None
            st.rerun()

    # --- DASHBOARD ---
    if menu == "Dashboard":
        st.title("📊 Painel de Controle")
        
        # Buscar Dados
        try:
            estoque_res = supabase.table("estoque").select("*").eq("user_id", user_id).execute()
            vendas_res = supabase.table("vendas").select("*").eq("user_id", user_id).execute()
            
            df_est = pd.DataFrame(estoque_res.data) if estoque_res.data else pd.DataFrame()
            df_ven = pd.DataFrame(vendas_res.data) if vendas_res.data else pd.DataFrame()
            
            # Cálculos
            if not df_est.empty:
                # Soma custos detalhados
                df_est['custo_total_unit'] = df_est.get('custo_muda', 0) + df_est.get('custo_adubo', 0) + df_est.get('custo_mao_obra', 0)
                total_investido = (df_est['quantidade'] * df_est['custo_total_unit']).sum()
            else:
                total_investido = 0
                
            total_vendas = (df_ven['quantidade'] * df_ven['preco']).sum() if not df_ven.empty else 0
            lucro = total_vendas - total_investido
            
            # Métricas em Cards
            m1, m2, m3 = st.columns(3)
            m1.metric("💸 Investimento Total", format_currency(total_investido))
            m2.metric("💰 Receita de Vendas", format_currency(total_vendas))
            m3.metric("📈 Lucro Estimado", format_currency(lucro), delta=f"{lucro:.2f}")
            
            st.divider()
            
            # Gráficos e Relatórios
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📦 Status do Estoque")
                if not df_est.empty:
                    st.bar_chart(df_est.set_index('planta')['quantidade'])
                else:
                    st.info("Sem dados de estoque.")
            
            with c2:
                st.subheader("📄 Relatórios")
                resumo_data = {"total_custo": total_investido, "total_venda": total_vendas, "lucro": lucro}
                if st.button("Gerar PDF do Resumo"):
                    pdf_bytes = generate_pdf(df_est, df_ven, resumo_data)
                    st.download_button(
                        label="⬇️ Baixar Relatório PDF",
                        data=pdf_bytes,
                        file_name=f"relatorio_viveiro_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf"
                    )
        except Exception as e:
            st.error(f"Erro ao carregar dashboard: {e}")

    # --- ESTOQUE & PRODUÇÃO ---
    elif menu == "Estoque & Produção":
        st.title("📦 Gestão de Produção")
        
        with st.expander("➕ Cadastrar Nova Produção/Lote", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                planta = st.text_input("Espécie/Planta")
                qtd = st.number_input("Quantidade de Mudas", min_value=1)
                data_plantio = st.date_input("Data de Plantio", datetime.now())
            
            with col2:
                st.write("**Detalhamento de Custos (Unitário)**")
                c_muda = st.number_input("Custo da Muda (R$)", min_value=0.0, format="%.2f")
                c_adubo = st.number_input("Custo Adubagem/Insumos (R$)", min_value=0.0, format="%.2f")
                c_mao = st.number_input("Custo Mão de Obra (R$)", min_value=0.0, format="%.2f")
            
            if st.button("Salvar no Sistema"):
                try:
                    supabase.table("estoque").insert({
                        "user_id": user_id,
                        "planta": planta,
                        "quantidade": qtd,
                        "data_plantio": data_plantio.isoformat(),
                        "custo_muda": c_muda,
                        "custo_adubo": c_adubo,
                        "custo_mao_obra": c_mao
                    }).execute()
                    st.success("Lote cadastrado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

        st.subheader("📋 Inventário Detalhado")
        try:
            dados = supabase.table("estoque").select("*").eq("user_id", user_id).execute()
            if dados.data:
                df = pd.DataFrame(dados.data)
                # Formatação para exibição
                df_view = df.copy()
                df_view['Data'] = df_view['data_plantio'].apply(format_date)
                df_view['Custo Total'] = (df_view['custo_muda'] + df_view['custo_adubo'] + df_view['custo_mao_obra']) * df_view['quantidade']
                df_view['Custo Total'] = df_view['Custo Total'].apply(format_currency)
                
                st.dataframe(df_view[['planta', 'quantidade', 'Data', 'Custo Total']], use_container_width=True)
            else:
                st.info("Nenhum item no estoque.")
        except:
            st.error("Erro ao carregar inventário.")

    # --- VENDAS ---
    elif menu == "Vendas":
        st.title("💰 Registro de Vendas")
        
        # Formulário de Venda
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                v_planta = st.text_input("Planta Vendida")
            with c2:
                v_qtd = st.number_input("Qtd Vendida", min_value=1)
            with c3:
                v_preco = st.number_input("Preço Unitário (R$)", min_value=0.0, format="%.2f")
            
            if st.button("Confirmar Venda"):
                try:
                    supabase.table("vendas").insert({
                        "user_id": user_id,
                        "planta": v_planta,
                        "quantidade": v_qtd,
                        "preco": v_preco,
                        "data_venda": datetime.now().isoformat()
                    }).execute()
                    st.success("Venda registrada!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao registrar: {e}")

        st.subheader("📜 Histórico de Vendas")
        try:
            vendas = supabase.table("vendas").select("*").eq("user_id", user_id).execute()
            if vendas.data:
                df_v = pd.DataFrame(vendas.data)
                df_v['Total'] = (df_v['quantidade'] * df_v['preco']).apply(format_currency)
                st.table(df_v[['planta', 'quantidade', 'preco', 'Total']])
            else:
                st.info("Nenhuma venda registrada ainda.")
        except:
            st.error("Erro ao carregar histórico.")

# Footer
st.markdown("<div class='footer'>Viveiro Pro © 2026 - Gestão Agrícola Inteligente</div>", unsafe_allow_html=True)
