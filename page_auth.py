"""
Proteção de autenticação para páginas individuais
"""
import streamlit as st
from auth import verificar_autenticacao, tem_acesso_pagina, fazer_logout

def proteger_pagina(nome_pagina):
    """
    Protege uma página verificando autenticação e permissão
    Se não estiver autenticado, redireciona para a página principal
    Se não tiver permissão, mostra mensagem de acesso negado
    """
    # Verificar se está autenticado
    if not verificar_autenticacao():
        st.error("Você precisa fazer login para acessar esta página.")
        st.markdown("[Ir para página de login](app.py)")
        st.stop()
    
    # Verificar permissão para a página específica
    usuario = st.session_state.get('usuario', '')
    if not tem_acesso_pagina(usuario, nome_pagina):
        st.error(f"Você não tem permissão para acessar: {nome_pagina}")
        st.markdown("[Voltar para o Dashboard](app.py)")
        st.stop()
    
    # Mostrar informações do usuário na sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Usuário:** {usuario}")
    st.sidebar.markdown(f"**Página:** {nome_pagina}")
    if st.sidebar.button("Logout", use_container_width=True):
        fazer_logout()
