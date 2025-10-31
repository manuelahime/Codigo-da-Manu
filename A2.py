python -m venv venv
source venv/bin/activate  

pip install -r requirements.txt

streamlit run app.py

import streamlit as st
import pandas as pd
from gnews import GNews
import google.generativeai as genai
import os
import re
import spacy
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io

# === Configuração da Página ===
st.set_page_config(page_title="Analisador de Notícias de Parlamentares", layout="wide")
st.title("🔎 Agente de Notícias e Análise de Parlamentares")

# === Bloco 1: Funções de Carregamento (com Cache) ===
# Estas funções SÓ SERÃO EXECUTADAS quando chamadas, não mais no início

@st.cache_resource
def carregar_modelo_spacy():
    """
    Carrega o modelo de linguagem do Spacy.
    Assume que 'pt_core_news_sm' foi instalado via requirements.txt.
    """
    try:
        nlp = spacy.load("pt_core_news_sm")
        return nlp
    except IOError:
        st.error("Erro Crítico: Não foi possível carregar o modelo 'pt_core_news_sm'.")
        st.info("Por favor, pare o servidor (Ctrl+C no terminal), rode 'pip install -r requirements.txt' novamente e tente 'streamlit run app.py'.")
        return None

@st.cache_data
def carregar_lista_deputados(arquivo_upado):
    """
    Carrega a lista de deputados de um arquivo .csv, .xls ou .xlsx.
    """
    try:
        if arquivo_upado.name.endswith('.csv'):
            df = pd.read_csv(arquivo_upado)
        elif arquivo_upado.name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(arquivo_upado)
        else:
            st.error("Formato de arquivo não suportado. Use .csv, .xls ou .xlsx")
            return None, None
        
        coluna_alvo_1 = "nome parlamentar"
        coluna_alvo_2 = "nome"
        
        coluna_nome = next((col for col in df.columns if col.lower() == coluna_alvo_1), None)
        if not coluna_nome:
            coluna_nome = next((col for col in df.columns if col.lower() == coluna_alvo_2), None)
        
        if not coluna_nome:
            st.error(f"Erro: Não foi possível encontrar uma coluna 'Nome Parlamentar' ou 'Nome' no arquivo.")
            st.info(f"Colunas encontradas: {df.columns.tolist()}")
            return None, None
            
        return df, coluna_nome
        
    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")
        return None, None

def configurar_api_gemini():
    """Configura a API do Gemini usando os segredos do Streamlit."""
    try:
        GOOGLE_API_KEY = st.secrets['GEMINI_API_KEY']
        genai.configure(api_key=GOOGLE_API_KEY)
        return True
    except KeyError:
        st.error("Erro: A chave 'GEMINI_API_KEY' não foi encontrada nos Segredos (Secrets) do Streamlit.")
        st.info("Por favor, crie um arquivo .streamlit/secrets.toml e adicione sua chave lá.")
        return False
    except Exception as e:
        st.error(f"Erro ao configurar a API do Gemini: {e}")
        return False

# === Bloco 2: Funções de Lógica (Notícias, Resumo, Nuvem) ===

def buscar_noticias(deputado):
    """Busca notícias no GNews."""
    google_news = GNews(language='pt', country='BR', max_results=10)
    noticias = google_news.get_news(f"deputado {deputado}")
    
    if not noticias:
        return None, None

    texto_noticias = " ".join([f"{artigo['title']} {artigo['description']}" 
                             for artigo in noticias 
                             if artigo['description']])
    
    prompt_noticias = "\n".join([f"- Título: {artigo['title']}\n  Descrição: {artigo['description']}" 
                               for artigo in noticias])
    
    return texto_noticias, prompt_noticias

def resumir_noticias_com_gemini(prompt_noticias, nome_deputado):
    """Usa a API do Gemini para gerar um resumo das notícias."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt_completo = f"""
        Você é um assistente de notícias políticas. Com base nos seguintes artigos sobre {nome_deputado}, 
        forneça um resumo conciso e informativo dos principais pontos.

        Artigos:
        {prompt_noticias}

        Resumo:
        """
        response = model.generate_content(prompt_completo)
        return response.text
    except Exception as e:
        st.error(f"Erro ao gerar conteúdo do Gemini: {e}")
        return "Erro na geração do resumo."

def gerar_nuvem_de_palavras(nlp_model, texto, nome_deputado): # Adicionamos nlp_model como argumento
    """
    Processa o texto com Spacy e gera uma figura do Matplotlib com a nuvem de palavras.
    """
    palavras_nome = nome_deputado.lower().split()
    stop_words_custom = nlp_model.Defaults.stop_words.union(palavras_nome)
    
    doc = nlp_model(texto.lower())
    tokens_limpos = []
    for token in doc:
        if (token.text not in stop_words_custom and 
            not token.is_punct and 
            not token.is_space and 
            not token.like_num):
            tokens_limpos.append(token.lemma_)
            
    if not tokens_limpos:
        st.warning("Nenhuma palavra-chave encontrada após a limpeza para a nuvem.")
        return None
    
    texto_limpo = " ".join(tokens_limpos)
    
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
        return fig

    except Exception as e:
        st.error(f"Erro ao gerar a nuvem de palavras: {e}")
        return None


# === Bloco 3: Interface do Aplicativo (Streamlit) ===

st.header("1. Carregar Lista de Parlamentares")
uploaded_file = st.file_uploader("Faça o upload do seu arquivo (Excel ou CSV)", type=["xls", "xlsx", "csv"])

if uploaded_file is not None:
    df, coluna_nome = carregar_lista_deputados(uploaded_file)
    
    if df is not None:
        st.header("2. Selecionar Parlamentar")
        
        nomes_lista = ["Selecione..."] + sorted(df[coluna_nome].unique())
        nome_selecionado = st.selectbox("Escolha um(a) parlamentar da lista:", options=nomes_lista)
        
        if nome_selecionado != "Selecione...":
            st.header("3. Gerar Análise")
            
            if st.button(f"Analisar {nome_selecionado}"):
                
                # --- INÍCIO DA ALTERAÇÃO ---
                # SÓ AGORA vamos carregar a API e o Modelo
                
                with st.spinner("Configurando API e carregando modelo de linguagem..."):
                    api_configurada = configurar_api_gemini()
                    nlp = carregar_modelo_spacy()
                
                # Se a configuração ou o modelo falharem, paramos aqui
                if not api_configurada:
                    st.error("Falha na configuração da API. Verifique o secrets.toml e tente novamente.")
                    st.stop() # Para a execução
                
                if not nlp:
                    st.error("Falha ao carregar modelo Spacy. Verifique a instalação (requirements.txt) e tente novamente.")
                    st.stop() # Para a execução
                
                st.success("Modelos e API carregados com sucesso!")
                # --- FIM DA ALTERAÇÃO ---

                with st.spinner(f"Buscando notícias recentes sobre {nome_selecionado}..."):
                    texto_noticias, prompt_noticias = buscar_noticias(nome_selecionado)
                
                if not texto_noticias:
                    st.error(f"Nenhuma notícia encontrada para {nome_selecionado}.")
                else:
                    st.success("Notícias encontradas!")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Resumo das Notícias (via Gemini)")
                        with st.spinner("Gerando resumo com IA..."):
                            resumo_noticias = resumir_noticias_com_gemini(prompt_noticias, nome_selecionado)
                            st.write(resumo_noticias)
                    
                    with col2:
                        st.subheader("Nuvem de Palavras (WordCloud)")
                        with st.spinner("Criando nuvem de palavras..."):
                            # Passamos o modelo 'nlp' que acabamos de carregar
                            fig_nuvem = gerar_nuvem_de_palavras(nlp, texto_noticias, nome_selecionado)
                            if fig_nuvem:
                                st.pyplot(fig_nuvem)
