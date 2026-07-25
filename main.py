import streamlit as st
from src.app.app import StreamlitApp
from src.utils.utils import reset_application_storage


@st.cache_resource
def bootstrap_system():
    """Executa a limpeza física de inicialização uma única vez no boot do servidor."""
    reset_application_storage()
    return True


if __name__ == "__main__":
    # Garante que o ambiente esteja 100% limpo antes de instanciar a UI
    bootstrap_system()
    # Instancia e roda a aplicação Streamlit
    app = StreamlitApp()
    app.run()
