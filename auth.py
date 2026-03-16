"""
Módulo de Autenticação e Controle de Acesso
"""
import streamlit as st

# Usuários e senhas
USUARIOS = {
    "Gestor": {
        "senha": "Afirmaevias",
        "paginas": ["Dashboard de Certificados", "Cronograma de Ensaios", "Mapeamento de Projetos CAUQ"]
    },
    "Geoloc": {
        "senha": "Afirmaevias",
        "paginas": ["Mapeamento de Projetos CAUQ"]
    },
    "EPR": {
        "senha": "Afirmaevias",
        "paginas": ["EPR Litoral Pioneiro"]
    },
    "Dev": {
        "senha": "Afirmaevias",
        "paginas": ["Dashboard de Certificados", "Cronograma de Ensaios", "EPR Litoral Pioneiro", "Mapeamento de Projetos CAUQ"]
    }
}

# Mapeamento de páginas para arquivos
PAGINA_ARQUIVO = {
    "Dashboard de Certificados": "pages/01_Dashboard_Certificados.py",
    "Cronograma de Ensaios": "pages/02_Cronograma_Relatorios.py", 
    "EPR Litoral Pioneiro": "pages/03_EPR_Litoral_Pioneiro.py",
    "Mapeamento de Projetos CAUQ": "pages/04_Mapeamento_CAUQ.py"
}

def verificar_login(usuario, senha):
    """Verifica se o usuário e senha estão corretos"""
    if usuario in USUARIOS and USUARIOS[usuario]["senha"] == senha:
        return True
    return False

def get_paginas_permitidas(usuario):
    """Retorna a lista de páginas permitidas para o usuário"""
    if usuario in USUARIOS:
        return USUARIOS[usuario]["paginas"]
    return []

def tem_acesso_pagina(usuario, pagina):
    """Verifica se o usuário tem acesso à página específica"""
    paginas_permitidas = get_paginas_permitidas(usuario)
    return pagina in paginas_permitidas

def mostrar_tela_login():
    """Mostra a tela de login centralizada usando colunas do Streamlit"""
    # CSS mínimo para esconder sidebar + rótulo dev fixo
    st.markdown("""
    <style>
        div[data-testid="stSidebar"] {
            display: none !important;
        }
        div[data-testid="collapsedControl"] {
            display: none !important;
        }
        .dev-label-fixed {
            position: fixed;
            bottom: 12px;
            right: 16px;
            font-size: 11px;
            color: #BFCF99;
            font-family: 'Poppins', sans-serif;
            font-weight: 500;
            opacity: 0.75;
            z-index: 99999;
            letter-spacing: 0.6px;
            text-shadow: 0 0 8px rgba(191,207,153,0.5);
            pointer-events: none;
        }
    </style>
    <div class="dev-label-fixed">Developed By: Matheus Resende</div>
    """, unsafe_allow_html=True)
    
    # Criar colunas para centralização [margem_esq, centro, margem_dir]
    col_esq, col_centro, col_dir = st.columns([1, 1.2, 1])
    
    with col_centro:
        # Espaço para descer o card na tela
        st.write("")
        st.write("")
        st.write("")
        
        # Logo centralizada
        try:
            logo_path = r"G:\.shortcut-targets-by-id\1JbWwLDR6PaShh0-_xJZLFAvEXQKn65V1\008 - Comercial\010 - Marketing\00 - Identidade Visual Afirma Evias\Manual Completo\Identidade Visual\Logotipo e Variações\Logotipo\PNG\AE - Logo Hor Principal_2.png"
            st.image(logo_path, width=840, use_container_width=False)
        except Exception:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #566E3D 0%, #6a8a4a 100%); 
                        padding: 1.5rem; border-radius: 16px; border: 3px solid #BFCF99; 
                        text-align: center; margin-bottom: 1.5rem;">
                <h2 style="color: white; margin: 0; font-size: 1.8rem;">AFIRMA E-VIAS</h2>
                <p style="color: #BFCF99; margin: 0.5rem 0 0 0;">Sistema de Gestão de Ensaios</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Card de login
        with st.container():
            st.markdown("""
            <style>
            .login-card {
                background: linear-gradient(135deg, #566E3D 0%, #6a8a4a 100%);
                border-radius: 16px;
                border: 3px solid #BFCF99;
                padding: 2rem;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                margin: 0 auto;
            }
            .login-title {
                color: white;
                text-align: center;
                margin-bottom: 1.5rem;
                font-size: 3.5rem;
            }
            </style>
            <div class="login-card">
                <h3 class="login-title"> Login</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Formulário dentro do card
            usuario = st.text_input("Usuário", placeholder="Digite seu usuário")
            senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            
            if st.button("Entrar", use_container_width=True):
                if verificar_login(usuario, senha):
                    st.session_state['logado'] = True
                    st.session_state['usuario'] = usuario
                    st.session_state['paginas_permitidas'] = get_paginas_permitidas(usuario)
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos!")

def verificar_autenticacao():
    """Verifica se o usuário está autenticado"""
    return st.session_state.get('logado', False)

def fazer_logout():
    """Realiza o logout do usuário"""
    for key in ['logado', 'usuario', 'paginas_permitidas']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()
