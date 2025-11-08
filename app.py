import streamlit as st
import spacy
import google.generativeai as genai
from gnews import GNews
from wordcloud import WordCloud
import re

# --- Configuração da Página e Funções Essenciais ---

# Configura o título da página e o layout
st.set_page_config(page_title="Análise Política", layout="wide")

# Carrega o modelo Spacy para Português (cache para performance)
@st.cache_resource
def load_spacy_model():
    """Carrega o modelo 'pt_core_news_sm' do Spacy."""
    return spacy.load("pt_core_news_sm")

nlp = load_spacy_model()

# Configura a API do Gemini
try:
    # Tenta carregar a API Key dos segredos do Streamlit
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
except (KeyError, FileNotFoundError):
    st.error("Chave de API do Gemini não encontrada. Por favor, adicione-a ao arquivo `.streamlit/secrets.toml`.")
    model = None

# --- Funções de Lógica do Aplicativo ---

def fetch_news(deputy_name):
    """Busca notícias usando GNews para o nome do deputado."""
    try:
        google_news = GNews(language='pt', country='BR', max_results=10)
        # Adiciona "deputado federal" para especificar a busca
        search_query = f'"{deputy_name}" deputado federal'
        articles = google_news.get_news(search_query)
        
        if not articles:
            st.warning("Nenhuma notícia recente encontrada para este parlamentar.")
            return None, None

        # Concatena títulos e descrições
        full_text = " ".join([
            (art['title'] + " " + art['description']) 
            for art in articles if art['description']
        ])
        
        return full_text, articles
    except Exception as e:
        st.error(f"Erro ao buscar notícias: {e}")
        return None, None

def summarize_with_gemini(text_to_summarize):
    """Envia o texto das notícias para o Gemini e retorna um resumo."""
    if not model:
        return "Erro: Modelo Gemini não foi inicializado."

    prompt = f"""
    Você é um analista político sênior.
    Com base nos seguintes títulos e descrições de notícias recentes, gere um resumo conciso e informativo.
    Identifique os fatos centrais e os temas mais prementes associados ao parlamentar mencionado.

    Notícias:
    {text_to_summarize}

    Resumo Analítico:
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Erro ao gerar resumo com o Gemini: {e}")
        return "Não foi possível gerar o resumo."

def clean_text_and_generate_wordcloud(text, deputy_name):
    """Limpa o texto (stopwords, pontuação, nome do deputado) e gera a nuvem de palavras."""
    
    # 1. Processar o texto com Spacy
    doc = nlp(text.lower())
    
    # 2. Obter partes do nome do deputado para remoção
    name_parts = deputy_name.lower().split()
    
    # 3. Lemmatização e remoção de stopwords, pontuação e o nome
    lemmas = []
    for token in doc:
        if (
            not token.is_stop and     # Remove stopwords (ex: 'o', 'de', 'para')
            not token.is_punct and    # Remove pontuação (ex: '.', ',')
            token.text not in name_parts and # Remove partes do nome
            len(token.lemma_) > 3     # Remove palavras muito curtas
        ):
            lemmas.append(token.lemma_)
            
    processed_text = " ".join(lemmas)
    
    if not processed_text:
        st.warning("Não há texto suficiente para gerar a nuvem de palavras após a limpeza.")
        return None

    # 4. Gerar a Nuvem de Palavras
    try:
        wordcloud = WordCloud(
            width=800, 
            height=400, 
            background_color='white',
            colormap='viridis',
            max_words=100
        ).generate(processed_text)
        
        # Converte a nuvem para uma imagem que o Streamlit possa exibir
        image = wordcloud.to_image()
        return image
    except ValueError:
        st.info("Texto insuficiente para gerar a nuvem de palavras.")
        return None

# --- Interface do Usuário (Streamlit) ---

st.title("🤖 Ferramenta de Análise Política Automatizada")
st.markdown("Monitore a percepção pública de deputados federais através de notícias recentes.")

# Entrada do usuário
deputy_name = st.text_input("Digite o nome do Deputado Federal:", placeholder="Ex: Arthur Lira")

if st.button("Analisar Parlamentar"):
    if not deputy_name:
        st.error("Por favor, digite um nome para pesquisar.")
    elif not model:
         st.error("A aplicação não pode funcionar sem a API Key do Gemini.")
    else:
        with st.spinner(f"Buscando e analisando notícias sobre {deputy_name}..."):
            
            # 1. Buscar Notícias
            news_text, articles = fetch_news(deputy_name)
            
            if news_text:
                # 2. Gerar Resumo Analítico (Gemini)
                st.subheader("1. Relatório Textual Analítico (via Gemini)")
                summary = summarize_with_gemini(news_text)
                st.write(summary)
                
                # 3. Gerar Relatório Visual (Word Cloud)
                st.subheader("2. Relatório Visual (Nuvem de Palavras)")
                st.markdown(
                    "Termos e conceitos mais frequentes associados ao parlamentar "
                    "(após remoção de stopwords e do nome do deputado)."
                )
                
                wordcloud_image = clean_text_and_generate_wordcloud(news_text, deputy_name)
                
                if wordcloud_image:
                    st.image(wordcloud_image, use_column_width=True)
                
                # Bônus: Mostrar as fontes das notícias
                with st.expander("Ver fontes das notícias coletadas"):
                    for art in articles:
                        st.markdown(f"- [{art['title']}]({art['url']}) *({art['publisher']['title']})*")
