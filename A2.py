# === Bloco 1: Instalações ===
!pip install -q --upgrade google-generativeai
!pip install -q wordcloud gnews pandas openpyxl matplotlib
!python -m spacy download pt_core_news_sm


# === Bloco 2: Imports ===
import pandas as pd
from gnews import GNews
import google.generativeai as genai
from google.colab import userdata
import os
import re
import spacy
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from IPython.display import Image, display


try:
    nlp = spacy.load("pt_core_news_sm")
except IOError:
    print("Modelo 'pt_core_news_sm' não encontrado. Baixando...")
    !python -m spacy download pt_core_news_sm
    nlp = spacy.load("pt_core_news_sm")
print("Modelo Spacy (pt) carregado.")
print("-"*40)


# === Bloco 3: Configuração da API ===
try:
    GOOGLE_API_KEY = userdata.get('GEMINI_API_KEY')
    if not GOOGLE_API_KEY:
        raise ValueError("A chave 'GEMINI_API_KEY' não foi encontrada ou está vazia.")
    genai.configure(api_key=GOOGLE_API_KEY)
    print("Chave de API do Gemini carregada e configurada com sucesso.")
except Exception as e:
    print(f"Erro ao configurar a API do Gemini: {e}")
    print("Por favor, configure a 'GEMINI_API_KEY' nos segredos do Colab.")
print("-"*40)


# === Bloco 4: Funções de Carregamento e Seleção ===

def carregar_lista_deputados(caminho_arquivo):
    """
    Carrega a lista de deputados de um arquivo .csv, .xls ou .xlsx.
    """
    print(f"Carregando lista de deputados de '{caminho_arquivo}'...")
    try:
        if caminho_arquivo.endswith('.csv'):
            df = pd.read_csv(caminho_arquivo)
        elif caminho_arquivo.endswith('.xls') or caminho_arquivo.endswith('.xlsx'):
            df = pd.read_excel(caminho_arquivo)
        else:
            print("Formato de arquivo não suportado. Use .csv, .xls ou .xlsx")
            return None

        coluna_alvo_1 = "nome parlamentar"
        coluna_alvo_2 = "nome"

        coluna_nome = next((col for col in df.columns if col.lower() == coluna_alvo_1), None)

        if not coluna_nome:
            coluna_nome = next((col for col in df.columns if col.lower() == coluna_alvo_2), None)

        if not coluna_nome:
            print(f"Erro: Não foi possível encontrar uma coluna '{coluna_alvo_1}' ou '{coluna_alvo_2}' no arquivo {caminho_arquivo}.")
            print(f"Colunas encontradas: {df.columns.tolist()}")
            return None

        print(f"Lista carregada com sucesso. Usando a coluna: '{coluna_nome}'")
        return df, coluna_nome

    except FileNotFoundError:
        print(f"Erro: Arquivo '{caminho_arquivo}' não encontrado.")
        print("Por favor, faça o upload do arquivo para o ambiente do Colab.")
        return None
    except Exception as e:
        print(f"Erro ao ler o arquivo: {e}")
        return None

def selecionar_deputado(df, coluna_nome):
    """
    Permite ao usuário buscar e selecionar um deputado da lista.
    """
    while True:
        nome_input = input("Digite o nome do deputado(a) que deseja pesquisar: ")
        if not nome_input:
            print("Por favor, digite um nome.")
            continue

        try:
            resultados = df[df[coluna_nome].str.contains(nome_input, case=False, na=False, flags=re.IGNORECASE)]
        except Exception as e:
            print(f"Erro ao buscar nome: {e}")
            continue

        if resultados.empty:
            print("Nenhum deputado(a) encontrado com esse nome. Tente novamente.")
        elif len(resultados) == 1:
            nome_selecionado = resultados.iloc[0][coluna_nome]
            print(f"Deputado(a) selecionado(a): {nome_selecionado}")
            return nome_selecionado
        else:
            print("Vários deputados(as) encontrados. Por favor, seja mais específico:")
            print(resultados[coluna_nome].head(10).tolist())

# === Bloco 5: Funções de Notícias e Resumo (ATUALIZADO) ===

def buscar_noticias(deputado):
    """
    Busca notícias no GNews e retorna o texto concatenado e o prompt para o Gemini.
    """
    print(f"Buscando notícias sobre: {deputado}...")
    google_news = GNews(language='pt', country='BR', max_results=10)
    noticias = google_news.get_news(f"deputado {deputado}")

    if not noticias:
        print("Nenhuma notícia encontrada.")
        return None, None

    texto_noticias = " ".join([f"{artigo['title']} {artigo['description']}"
                             for artigo in noticias
                             if artigo['description']])

    prompt_noticias = "\n".join([f"- Título: {artigo['title']}\n  Descrição: {artigo['description']}"
                               for artigo in noticias])

    return texto_noticias, prompt_noticias

def resumir_noticias_com_gemini(prompt_noticias, nome_deputado):
    """
    Usa a API do Gemini para gerar um resumo das notícias.
    """
    print("Enviando notícias para o Gemini para resumo...")
  
    # --- INÍCIO DA ALTERAÇÃO ---
    # ATUALIZAÇÃO 2: Usando o modelo 'gemini-1.5-flash'.
    # Este é o modelo mais recente e rápido, ideal para resumos.
    # A atualização da biblioteca no Bloco 1 garante que ele será encontrado.
    model = genai.GenerativeModel('gemini-2.5-flash')
    # --- FIM DA ALTERAÇÃO ---

    prompt_completo = f"""
    Você é um assistente de notícias políticas. Com base nos seguintes artigos sobre {nome_deputado},
    forneça um resumo conciso e informativo dos principais pontos.

    Artigos:
    {prompt_noticias}

    Resumo:
    """

    response = model.generate_content(prompt_completo)
    return response.text



# === Bloco 6: Função da Nuvem de Palavras (com 'wordcloud') ===

def limpar_texto_para_nuvem(texto, nome_deputado):
    """
    Usa o spacy para processar o texto, remover stopwords, pontuação
    e o nome do próprio deputado (para não poluir a nuvem).
    """
    print("Iniciando processamento de texto para nuvem de palavras (Spacy)...")

    palavras_nome = nome_deputado.lower().split()
    stop_words_custom = nlp.Defaults.stop_words.union(palavras_nome)

    doc = nlp(texto.lower())

    tokens_limpos = []
    for token in doc:
        if (token.text not in stop_words_custom and
            not token.is_punct and
            not token.is_space and
            not token.like_num):
            tokens_limpos.append(token.lemma_)

    if not tokens_limpos:
        print("Nenhuma palavra-chave encontrada após a limpeza.")
        return None

    return " ".join(tokens_limpos)

def gerar_nuvem_de_palavras(texto, nome_deputado):
    """
    Gera e exibe uma nuvem de palavras a partir do texto das notícias usando 'wordcloud'.
    """
    if not texto:
        print("Texto vazio, não é possível gerar nuvem de palavras.")
        return

    texto_limpo = limpar_texto_para_nuvem(texto, nome_deputado)

    if not texto_limpo:
        print("Não foi possível gerar a nuvem, texto limpo está vazio.")
        return

    print("Gerando a imagem da nuvem de palavras (WordCloud)...")

    try:
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white',
            colormap='viridis',
            collocations=False
        ).generate(texto_limpo)

        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.show()

        nome_arquivo = f"nuvem_{nome_deputado.lower().replace(' ', '_')}.png"
        wordcloud.to_file(nome_arquivo)
        print(f"Nuvem de palavras salva como '{nome_arquivo}'")

    except Exception as e:
        print(f"Erro ao gerar a nuvem de palavras com 'wordcloud': {e}")


# === Bloco 7: Execução Principal ===

def main():
    print("--- Agente de Notícias e Análise de Parlamentares ---")

    # 1. Definir o nome do arquivo
    # ATENÇÃO: Certifique-se que este nome bate com o seu arquivo
    # Ex: "deputado.xls", "deputados_2022.csv"
    arquivo_deputados = "deputado.xls"

    if not os.path.exists(arquivo_deputados):
        print(f"Erro Crítico: O arquivo '{arquivo_deputados}' não foi encontrado.")
        print("Por favor, faça o upload do arquivo para o ambiente do Colab e tente novamente.")
        return

    # 2. Carregar e selecionar deputado
    dados_deputados = carregar_lista_deputados(arquivo_deputados)

    if dados_deputados:
        df, coluna_nome = dados_deputados
        nome_selecionado = selecionar_deputado(df, coluna_nome)

        if nome_selecionado:
            # 3. Buscar Notícias
            texto_noticias, prompt_noticias = buscar_noticias(nome_selecionado)

            if texto_noticias:
                # 4. Gerar Resumo com Gemini
                resumo_noticias = resumir_noticias_com_gemini(prompt_noticias, nome_selecionado)
                print("\n" + "="*30)
                print("   Resumo das Notícias (via Gemini)")
                print("="*30)
                print(resumo_noticias)

                # 5. Gerar Nuvem de Palavras
                print("\n" + "="*30)
                print("   Nuvem de Palavras (via WordCloud)")
                print("="*30)
                gerar_nuvem_de_palavras(texto_noticias, nome_selecionado)
            else:
                print(f"Não foi possível encontrar notícias ou texto para {nome_selecionado}.")
    else:
        print("Não foi possível carregar a lista de deputados. Encerrando o programa.")

# === PONTO DE PARTIDA ===
main()
