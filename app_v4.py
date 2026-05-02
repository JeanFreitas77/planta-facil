import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import base64
import json
import os
from dotenv import  load_dotenv

load_dotenv()

# =========================
# CONFIGURAÇÕES E ESTILO
# =========================
st.set_page_config(
    page_title="Gerenciador PlantaFácil",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Customizado para um visual moderno e limpo
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.2em; background-color: #2e7d32; color: white; font-weight: bold; border: none; transition: 0.3s; }
    .stButton>button:hover { background-color: #1b5e20; transform: translateY(-2px); }
    .stMetric { background-color: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border: 1px solid #e0e0e0; }
    [data-testid="stSidebar"] { background-color: #1b5e20; }
    [data-testid="stSidebar"] * { color: white !important; }
    /* Ajuste para garantir que o texto das opções do Radio Button e Selectbox apareça */
    [data-testid="stSidebar"] .stRadio label, [data-testid="stSidebar"] .stSelectbox label { color: white !important; }
    [data-testid="stSidebar"] div[role="radiogroup"] { color: white !important; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: white; color: #6c757d; text-align: center; padding: 12px; font-size: 13px; border-top: 1px solid #dee2e6; z-index: 100; }
    .stDataFrame {
    background-color: white;
    border-radius: 12px;
    padding: 10px;
    border: 1px solid #dcdcdc;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    /* Cabeçalho da tabela */
    .stDataFrame thead tr th {
    background-color: #2e7d32 !important;
    color: white !important;
    font-weight: bold;
    text-align: left;
    }
    /* Linhas */
    .stDataFrame tbody tr {
    border-bottom: 1px solid #eee;
    }

    /* Hover (passar o mouse) */
    .stDataFrame tbody tr:hover {
    background-color: #f5f5f5;
    }

    /* Texto mais legível */
    .stDataFrame td {
    font-size: 14px;
    color: #333;
    }
            
    </style>
    """, unsafe_allow_html=True)

# =========================
# CONEXÃO SUPABASE
# =========================
# IMPORTANTE: Substitua pelas suas credenciais reais
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def get_supabase():
    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro na conexão com Supabase: {e}")
        return None

supabase = get_supabase()

# =========================
# FUNÇÕES AUXILIARES
# =========================
def format_currency(value):
    try:
        val = float(value)
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def format_date_br(date_str):
    if not date_str: return "-"
    try:
        # Tenta vários formatos comuns de data do Supabase
        for fmt in ["%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"]:
            try:
                dt = datetime.strptime(date_str.split('+')[0].split('.')[0], "%Y-%m-%dT%H:%M:%S")
                return dt.strftime("%d/%m/%Y")
            except: continue
        return date_str
    except:
        return date_str

def generate_pdf(df_est, df_ven, resumo):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # =========================
    # HEADER MODERNO
    # =========================
    pdf.set_fill_color(27, 94, 32)  # verde escuro
    pdf.rect(0, 0, 210, 25, 'F')

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "RELATORIO GERENCIAL", ln=True, align="C")

    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")

    pdf.ln(10)

    # =========================
    # RESUMO FINANCEIRO
    # =========================
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "RESUMO FINANCEIRO", ln=True)

    pdf.set_fill_color(240, 240, 240)

    pdf.set_font("Arial", "", 11)
    pdf.cell(63, 10, f"Investimento: {format_currency(resumo['total_custo'])}", border=1, fill=True)
    pdf.cell(63, 10, f"Vendas: {format_currency(resumo['total_venda'])}", border=1, fill=True)
    pdf.cell(64, 10, f"Lucro: {format_currency(resumo['lucro'])}", border=1, ln=True, fill=True)

    pdf.ln(8)

    # =========================
    # ESTOQUE
    # =========================
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "ESTOQUE ATUAL", ln=True)

    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 230, 201)

    pdf.cell(70, 8, "Planta", border=1, fill=True)
    pdf.cell(30, 8, "Qtd", border=1, fill=True)
    pdf.cell(50, 8, "Data Plantio", border=1, fill=True)
    pdf.cell(40, 8, "Custo Total", border=1, ln=True, fill=True)

    pdf.set_font("Arial", "", 9)

    for _, row in df_est.iterrows():
        custos = row.get('custos_detalhados', {})
        if isinstance(custos, str):
            try:
                custos = json.loads(custos)
            except:
                custos = {}

        unit_cost = sum(float(v) for v in custos.values()) if custos else float(row.get('custo', 0))
        total = unit_cost * int(row.get('quantidade', 0))

        pdf.cell(70, 8, str(row.get('planta', '-')), border=1)
        pdf.cell(30, 8, str(row.get('quantidade', 0)), border=1)
        pdf.cell(50, 8, format_date_br(row.get('data_plantio', '')), border=1)
        pdf.cell(40, 8, format_currency(total), border=1, ln=True)

    pdf.ln(8)

    # =========================
    # VENDAS
    # =========================
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "ULTIMAS VENDAS", ln=True)

    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(255, 224, 178)

    pdf.cell(70, 8, "Data", border=1, fill=True)
    pdf.cell(30, 8, "Planta", border=1, fill=True)
    pdf.cell(50, 8, "Qtd", border=1, fill=True)
    pdf.cell(40, 8, "Total", border=1, ln=True, fill=True)
        
    pdf.set_font("Arial", "", 9)

    for _, row in df_ven.tail(10).iterrows():
        total = float(row.get('quantidade', 0)) * float(row.get('preco', 0))

        pdf.cell(70, 8, format_date_br(row.get('data_venda', '')), border=1)
        pdf.cell(30, 8, str(row.get('planta', '-')), border=1)
        pdf.cell(50, 8, str(row.get('quantidade', 0)), border=1)
        pdf.cell(40, 8, format_currency(total), border=1, ln=True)
                
    return pdf.output(dest="S").encode("latin-1")

def verificar_usuario_ativo(supabase, user_id, email):
    try:
        res = supabase.table("usuarios") \
            .select("ativo") \
            .eq("id", user_id) \
            .execute()

        # se não existir, cria automaticamente
        if not res.data:
            supabase.table("usuarios").insert({
                "id": user_id,
                "email": email,
                "ativo": True
            }).execute()
            return True

        # se existir, verifica se está ativo
        return res.data[0]["ativo"]

    except Exception as e:
        st.error(f"Erro ao validar usuário: {e}")
        return False


# =========================
# GESTÃO DE SESSÃO
# =========================
if "user" not in st.session_state: st.session_state.user = None
if "tipos_custo" not in st.session_state: st.session_state.tipos_custo = ["Muda", "Adubagem", "Mão de Obra", "Irrigação"]

# =========================
# TELA DE LOGIN (CORRIGIDA PARA TAB)
# =========================
if st.session_state.user is None:
    _, col_login, _ = st.columns([1, 1.2, 1])
    with col_login:
        st.markdown("<h1 style='text-align: center; color: #2e7d32; white-space:nowrap'>🌱 PlantaFácil</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Gerenciador PlantaFácil</p>", unsafe_allow_html=True)
        
                with st.container(border=True):
            # 1. Primeiro definimos as variáveis (isso evita o erro 'not defined')
            email = st.text_input("E-mail", placeholder="seu@email.com")
            senha = st.text_input("Senha", type="password", placeholder="******")
            
            st.write("") # Espaço visual
            
            # 2. Depois criamos as colunas com os botões
            col_login, col_cadastro = st.columns(2)
            
            with col_login:
                if st.button("Acessar Painel"):
                    if supabase:
                        try:
                            resposta = supabase.auth.sign_in_with_password({
                                "email": email,
                                "password": senha
                            })
                            if resposta and resposta.user:
                                user_id = resposta.user.id
                                if verificar_usuario_ativo(supabase, user_id, email):
                                    st.session_state.user = user_id
                                    st.success("Bem-vindo!")
                                    st.rerun()
                                else:
                                    st.error("Seu acesso está inativo.")
                            else:
                                st.error("E-mail ou senha incorretos.")
                        except Exception as e:
                            st.error(f"Erro ao conectar: {e}")
                    else:
                        st.warning("Configuração do Supabase não encontrada.")

            with col_cadastro:
                if st.button("Criar Nova Conta"):
                    if not email or not senha:
                        st.warning("Preencha e-mail e senha.")
                    elif len(senha) < 6:
                        st.error("A senha deve ter 6+ caracteres.")
                    else:
                        try:
                            resp = supabase.auth.sign_up({"email": email, "password": senha})
                            if resp and resp.user:
                                try:
                                    supabase.table("usuarios").insert({
                                        "id": resp.user.id,
                                        "email": email,
                                        "ativo": True
                                    }).execute()
                                except:
                                    pass
                                st.success("Conta criada! Agora clique em 'Acessar Painel'.")
                            else:
                                st.error("Erro ao criar conta.")
                        except Exception as e:
                            st.error(f"Erro no cadastro: {e}")



                    
# =========================
# ÁREA LOGADA
# =========================
else:
    user_id = st.session_state.user
    
    with st.sidebar:
        st.markdown("<h2 style='color: white; text-align: center;'>🌱 Menu</h2>", unsafe_allow_html=True)
        menu = st.radio("", ["📊 Dashboard", "📦 Produção & Estoque", "💰 Vendas & Clientes"])
        st.divider()
        if st.button("Encerrar Sessão"):
            st.session_state.user = None
            st.rerun()

    # --- DASHBOARD (COM TRATAMENTO DE ERROS ROBUSTO) ---
    if menu == "📊 Dashboard":
        st.title("Painel de Controle")
        
        try:
            # Buscar dados com segurança
            res_est = supabase.table("estoque").select("*").eq("user_id", user_id).execute()
            res_ven = supabase.table("vendas").select("*").eq("user_id", user_id).execute()
            
            df_est = pd.DataFrame(res_est.data) if res_est.data else pd.DataFrame()
            df_ven = pd.DataFrame(res_ven.data) if res_ven.data else pd.DataFrame()
            
            # Cálculos Financeiros
            total_investido = 0
            if not df_est.empty:
                for _, row in df_est.iterrows():
                    custos = row.get('custos_detalhados', {})
                    if isinstance(custos, str): 
                        try: custos = json.loads(custos)
                        except: custos = {}
                    
                    # Soma custos detalhados ou usa o custo unitário antigo se o detalhado estiver vazio
                    unit_cost = sum(float(v) for v in custos.values()) if custos else float(row.get('custo', 0))
                    total_investido += (unit_cost * int(row.get('quantidade', 0)))
            
            total_vendas = 0
            if not df_ven.empty:
                total_vendas = (df_ven['quantidade'].astype(float) * df_ven['preco'].astype(float)).sum()
            
            lucro = total_vendas - total_investido
            
            # Exibição de Métricas
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("Investimento em Mudas", format_currency(total_investido))
            with m2: st.metric("Faturamento Total", format_currency(total_vendas))
            with m3: st.metric("Lucro", format_currency(lucro), delta=f"{lucro:.2f}")
            
            st.divider()
            
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("📦 Estoque por Espécie")
                if not df_est.empty:
                    st.bar_chart(df_est.set_index('planta')['quantidade'])
                else: st.info("Nenhum dado de produção cadastrado.")
            
            with c2:
                st.subheader("📄 Relatórios")
                if not df_est.empty:
                    resumo_data = {"total_custo": total_investido, "total_venda": total_vendas, "lucro": lucro}
                    pdf_bytes = generate_pdf(df_est, df_ven, resumo_data)
                    st.download_button(
                        label="📥 Baixar PDF do Resumo",
                        data=pdf_bytes,
                        file_name=f"relatorio_geral_{datetime.now().strftime('%d_%m_%Y')}.pdf",
                        mime="application/pdf"
                    )
                else: st.warning("Cadastre lotes para gerar relatórios.")
                
        except Exception as e:
            st.error(f"Atenção: Algumas tabelas podem não estar configuradas corretamente no Supabase.")
            st.info("Dica: Verifique se você adicionou as colunas 'custos_detalhados' (jsonb) e 'cliente_nome' (text).")

    # --- PRODUÇÃO & ESTOQUE ---
    elif menu == "📦 Produção & Estoque":
        st.title("Gestão de Produção")
        
        with st.expander("➕ Cadastrar Novo Lote", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                planta = st.text_input("Espécie / Nome da Planta")
                qtd = st.number_input("Quantidade de Mudas", min_value=1, step=1)
                data_p = st.date_input("Data de Plantio", datetime.now(), format="DD/MM/YYYY")
            
            with col2:
                st.write("**Detalhamento de Custos Unitários**")
                custos_input = {}
                for tipo in st.session_state.tipos_custo:
                    custos_input[tipo] = st.number_input(f"Custo: {tipo} (R$)", min_value=0.0, format="%.2f", key=f"c_{tipo}")
                
                new_cost_type = st.text_input("➕ Adicionar novo tipo de custo")
                if st.button("Incluir Custo"):
                    if new_cost_type and new_cost_type not in st.session_state.tipos_custo:
                        st.session_state.tipos_custo.append(new_cost_type)
                        st.rerun()

            if st.button("Salvar Lote no Sistema"):
                try:
                    supabase.table("estoque").insert({
                        "user_id": user_id,
                        "planta": planta,
                        "quantidade": qtd,
                        "data_plantio": data_p.isoformat(),
                        "custos_detalhados": json.dumps(custos_input)
                    }).execute()
                    st.success("Lote cadastrado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

        st.subheader("✏️ Editar Lote")

        dados = supabase.table("estoque").select("*").eq("user_id", user_id).execute()

        if dados.data:
            opcoes = {f"{d['planta']} - {d['quantidade']}": d for d in dados.data}

            escolha = st.selectbox("Selecionar lote", list(opcoes.keys()))

            item = opcoes[escolha]

            nova_qtd = st.number_input("Nova quantidade", value=int(item["quantidade"]))

            if st.button("Atualizar lote"):
                supabase.table("estoque").update({
                    "quantidade": nova_qtd
                }).eq("id", item["id"]).execute()

                st.success("Atualizado!")
                st.rerun()
        
        st.subheader("🗑️ Deletar Lote")

        if dados.data:
            escolha_del = st.selectbox("Selecionar para deletar", list(opcoes.keys()), key="del")

            item_del = opcoes[escolha_del]

            if st.button("Deletar"):
                supabase.table("estoque").delete().eq("id", item_del["id"]).execute()

                st.success("Deletado!")
                st.rerun()

        st.subheader("📜 Histórico de Produção")

        try:
            dados_hist = supabase.table("estoque").select("*").eq("user_id", user_id).execute()

            if dados_hist.data:
                df_hist = pd.DataFrame(dados_hist.data)

                df_hist["Data Plantio"] = df_hist["data_plantio"].apply(format_date_br)

                # calcular custo total
                def calcular_total(row):
                    custos = row.get('custos_detalhados', {})
                    if isinstance(custos, str):
                        try:
                            custos = json.loads(custos)
                        except:
                            custos = {}

                    unit = sum(float(v) for v in custos.values()) if custos else float(row.get('custo', 0))
                    return unit * int(row.get('quantidade', 0))

                df_hist["Custo Total"] = df_hist.apply(calcular_total, axis=1).apply(format_currency)

                st.dataframe(
                    df_hist[["planta", "quantidade", "Data Plantio", "Custo Total"]],
                    use_container_width=True
                )
            else:
                st.info("Nenhum lote cadastrado ainda.")

        except Exception as e:
            st.error(f"Erro ao carregar histórico: {e}")

    # --- VENDAS & CLIENTES ---
    elif menu == "💰 Vendas & Clientes":
        st.title("Registro de Vendas")

        # =========================
        # BUSCAR PLANTAS DO ESTOQUE
        # =========================
        try:
            dados = supabase.table("estoque").select("planta").eq("user_id", user_id).execute()
            lista_plantas = list(set([item["planta"] for item in dados.data])) if dados.data else []
        except Exception:
            lista_plantas = []

        with st.container(border=True):
            st.subheader("Informações da Venda")

            c1, c2, c3 = st.columns(3)

            with c1:
                if lista_plantas:
                    v_planta = st.selectbox("Planta Vendida", lista_plantas)
                else:
                    v_planta = st.text_input("Planta Vendida")

        # =========================
        # BUSCAR ESTOQUE
        # =========================
        estoque_atual = 0
        estoque_resp = None

        if lista_plantas and v_planta:
            estoque_resp = supabase.table("estoque") \
                .select("id, quantidade") \
                .eq("user_id", user_id) \
                .eq("planta", v_planta) \
                .execute()

            if estoque_resp.data:
                estoque_atual = sum([item["quantidade"] for item in estoque_resp.data])

        with c2:
            st.markdown(f"**Estoque disponível:** {estoque_atual}")
            v_qtd = st.number_input("Qtd Vendida", min_value=1)

        with c3:
            v_preco = st.number_input("Preço de Venda (R$)", min_value=0.0, format="%.2f")

        st.divider()

        st.subheader("Dados do Comprador")

        cc1, cc3 = st.columns(2)

        with cc1:
            c_nome = st.text_input("Cliente")

        with cc3:
            c_contato = st.text_input("Contato (Tel/Email)")

        if st.button("Finalizar e Registrar Venda"):
            try:
                # =========================
                # VALIDAÇÃO DE ESTOQUE
                # =========================
                if v_qtd > estoque_atual:
                    st.error(f"Estoque insuficiente! Disponível: {estoque_atual}")
                    st.stop()

                # =========================
                # REGISTRAR VENDA
                # =========================
                supabase.table("vendas").insert({
                    "user_id": user_id,
                    "planta": v_planta,
                    "quantidade": v_qtd,
                    "preco": v_preco,
                    "cliente_nome": c_nome,
                    "cliente_contato": c_contato,
                    "data_venda": datetime.now().isoformat()
                }).execute()

                # =========================
                # DAR BAIXA NO ESTOQUE
                # =========================
                if estoque_resp and estoque_resp.data:
                    for item in estoque_resp.data:
                        nova_qtd = item["quantidade"] - v_qtd

                        supabase.table("estoque").update({
                            "quantidade": nova_qtd
                        }).eq("id", item["id"]).execute()

                        break  # apenas um lote (simples)

                st.success(f"Venda registrada com sucesso para {c_nome}!")
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao registrar venda: {e}")
        st.subheader("✏️ / 🗑️ Gerenciar Vendas")

        vendas = supabase.table("vendas").select("*").eq("user_id", user_id).execute()

        if vendas.data:
            df_v = pd.DataFrame(vendas.data)

            df_v["label"] = df_v["planta"]
            
            escolha_v = st.selectbox("Selecionar venda", df_v["label"].tolist())

            venda = df_v[df_v["planta"] == escolha_v].iloc[0].to_dict()

            nova_qtd = st.number_input("Nova quantidade", value=int(venda["quantidade"]))

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Atualizar venda"):
                    supabase.table("vendas").update({
                        "quantidade": nova_qtd
                    }).eq("id", venda["id"]).execute()

                    st.success("Atualizado!")
                    st.rerun()

            with col2:
                if st.button("Deletar venda"):
                    supabase.table("vendas").delete().eq("id", venda["id"]).execute()

                    st.success("Deletado!")
                    st.rerun()

    # =========================
    # HISTÓRICO
    # =========================
    st.subheader("📜 Histórico de Vendas")

    try:
        vendas = supabase.table("vendas").select("*").eq("user_id", user_id).execute()

        if vendas.data:
            df_v = pd.DataFrame(vendas.data)
            df_v["Data"] = df_v["data_venda"].apply(format_date_br)
            df_v["Total"] = (df_v["quantidade"].astype(float) * df_v["preco"].astype(float)).apply(format_currency)

            df_v = df_v.rename(columns={
                "cliente_nome": "Cliente",
                "cliente_contato": "Contato"
            })

            st.dataframe(
                df_v[["Data", "planta", "quantidade", "Total", "Cliente", "Contato"]],
                use_container_width=True
            )
        else:
            st.info("Nenhuma venda registrada ainda.")

    except Exception as e:
        st.error(f"Erro ao carregar vendas: {e}")

# Rodapé
st.markdown("<div class='footer'>Gerenciador PlantaFácil © 2026 </div>", unsafe_allow_html=True)
