# ==========================================
# ESTILIZAÇÃO CSS (CORRIGIDA)
# ==========================================
css_code = """<style>
    /* Ocultar o cabeçalho superior nativo do Streamlit */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    [data-testid='stAppViewContainer'] {
        background-color: #F0F4F9 !important;
    }

    .main .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 1200px !important;
    }

    /* Sidebar */
    [data-testid='stSidebar'] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #D7E3F1;
    }
    [data-testid='stSidebar'] * {
        color: #103965 !important;
    }

    /* Ajuste das colunas centrais no Streamlit para compactar o formulário */
    [data-testid="column"] div[data-testid="stForm"] {
        background-color: #FFFFFF !important;
        padding: 1.5rem 1.5rem 1.2rem 1.5rem !important;
        border-radius: 16px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 10px 25px rgba(0, 33, 113, 0.08) !important;
        max-width: 380px !important;
        margin: 0 auto !important;
    }

    /* Imagem da logo compacta */
    .login-logo-img {
        max-width: 200px;
        width: 100%;
        height: auto;
        display: block;
        margin: 0 auto 0.8rem auto;
    }

    .login-welcome-title {
        color: #0D1B2A;
        font-size: 1.25rem;
        font-weight: 800;
        margin: 0 0 0.1rem 0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    .login-welcome-sub {
        color: #64748B;
        font-size: 0.85rem;
        margin-bottom: 1rem;
        font-weight: 500;
    }

    /* Estilização do Botão de Acesso */
    div[data-testid='stForm'] button[kind='secondaryFormSubmit'] {
        background-color: #0D47A1 !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.5rem 1rem !important;
        margin-top: 0.3rem !important;
    }

    div[data-testid='stForm'] button[kind='secondaryFormSubmit']:hover {
        background-color: #002171 !important;
        color: #FFFFFF !important;
    }

    .user-profile-card {
        background-color: #0D47A1;
        color: #FFFFFF;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1.2rem;
        border-left: 5px solid #5A9BE5;
    }

    .user-profile-card p {
        margin: 0;
        color: #FFFFFF !important;
    }
</style>"""
st.markdown(css_code, unsafe_allow_html=True)
