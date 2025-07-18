import pandas as pd
import gensim
from gensim import corpora
from gensim.models import LdaMulticore
import spacy
import nltk # installare prima di usare questo script: conda installa tutta la libreria per fare questo lavoro. Fantastico!
import re

# Importa le configurazioni dal file config.py
from config import (
    TOPIC_MODELING_INPUT_CSV,
    LDA_TOPICS_EN_TXT,
    DOCUMENT_TOPICS_EN_CSV,
    LDA_TOPICS_IT_TXT,
    DOCUMENT_TOPICS_IT_CSV,
    LDA_NUM_TOPICS_EN,
    LDA_NUM_PASSES_EN,
    LDA_WORKERS_EN,
    LDA_NUM_TOPICS_IT,
    LDA_NUM_PASSES_IT,
    LDA_WORKERS_IT
)

# --- CONFIGURAZIONE SPECIFICA (mantenuta qui o spostata se utile altrove) ---
# Nomi delle colonne nel CSV preprocessato
COLONNA_TESTO_PROCESSATO = "testo_lemmatizzato"
COLONNA_LINGUA = "lingua_rilevata"
COLONNA_ID_ORIGINALE = "id_originale"
COLONNA_FONTE = "fonte"
COLONNA_DATA_ORIGINALE = "data_originale_str"

# --- CARICAMENTO MODELLI SPACY ---
nlp_en = None
nlp_it = None
try:
    nlp_en = spacy.load('en_core_web_sm')
    print("Modello spaCy per l'inglese (en_core_web_sm) caricato.")
except OSError:
    print("ERRORE: Modello spaCy 'en_core_web_sm' non trovato. Scaricarlo con: python -m spacy download en_core_web_sm")

try:
    nlp_it = spacy.load('it_core_news_sm')
    print("Modello spaCy per l'italiano (it_core_news_sm) caricato.")
except OSError:
    print("ERRORE: Modello spaCy 'it_core_news_sm' non trovato. Scaricarlo con: python -m spacy download it_core_news_sm")

# --- FUNZIONI ---

def prepara_corpus_per_lda(documenti_testuali):
    """
    Prepara i dati per Gensim LDA: tokenizza, crea dizionario e corpus BoW.
    documenti_testuali: una lista di stringhe (documenti già lemmatizzati, token separati da spazi).
    """
    if not documenti_testuali:
        print("Nessun documento testuale fornito per la preparazione del corpus.")
        return None, None, None

    print("  Tokenizzazione dei documenti (split by space)...")
    tokenized_docs = [doc.split() for doc in documenti_testuali if isinstance(doc, str) and doc.strip()]
    
    if not tokenized_docs:
        print("  Nessun documento valido dopo la tokenizzazione preliminare.")
        return None, None, None

    print("  Creazione del dizionario Gensim...")
    dictionary = corpora.Dictionary(tokenized_docs)
    print(f"    Dizionario creato con {len(dictionary)} token unici.")

    print("  Creazione del corpus Bag-of-Words...")
    corpus_bow = [dictionary.doc2bow(doc) for doc in tokenized_docs]
    print(f"    Corpus BoW creato per {len(corpus_bow)} documenti.")
    
    return tokenized_docs, dictionary, corpus_bow

# --- FLUSSO PRINCIPALE DELLO SCRIPT ---
if __name__ == "__main__":
    if not nlp_en and not nlp_it:
        print("\nERRORE CRITICO: Nessun modello spaCy è stato caricato. Impossibile procedere.")
        exit()

    print(f"Caricamento dati preprocessati da: {TOPIC_MODELING_INPUT_CSV}")
    try:
        df_processed = pd.read_csv(TOPIC_MODELING_INPUT_CSV, low_memory=False)
        print(f"Caricate {len(df_processed)} righe di dati preprocessati.")
    except FileNotFoundError:
        print(f"ERRORE: File '{TOPIC_MODELING_INPUT_CSV}' non trovato.")
        exit()
    except Exception as e:
        print(f"ERRORE durante la lettura del CSV preprocessato: {e}")
        exit()

    if COLONNA_TESTO_PROCESSATO not in df_processed.columns:
        print(f"ERRORE: La colonna testo '{COLONNA_TESTO_PROCESSATO}' non è presente nel CSV.")
        exit()
    df_processed.dropna(subset=[COLONNA_TESTO_PROCESSATO], inplace=True)
    df_processed = df_processed[df_processed[COLONNA_TESTO_PROCESSATO].str.strip() != '']
    print(f"Numero di righe dopo rimozione testi vuoti: {len(df_processed)}")

    # --- TOPIC MODELING PER TESTI IN INGLESE ---
    if nlp_en:
        print("\n--- Inizio Topic Modeling per testi in INGLESE ---")
        df_en = df_processed[df_processed[COLONNA_LINGUA] == 'en'].copy()
        
        if df_en.empty:
            print("Nessun documento in inglese trovato per il Topic Modeling.")
        else:
            print(f"Trovati {len(df_en)} documenti in inglese.")
            documenti_en = df_en[COLONNA_TESTO_PROCESSATO].tolist()
            
            tokenized_docs_en, dictionary_en, corpus_bow_en = prepara_corpus_per_lda(documenti_en)

            if tokenized_docs_en and dictionary_en and corpus_bow_en:
                print(f"\nAddestramento modello LDA per l'inglese con {LDA_NUM_TOPICS_EN} topic...")
                try:
                    lda_model_en = LdaMulticore(
                        corpus=corpus_bow_en,
                        id2word=dictionary_en,
                        num_topics=LDA_NUM_TOPICS_EN,
                        passes=LDA_NUM_PASSES_EN,
                        workers=LDA_WORKERS_EN,
                        random_state=100,
                        chunksize=100,
                        alpha='symmetric',
                        eta=None
                    )
                    print("Modello LDA per l'inglese addestrato.")

                    print("\nTopic identificati per l'inglese (top words per topic):")
                    topics_en = lda_model_en.print_topics(num_words=10)
                    with open(LDA_TOPICS_EN_TXT, 'w', encoding='utf-8') as f_out_en:
                        for i, topic in enumerate(topics_en):
                            print(f"Topic EN #{i}: {topic[1]}")
                            f_out_en.write(f"Topic EN #{i}: {topic[1]}\n")
                    print(f"I topic per l'inglese sono stati salvati in '{LDA_TOPICS_EN_TXT}'")

                    print("\nAssegnazione topic dominanti ai documenti inglesi...")
                    doc_topics_distr_en = [lda_model_en.get_document_topics(bow, minimum_probability=0.0) for bow in corpus_bow_en]
                    dominant_topics_en = []
                    for doc_distr in doc_topics_distr_en:
                        dominant_topics_en.append(sorted(doc_distr, key=lambda x: x[1], reverse=True)[0][0] if doc_distr else None)
                    
                    if len(dominant_topics_en) == len(df_en):
                        df_en['topic_dominante_lda_en'] = dominant_topics_en
                        df_en_output = df_en[[COLONNA_ID_ORIGINALE, COLONNA_FONTE, COLONNA_DATA_ORIGINALE, COLONNA_TESTO_PROCESSATO, 'topic_dominante_lda_en']]
                        df_en_output.to_csv(DOCUMENT_TOPICS_EN_CSV, index=False, encoding='utf-8')
                        print(f"I topic dominanti per i documenti inglesi salvati in '{DOCUMENT_TOPICS_EN_CSV}'")
                    else:
                         print(f"ERRORE: discordanza nel numero di topic dominanti EN ({len(dominant_topics_en)}) e documenti EN ({len(df_en)}).")

                except Exception as e_lda_en:
                    print(f"ERRORE durante il modello LDA per l'inglese: {e_lda_en}")
            else:
                print("Preparazione corpus fallita per i testi in inglese.")
    else:
        print("Modello spaCy per l'inglese non caricato, salto il Topic Modeling per l'inglese.")


    # --- TOPIC MODELING PER TESTI IN ITALIANO ---
    if nlp_it:
        print("\n\n--- Inizio Topic Modeling per testi in ITALIANO ---")
        df_it = df_processed[df_processed[COLONNA_LINGUA] == 'it'].copy()
        
        if df_it.empty:
            print("Nessun documento in italiano trovato per il Topic Modeling.")
        else:
            print(f"Trovati {len(df_it)} documenti in italiano.")
            documenti_it = df_it[COLONNA_TESTO_PROCESSATO].tolist()
            
            tokenized_docs_it, dictionary_it, corpus_bow_it = prepara_corpus_per_lda(documenti_it)

            if tokenized_docs_it and dictionary_it and corpus_bow_it:
                print(f"\nAddestramento modello LDA per l'italiano con {LDA_NUM_TOPICS_IT} topic...")
                try:
                    lda_model_it = LdaMulticore(
                        corpus=corpus_bow_it,
                        id2word=dictionary_it,
                        num_topics=LDA_NUM_TOPICS_IT,
                        passes=LDA_NUM_PASSES_IT,
                        workers=LDA_WORKERS_IT,
                        random_state=100,
                        chunksize=100,
                        alpha='symmetric',
                        eta=None
                    )
                    print("Modello LDA per l'italiano addestrato.")

                    print("\nTopic identificati per l'italiano (top words per topic):")
                    topics_it = lda_model_it.print_topics(num_words=10)
                    with open(LDA_TOPICS_IT_TXT, 'w', encoding='utf-8') as f_out_it:
                        for i, topic in enumerate(topics_it):
                            print(f"Topic IT #{i}: {topic[1]}")
                            f_out_it.write(f"Topic IT #{i}: {topic[1]}\n")
                    print(f"I topic per l'italiano sono stati salvati in '{LDA_TOPICS_IT_TXT}'")

                    print("\nAssegnazione topic dominanti ai documenti italiani...")
                    doc_topics_distr_it = [lda_model_it.get_document_topics(bow, minimum_probability=0.0) for bow in corpus_bow_it]
                    dominant_topics_it = []
                    for doc_distr in doc_topics_distr_it:
                        dominant_topics_it.append(sorted(doc_distr, key=lambda x: x[1], reverse=True)[0][0] if doc_distr else None)
                    
                    if len(dominant_topics_it) == len(df_it):
                        df_it['topic_dominante_lda_it'] = dominant_topics_it
                        df_it_output = df_it[[COLONNA_ID_ORIGINALE, COLONNA_FONTE, COLONNA_DATA_ORIGINALE, COLONNA_TESTO_PROCESSATO, 'topic_dominante_lda_it']]
                        df_it_output.to_csv(DOCUMENT_TOPICS_IT_CSV, index=False, encoding='utf-8')
                        print(f"I topic dominanti per i documenti italiani salvati in '{DOCUMENT_TOPICS_IT_CSV}'")
                    else:
                        print(f"ERRORE: discordanza nel numero di topic dominanti IT ({len(dominant_topics_it)}) e documenti IT ({len(df_it)}).")


                except Exception as e_lda_it:
                    print(f"ERRORE durante il modello LDA per l'italiano: {e_lda_it}")
            else:
                print("Preparazione corpus fallita per i testi in italiano.")
    else:
        print("Modello spaCy per l'italiano non caricato, salto il Topic Modeling per l'italiano.")

    print("\nScript di Topic Modeling terminato.")