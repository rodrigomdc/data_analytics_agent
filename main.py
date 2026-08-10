# DEPOIS
import streamlit as st
from src.app.app import StreamlitApp
from src.utils.utils import reset_application_storage


@st.cache_resource
def bootstrap_system():
    """Executa a limpeza física de inicialização uma única vez no boot do servidor."""
    reset_application_storage()
    return True


# Executa sempre que o módulo é carregado pelo Streamlit
bootstrap_system()
app = StreamlitApp()
app.run()
