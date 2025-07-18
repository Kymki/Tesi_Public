# config.py

import os

# --- Configurazione delle directory di base ---
# Definisci la directory radice del progetto per costruire percorsi relativi.
# Assumi che 'config.py' sia nella radice o un livello sotto 'src/'.
# Ad esempio, se config.py è in 'Tesi_Public/', ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
# Se config.py è in 'Tesi_Public/src/', ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directory per i dati grezzi
RAW_DATA_DIR = os.path.join(ROOT_DIR, "data", "raw")
# Directory per i dati preprocessati (output della fase di Lemmatization)
PROCESSED_DATA_DIR = os.path.join(ROOT_DIR, "data", "processed")
# Directory per i risultati delle analisi (Topic Modeling, Sentiment Analysis)
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
# Directory per i grafici e le visualizzazioni
CHARTS_DIR = os.path.join(ROOT_DIR, "charts")

# Assicurati che le directory esistano
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(os.path.join(RESULTS_DIR, "topic_modeling"), exist_ok=True)
os.makedirs(os.path.join(RESULTS_DIR, "sentiment_analysis"), exist_ok=True)


# --- Percorsi dei file specifici (Input/Output) ---

# Build_Dataset - Papers
# Nota: per gli script di raccolta (01_kyiv_paper.py, 03_bbc_paper.py), 
# gli URL di partenza sono hardcoded, ma i file di output possono essere configurati.
KYIV_INDEPENDENT_ARCHIVE_URLS_CSV = os.path.join(RAW_DATA_DIR, "kyiv_independent_archive_article_urls.csv")
KYIV_INDEPENDENT_ARTICLES_EXTRACTED_CSV = os.path.join(RAW_DATA_DIR, "kyiv_independent_contenuti_articoli_estratti.csv")
BBC_NEWS_ARCHIVE_URLS_CSV = os.path.join(RAW_DATA_DIR, "bbc_news_archive_article_urls.csv")
BBC_NEWS_ARTICLES_EXTRACTED_CSV = os.path.join(RAW_DATA_DIR, "bbc_news_contenuti_articoli_estratti.csv")

# Build_Dataset - Reddit
REDDIT_POSTS_COLLECTED_CSV = os.path.join(RAW_DATA_DIR, "reddit_posts_raccolti.csv")
REDDIT_COMMENTS_COLLECTED_CSV = os.path.join(RAW_DATA_DIR, "reddit_comments_raccolti.csv")

# Build_Dataset - Telegram
TELEGRAM_MESSAGES_COLLECTED_CSV = os.path.join(RAW_DATA_DIR, "telegram_messaggi_raccolti.csv")

# Lemmatization (Output)
PROCESSED_CONSOLIDATED_CSV = os.path.join(PROCESSED_DATA_DIR, "dati_testuali_preproc_consolidati.csv")

# Topic_Modeling (Input/Output)
# L'input per 01_topic.py è il file consolidato dal preprocessing
TOPIC_MODELING_INPUT_CSV = PROCESSED_CONSOLIDATED_CSV
LDA_TOPICS_EN_TXT = os.path.join(RESULTS_DIR, "topic_modeling", "lda_topics_en.txt")
LDA_TOPICS_IT_TXT = os.path.join(RESULTS_DIR, "topic_modeling", "lda_topics_it.txt")
DOCUMENT_TOPICS_EN_CSV = os.path.join(RESULTS_DIR, "topic_modeling", "document_topics_en.csv")
DOCUMENT_TOPICS_IT_CSV = os.path.join(RESULTS_DIR, "topic_modeling", "document_topics_it.csv")

# Sentiment_analysis (Input/Output)
# L'input per 01_sent.py è il file consolidato dal preprocessing
SENTIMENT_ANALYSIS_INPUT_CSV = PROCESSED_CONSOLIDATED_CSV
SENTIMENT_FINAL_CSV = os.path.join(RESULTS_DIR, "sentiment_analysis", "dati_con_sentiment_finale.csv")

# Charts (Output)
DISTRIBUTION_TOPIC_CHART_EN_PNG = os.path.join(CHARTS_DIR, "distribuzione_topic_en.png")
DISTRIBUTION_TOPIC_CHART_IT_PNG = os.path.join(CHARTS_DIR, "distribuzione_topic_it.png")

# Elasticsearch (Input per gli indexer)
# L'input per 01_indexer.py è il file con il sentiment
ELASTICSEARCH_INDEXER_INPUT_CSV = SENTIMENT_FINAL_CSV
# L'input per 02_indexer_topic.py sono i file di topic per lingua
ELASTICSEARCH_INDEXER_TOPICS_EN_CSV = DOCUMENT_TOPICS_EN_CSV
ELASTICSEARCH_INDEXER_TOPICS_IT_CSV = DOCUMENT_TOPICS_IT_CSV

ELASTICSEARCH_HOST = "https://localhost:9200"
ELASTIC_USER = "elastic"
ELASTIC_PASSWORD = "elastic" # ### IMPORTANTE: SOSTITUISCI CON LA TUA PASSWORD REALE ###
INDEX_NAME_MAIN = "semantic_tesi"
INDEX_NAME_TOPIC = "topic_modeling_tesi"

# --- Credenziali API (NON caricarle su GitHub se sono reali!) ---
# È preferibile gestire queste credenziali come variabili d'ambiente o tramite un file .env
# Per semplicità di esempio, sono qui, ma SCONSIGLIATO PER LA PRODUZIONE.
REDDIT_CLIENT_ID = "IL_TUO_CLIENT_ID"
REDDIT_CLIENT_SECRET = "IL_TUO_CLIENT_SECRET"
REDDIT_USER_AGENT = "ScriptTesiV1.0 by ZeroCool 4(tesi di laurea)"

TELEGRAM_API_ID = 12345678 # Il tuo API_ID numerico
TELEGRAM_API_HASH = "IL_TUO_API_HASH" # Il tuo API_HASH alfanumerico
TELEGRAM_SESSION_NAME = "mia_sessione_tesi"
TELEGRAM_MESSAGE_LIMIT_PER_ENTITY = 1000 # Limite di messaggi per entità (o None per nessun limite)
TELEGRAM_START_DATE = (2022, 2, 1) # Anno, Mese, Giorno per la data di inizio raccolta