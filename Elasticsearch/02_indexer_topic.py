import pandas as pd
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, BulkIndexError
import math
import warnings
import urllib3

# Sopprime i warning di sicurezza per connessioni HTTPS non verificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Importa le configurazioni dal file config.py
from config import (
    ELASTICSEARCH_INDEXER_TOPICS_EN_CSV,
    ELASTICSEARCH_INDEXER_TOPICS_IT_CSV,
    ELASTICSEARCH_HOST,
    ELASTIC_USER,
    ELASTIC_PASSWORD,
    INDEX_NAME_TOPIC
)

# --- CONFIGURAZIONE SPECIFICA (mantenuta qui o spostata se utile altrove) ---
# Ora queste variabili sono importate da config.py
INPUT_TOPICS_EN_CSV = ELASTICSEARCH_INDEXER_TOPICS_EN_CSV
INPUT_TOPICS_IT_CSV = ELASTICSEARCH_INDEXER_TOPICS_IT_CSV

ELASTICSEARCH_HOST = ELASTICSEARCH_HOST
ELASTIC_USER = ELASTIC_USER
ELASTIC_PASSWORD = ELASTIC_PASSWORD
INDEX_NAME = INDEX_NAME_TOPIC # Nome del NUOVO indice dedicato ai topic

TOPIC_LABELS_EN = {
    0: "Conflitto Geopolitico e Minaccia Nucleare",
    1: "Meta-Discussione su Informazione e Fonti Online",
    2: "Resoconti di Attacchi su Città e Civili",
    3: "Leader e Incontri Diplomatici (Trump, Putin, Zelensky)",
    4: "Economia del Conflitto e Ruolo della Cina",
    5: "Supporto Internazionale e Sicurezza dell'Ucraina",
    6: "Critica Politica Emotiva (Ungheria/Orbán)",
    7: "Operazioni Militari e Controllo del Territorio",
    8: "Narrazioni Storiche e Propaganda (Nazismo)",
    9: "Risposta e Difesa Europea (EU/NATO)",
    10: "Opinione Pubblica Social (Chatter Generale)",
    11: "Jargon di Guerra e Linguaggio Social ('Operazione Speciale')",
    12: "Politica Interna USA e Ripercussioni (Afghanistan)",
    13: "Sanzioni, Energia e Negoziati di Pace",
    14: "Intelligence, Tecnologia e Ruolo di Elon Musk"
}

TOPIC_LABELS_IT = {
    0: "Narrazione dell'Operazione Militare e Rischi",
    1: "Guerra Aerea e Sistemi di Difesa",
    2: "Impatto del Conflitto sui Civili",
    3: "Quadro Politico-Diplomatico (Sanzioni Europee)",
    4: "Attacchi a Infrastrutture e Siti Nucleari (Chernobyl)",
    5: "Coinvolgimento Leader Europei (Draghi/Macron)",
    6: "Discorso Politico Generale sul Conflitto (1)",
    7: "Comunicazioni Ufficiali Russe (Cremlino/Peskov)",
    8: "Discorso Politico Generale sul Conflitto (2)",
    9: "Assedio di Mariupol e Corridoi Umanitari",
    10: "Prospettiva Politica Italiana e Scenario Globale (Gaza)",
    11: "Adesione NATO (Svezia) e Ruolo UK",
    12: "Sanzioni, Neutralità e Media Internazionali",
    13: "Discorso Politico-Militare Generale (Attacchi)",
    14: "Referendum e Fornitura di Caccia (Svezia)"
}

# --- FUNZIONI (Simili allo script precedente) ---
def connetti_a_elasticsearch():
    """Tenta di connettersi a un'istanza Elasticsearch sicura (HTTPS)."""
    print(f"Tentativo di connessione sicura (HTTPS) a Elasticsearch su {ELASTICSEARCH_HOST}...")
    try:
        es_client = Elasticsearch(
            hosts=[ELASTICSEARCH_HOST], basic_auth=(ELASTIC_USER, ELASTIC_PASSWORD), verify_certs=False
        )
        es_client.info()
        print("Connessione a Elasticsearch riuscita!")
        return es_client
    except Exception as e:
        print(f"ERRORE DI CONNESSIONE: {e}")
        return None

def crea_indice_topic_con_mapping(es_client, index_name):
    """Crea un indice con un mapping specifico per i dati dei topic."""
    if es_client.indices.exists(index=index_name):
        print(f"L'indice '{index_name}' esiste già. Verrà eliminato e ricreato.")
        es_client.indices.delete(index=index_name)
    mapping = {
        "properties": {
            "id_originale": {"type": "keyword"},
            "fonte": {"type": "keyword"},
            "data_originale_str": {"type": "date", "format": "date_optional_time||epoch_second"},
            "lingua": {"type": "keyword"},
            "testo_processato": {"type": "text", "analyzer": "standard"},
            "topic_id": {"type": "integer"},
            "topic_label": {"type": "keyword"}
        }
    }
    print(f"Creazione del nuovo indice '{index_name}' con mapping...")
    es_client.indices.create(index=index_name, mappings=mapping)

def generatore_documenti_da_df(df, index_name, id_column):
    """Funzione generatore per produrre documenti da indicizzare."""
    for index, row in df.iterrows():
        doc = row.to_dict()
        doc_pulito = {key: None if pd.isna(value) else value for key, value in doc.items()}
        yield {
            "_index": index_name,
            "_id": str(doc_pulito.get(id_column, f"topic_doc_{index}")),
            "_source": doc_pulito,
        }

# --- BLOCCO DI ESECUZIONE PRINCIPALE ---
if __name__ == "__main__":
    if ELASTIC_PASSWORD == "elastic": # Valore di default in config.py, va cambiato dall'utente
        print("ERRORE: Per favore, inserisci la password reale per l'utente 'elastic' nella variabile ELASTIC_PASSWORD in config.py.")
    else:
        try:
            print(f"Caricamento dati topic inglesi da '{INPUT_TOPICS_EN_CSV}'...")
            df_en = pd.read_csv(INPUT_TOPICS_EN_CSV)
            df_en.rename(columns={'topic_dominante_lda_en': 'topic_id'}, inplace=True)
            df_en['topic_label'] = df_en['topic_id'].map(TOPIC_LABELS_EN)
            df_en['lingua'] = 'en'
            
            print(f"Caricamento dati topic italiani da '{INPUT_TOPICS_IT_CSV}'...")
            df_it = pd.read_csv(INPUT_TOPICS_IT_CSV)
            df_it.rename(columns={'topic_dominante_lda_it': 'topic_id'}, inplace=True)
            df_it['topic_label'] = df_it['topic_id'].map(TOPIC_LABELS_IT)
            df_it['lingua'] = 'it'

            print("Unione dei dataset inglese e italiano...")
            df_combined = pd.concat([df_en, df_it], ignore_index=True)
            df_combined.rename(columns={'testo_lemmatizzato': 'testo_processato'}, inplace=True, errors='ignore') # Ensure column name consistency
            print(f"Dataset finale per l'indicizzazione creato con {len(df_combined)} documenti.")
            print(f"Colonne disponibili: {df_combined.columns.tolist()}")

            es = connetti_a_elasticsearch()
            if es:
                crea_indice_topic_con_mapping(es, INDEX_NAME)
                
                print(f"Inizio indicizzazione dei dati dei topic nell'indice '{INDEX_NAME}'...")
                success, errors = bulk(
                    client=es,
                    actions=generatore_documenti_da_df(df_combined, INDEX_NAME, id_column='id_originale')
                )
                
                print("\n--- Risultato Indicizzazione Topic ---")
                print(f"Documenti indicizzati con successo: {success}")
                if errors:
                    print(f"Errori riscontrati: {len(errors)}")
                    print(f"Primo errore: {errors[0]}")
                else:
                    print("Nessun errore riscontrato.")
                
        except FileNotFoundError as e:
            print(f"ERRORE: File non trovato: {e.filename}. Assicurati che i file CSV dei topic siano nella directory corretta.")
        except Exception as e:
            print(f"Si è verificato un errore generale: {e}")