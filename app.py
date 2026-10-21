# ==========================================
# ESTILIZAÇÃO CSS (OCULTAR HEADER E FIXAR LOGIN)
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

    /* FIXAÇÃO E CENTRALIZAÇÃO TOTAL DO LOGIN */
    .login-wrapper {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: #F0F4F9;
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 99999;
        padding: 20px;
        box-sizing: border-box;
    }

    .login-card {
        width: 100%;
        max-width: 450px;
    }

    /* Cartão de LOGIN expandido */
    .login-card div[data-testid='stForm'] {
        background-color: #FFFFFF !important;
        padding: 2.5rem 2.5rem 2rem 2.5rem !important;
        border-radius: 20px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 12px 35px rgba(0, 33, 113, 0.09) !important;
        width: 100% !important;
    }

    .login-logo-img {
        max-width: 280px;
        width: 100%;
        height: auto;
        display: block;
        margin: 0 auto 1.2rem auto;
    }

    .login-welcome-title {
        color: #0D1B2A;
        font-size: 1.5rem;
        font-weight: 800;
        margin: 0 0 0.2rem 0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    .login-welcome-sub {
        color: #64748B;
        font-size: 0.92rem;
        margin-bottom: 1.5rem;
        font-weight: 500;
    }

    /* Formulários e Cartões Internos Elegantes */
    div[data-testid='stForm'] {
        background-color: #FFFFFF !important;
        border-radius: 16px !important;
        border: 1px solid #E2E8F0 !important;
        padding: 1.8rem !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04) !important;
    }

    /* Estilização dos Botões de Ação */
    div[data-testid='stForm'] button[kind='secondaryFormSubmit'] {
        background-color: #0D47A1 !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 0.7rem 1.5rem !important;
        margin-top: 0.5rem !important;
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
