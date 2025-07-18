# NLP Analysis Pipeline for Online Media

[](https://www.python.org/downloads/)
[](https://opensource.org/licenses/MIT)

Questo repository fornisce una pipeline di analisi NLP (Natural Language Processing) end-to-end, progettata per raccogliere, processare, analizzare e visualizzare dati testuali da diverse fonti online.

Il progetto è strutturato in moduli sequenziali che permettono di eseguire un workflow completo, dalla raccolta dati grezzi fino all'indicizzazione dei risultati arricchiti su Elasticsearch per l'esplorazione interattiva.

-----

## Caratteristiche

  * **Raccolta Dati Multi-Fonte**: Script per collezionare dati da piattaforme social come **Reddit** e **Telegram**, e da testate giornalistiche tramite **web scraping**.
  * **Preprocessing Avanzato**: Pipeline di pulizia e normalizzazione del testo che include tokenizzazione, lemmatizzazione e gestione di `stopwords` customizzate tramite `spaCy`.
  * **Analisi Semantica**:
  * **Topic Modeling**: Implementazione di *Latent Dirichlet Allocation* (LDA) con `Gensim` per scoprire i temi latenti in un corpus.
  * **Sentiment Analysis**: Classificazione del sentiment (positivo, negativo, neutro) utilizzando modelli **Transformer** pre-addestrati da `Hugging Face`.
  * **Indicizzazione e Visualizzazione**: Script per caricare i dati finali su **Elasticsearch**, pronti per essere esplorati con dashboard **Kibana**.
  * **Workflow Modulare**: Il progetto è suddiviso in cartelle e script che rappresentano le diverse fasi del processo, rendendolo facilmente customizzabile ed estendibile.

-----

## Stack Tecnologico

  * **Linguaggio**: `Python`
  * **Analisi Dati**: `Pandas`, `NumPy`
  * **Raccolta Dati**: `PRAW` (Reddit), `Telethon` (Telegram), `Requests`, `BeautifulSoup`, `Newspaper3k`
  * **NLP**: `spaCy`, `Gensim`, `Hugging Face Transformers`, `PyTorch`, `NLTK`
  * **Database**: `Elasticsearch`
  * **Ambiente**: `Conda` (consigliato), `Docker` (per Elastic Stack)

-----

## Struttura del Progetto

Il repository è organizzato in cartelle che riflettono le fasi della pipeline:

```
.
├── Build_Dataset/      # Script per la raccolta dati da Reddit, Telegram e testate
├── Lemmatization/      # Script per il preprocessing e la lemmatizzazione del testo
├── Topic_Modeling/     # Script per l'addestramento del modello LDA e l'assegnazione dei topic
├── Sentiment_analysis/ # Script per l'analisi del sentiment
├── Elasticsearch/      # Script per l'indicizzazione dei dati su Elasticsearch
└── requirements.txt    # File con le dipendenze Python
```

-----

## Guida all'Installazione

### Prerequisiti

  * Python 3.10 o superiore
  * Accesso a un'istanza di [Elasticsearch](https://www.elastic.co/elasticsearch/) (si consiglia l'uso di [Docker](https://www.docker.com/))
  * Credenziali API per **Reddit** e **Telegram**

### Setup dell'Ambiente

Si consiglia di utilizzare `Conda` per creare un ambiente isolato.

1.  **Clona il repository**

    ```bash
    git clone https://github.com/Kymki/Tesi_Public.git
    cd Tesi_Public
    ```

2.  **Crea e attiva l'ambiente Conda**

    ```bash
    conda create --name nlp_pipeline python=3.10
    conda activate nlp_pipeline
    ```

3.  **Installa le dipendenze**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Scarica i modelli linguistici per `spaCy`**

    ```bash
    python -m spacy download en_core_web_sm
    python -m spacy download it_core_news_sm
    ```

5.  **Configura le credenziali API**
    Apri gli script di raccolta dati (es. `Build_Dataset/Telegram/01_telegram.py` e `Build_Dataset/Reddit/01_reddit.py`) e inserisci le tue credenziali API dove richiesto.

-----

## ▶️ Esecuzione della Pipeline

Gli script sono progettati per essere eseguiti in sequenza. Ogni fase dipende dall'output della precedente.

1.  **Fase 1: Raccolta Dati**
    Esegui gli script contenuti nella cartella `Build_Dataset/` per popolare il tuo dataset iniziale.

2.  **Fase 2: Preprocessing del Testo**
    Esegui lo script in `Lemmatization/` per pulire e lemmatizzare i dati raccolti.

      * `Lemmatization/01_pre-processing_1.1.py`

3.  **Fase 3: Analisi NLP**
    Esegui gli script nelle cartelle `Sentiment_analysis/` e `Topic_Modeling/` per arricchire i dati con le analisi semantiche.

      * `Sentiment_analysis/01_sent.py`
      * `Topic_Modeling/01_topic.py`
      * `Topic_Modeling/02_labeling.py`

4.  **Fase 4: Indicizzazione**
    Infine, esegui gli script nella cartella `Elasticsearch/` per caricare i dati finali nella tua istanza di Elasticsearch.

      * `Elasticsearch/01_indexer.py`
      * `Elasticsearch/02_indexer_topic.py`

Una volta indicizzati, i dati possono essere esplorati e visualizzati tramite **Kibana**.

-----
