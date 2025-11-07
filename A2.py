import streamlit as st
import pandas as pd
from gnews import GNews
import google.generativeai as genai
import os
import re
import spacy
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO

# === 1. Configuração Inicial e de API ===

# Título da Aplicação
st.set_page_config(
    page_title="Agente de Notícias Parlamentares",
    layout="wide"
)

st.title("📰 Agente de Notícias e Análise de Parlamentares")
st.markdown("Use o Gemini e a GNews para obter um resumo de notícias e gerar uma nuvem de palavras sobre um deputado.")
st.markdown("---")

# Configuração da API do Gemini
try:
    # O Streamlit carrega a chave do arquivo .streamlit/secrets.toml
    GOOGLE_API_KEY = st.secrets["AIzaSyCVIS15AaZ2CHYAJI0-Q-HUDL_wrAED30o"]
    if not GOOGLE_API_KEY:
       raise ValueError("A chave 'GEMINI_API_KEY' foi lida mas está vazia.")
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    st.sidebar.success("✅ Gemini API configurada com sucesso!")
except KeyError: 
    st.sidebar.error("Erro: Chave 'GEMINI_API_KEY'não encontrada nas Secrets do Streamlit Cloud.")
except Exception as e:
    st.sidebar.error(f"❌ Erro ao configurar a API do Gemini. Certifique-se de que a `GEMINI_API_KEY` está no seu `secrets.toml`. {e}")
    st.stop() # Interrompe a execução se a API não estiver configurada.

# === Carregamento do Modelo Spacy (Simples) ===

@st.cache_resource
def load_spacy_model():
    """Carrega o modelo Spacy uma única vez."""
    try:
        nlp = spacy.load("pt_core_news_sm")
        st.sidebar.success("✅ Modelo Spacy (pt_core_news_sm) carregado.")
        return nlp
    except IOError:
        st.error("❌ Erro no Spacy: O modelo 'pt_core_news_sm' não foi instalado corretamente. Verifique o requirements.txt.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Erro ao carregar modelo Spacy: {e}")
        st.stop()

nlp = load_spacy_model()

# === 2. Funções de Carregamento e Seleção (Adaptadas para Streamlit) ===

@st.cache_data
def carregar_lista_deputados(uploaded_file):
    """
    Carrega a lista de deputados de um arquivo .csv, .xls ou .xlsx
    enviado pelo usuário.
    """
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.xls') or uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        else:
            st.error("Formato de arquivo não suportado. Use .csv, .xls ou .xlsx.")
            return None, None

        coluna_alvo_1 = "nome parlamentar"
        coluna_alvo_2 = "nome"

        coluna_nome = next((col for col in df.columns if col.lower() == coluna_alvo_1), None)

        if not coluna_nome:
            coluna_nome = next((col for col in df.columns if col.lower() == coluna_alvo_2), None)

        if not coluna_nome:
            st.error(f"Erro: Não foi possível encontrar uma coluna '{coluna_alvo_1}' ou '{coluna_alvo_2}' no arquivo.")
            return None, None

        return df, coluna_nome

    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")
        return None, None

# === 3. Funções de Notícias e Resumo ===

def buscar_noticias(deputado):
    """Busca notícias no GNews."""
    google_news = GNews(language='pt', country='BR', max_results=10)
    noticias = google_news.get_news(f"deputado {deputado}")

    if not noticias:
        return None, None

    # Texto concatenado para Nuvem de Palavras
    texto_noticias = " ".join([f"{artigo.get('title', '')} {artigo.get('description', '')}"
                               for artigo in noticias
                               if artigo.get('description')])

    # Prompt formatado para o Gemini
    prompt_noticias = "\n".join([f"- Título: {artigo.get('title', 'N/A')}\n  Descrição: {artigo.get('description', 'N/A')}"
                                 for artigo in noticias])

    return texto_noticias, prompt_noticias

def resumir_noticias_com_gemini(prompt_noticias, nome_deputado, model):
    """Usa a API do Gemini para gerar um resumo das notícias."""
    prompt_completo = f"""
    Você é um assistente de notícias políticas. Com base nos seguintes artigos sobre {nome_deputado},
    forneça um resumo conciso e informativo dos principais pontos.

    Artigos:
    {prompt_noticias}

    Resumo:
    """
    try:
        response = model.generate_content(prompt_completo)
        return response.text
    except Exception as e:
        return f"Erro ao gerar resumo com Gemini: {e}"

# === 4. Funções da Nuvem de Palavras ===

def limpar_texto_para_nuvem(texto, nome_deputado, nlp):
    """Limpa o texto usando Spacy."""
    palavras_nome = nome_deputado.lower().split()
    # Adiciona palavras do nome do deputado às stopwords
    stop_words_custom = nlp.Defaults.stop_words.union(palavras_nome)

    doc = nlp(texto.lower())

    tokens_limpos = []
    for token in doc:
        if (token.text not in stop_words_custom and
            not token.is_punct and
            not token.is_space and
            not token.like_num and
            len(token.text) > 2): # Remove palavras muito curtas
            tokens_limpos.append(token.lemma_)

    if not tokens_limpos:
        return None

    return " ".join(tokens_limpos)

def gerar_nuvem_de_palavras(texto, nome_deputado):
    """
    Gera a nuvem de palavras e a retorna como um objeto Matplotlib.
    Adaptado para o Streamlit (não usa plt.show()).
    """
    if not texto:
        return None

    texto_limpo = limpar_texto_para_nuvem(texto, nome_deputado, nlp)

    if not texto_limpo:
        return None

    try:
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white',
            colormap='viridis',
            collocations=False
        ).generate(texto_limpo)

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')

        return fig # Retorna a figura do Matplotlib
    except Exception as e:
        st.error(f"Erro ao gerar a nuvem de palavras: {e}")
        return None

# === 5. Interface Principal do Streamlit ===

# --- Upload e Carregamento de Dados ---
uploaded_file = st.sidebar.file_uploader(
    "1. Escolha o arquivo de deputados (.csv, .xls, .xlsx)",
    type=["csv", "xls", "xlsx"]
)

if uploaded_file:
    with st.spinner("Carregando e processando lista de deputados..."):
        df_deputados, coluna_nome = carregar_lista_deputados(uploaded_file)

    if df_deputados is not None:
        st.sidebar.success(f"Lista carregada! Coluna de nome: **{coluna_nome}**")

        # --- Seleção do Deputado ---
        nomes_completos = df_deputados[coluna_nome].unique().tolist()
        nome_selecionado = st.sidebar.selectbox(
            "2. Selecione o Deputado(a)",
            options=[""] + nomes_completos,
            index=0
        )

        if nome_selecionado:
            st.sidebar.markdown("---")
            st.sidebar.header(f"Executar Análise para:")
            st.sidebar.markdown(f"**{nome_selecionado}**")
            # Botão de Execução Principal
            if st.sidebar.button("3. 🚀 Iniciar Análise"):
                st.session_state['nome_analise'] = nome_selecionado
                st.session_state['executar_analise'] = True
            
        else:
            st.warning("Selecione um deputado para começar a análise.")

# --- Área de Resultados ---
if 'executar_analise' in st.session_state and st.session_state['executar_analise']:
    nome_selecionado = st.session_state['nome_analise']

    st.header(f"Resultados da Análise para: **{nome_selecionado}**")
    st.markdown("---")

    # 1. Busca de Notícias
    with st.spinner(f"Buscando notícias no GNews para {nome_selecionado}..."):
        texto_noticias, prompt_noticias = buscar_noticias(nome_selecionado)

    if texto_noticias:
        # 2. Geração do Resumo
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📝 Resumo das Notícias (via Gemini)")
            with st.spinner("Gerando resumo com Gemini..."):
                resumo_noticias = resumir_noticias_com_gemini(prompt_noticias, nome_selecionado, model)
                st.info(resumo_noticias)
        
        # 3. Geração da Nuvem de Palavras
        with col2:
            st.subheader("☁️ Nuvem de Palavras-Chave")
            with st.spinner("Gerando Nuvem de Palavras (WordCloud)..."):
                fig_wordcloud = gerar_nuvem_de_palavras(texto_noticias, nome_selecionado)
                if fig_wordcloud:
                    st.pyplot(fig_wordcloud)
                else:
                    st.warning("Não foi possível gerar a Nuvem de Palavras. Pouco texto relevante encontrado.")

    else:
        st.warning(f"Não foi possível encontrar notícias recentes para **{nome_selecionado}** no GNews.")

    st.session_state['executar_analise'] = False # Reseta a flag após a execução
elif uploaded_file and 'df_deputados' not in st.session_state:
    st.info("Arquivo de deputados carregado. Agora selecione um nome na barra lateral e clique em 'Iniciar Análise'.")
else:
    st.info("Faça o upload de um arquivo de deputados na barra lateral para começar.")
