import pandas as pd
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import math
import warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) # Disabilita i warning di sicurezza per le connessioni HTTPS non verificate

# Importa le configurazioni dal file config.py
from config import (
    ELASTICSEARCH_INDEXER_INPUT_CSV,
    ELASTICSEARCH_HOST,
    ELASTIC_USER,
    ELASTIC_PASSWORD,
    INDEX_NAME_MAIN
)

# --- CONFIGURAZIONE SPECIFICA (mantenuta qui o spostata se utile altrove) ---
# Ora queste variabili sono importate da config.py
INPUT_CSV_FILE = ELASTICSEARCH_INDEXER_INPUT_CSV
ELASTICSEARCH_HOST = ELASTICSEARCH_HOST
ELASTIC_USER = ELASTIC_USER
ELASTIC_PASSWORD = ELASTIC_PASSWORD
INDEX_NAME = INDEX_NAME_MAIN

# --- FUNZIONI (invariate) ---
def connetti_a_elasticsearch():
    """Tenta di connettersi a un'istanza Elasticsearch sicura (HTTPS)."""
    print(f"Tentativo di connessione sicura (HTTPS) a Elasticsearch su {ELASTICSEARCH_HOST}...")
    try:
        es_client = Elasticsearch(
            hosts=[ELASTICSEARCH_HOST],
            basic_auth=(ELASTIC_USER, ELASTIC_PASSWORD),
            verify_certs=False
        )
        es_client.info()
        print("Connessione a Elasticsearch riuscita!")
        return es_client
    except Exception as e:
        print(f"ERRORE DI CONNESSIONE: {e}")
        return None

def crea_indice_con_mapping(es_client, index_name):
    """Crea un indice con un mapping specifico per i dati."""
    if es_client.indices.exists(index=index_name):
        print(f"L'indice '{index_name}' esiste già. Verrà eliminato e ricreato.")
        es_client.indices.delete(index=index_name)
    mapping = {
        "properties": {
            "id_originale": {"type": "keyword"},
            "fonte": {"type": "keyword"},
            "data_originale_str": {"type": "date", "format": "date_optional_time||epoch_second"},
            "lingua_rilevata": {"type": "keyword"},
            "testo_pulito_base": {"type": "text", "analyzer": "standard"},
            "testo_lemmatizzato": {"type": "text", "analyzer": "standard"},
            "sentiment_label": {"type": "keyword"},
            "sentiment_score_positive": {"type": "float"},
            "sentiment_score_negative": {"type": "float"},
            "sentiment_score_neutral": {"type": "float"}
        }
    }
    print(f"Creazione del nuovo indice '{index_name}' con mapping...")
    es_client.indices.create(index=index_name, mappings=mapping)

def generatore_documenti_da_csv(df, index_name, id_column):
    """Funzione generatore per produrre documenti da indicizzare con 'bulk'."""
    for index, row in df.iterrows():
        doc = row.to_dict()
        doc_pulito = {key: None if pd.isna(value) or (isinstance(value, float) and math.isnan(value)) else value for key, value in doc.items()}
        yield {
            "_index": index_name,
            "_id": str(doc_pulito.get(id_column, f"doc_{index}")),
            "_source": doc_pulito,
        }

# --- BLOCCO DI ESECUZIONE PRINCIPALE (CON GESTIONE ERRORE CORRETTA) ---
if __name__ == "__main__":
    if ELASTIC_PASSWORD == "elastic": # Valore di default in config.py, va cambiato dall'utente
        print("ERRORE: Per favore, inserisci la password reale per l'utente 'elastic' nella variabile ELASTIC_PASSWORD in config.py.")
    else:
        es = connetti_a_elasticsearch()
        
        if es:
            try:
                print(f"Caricamento dati da '{INPUT_CSV_FILE}'...")
                df = pd.read_csv(INPUT_CSV_FILE)
                df.dropna(axis=1, how='all', inplace=True)
                print(f"Caricate {len(df)} righe. Colonne presenti: {df.columns.tolist()}")                
                crea_indice_con_mapping(es, INDEX_NAME)
                print("Inizio indicizzazione dei documenti in Elasticsearch...")
                
                success, errors = bulk(
                    client=es, 
                    actions=generatore_documenti_da_csv(df, INDEX_NAME, id_column='id_originale'),
                    raise_on_error=False
                )
                
                print("\n--- Risultato Indicizzazione ---")
                print(f"Documenti indicizzati con successo: {success}")
                
                if errors:
                    print(f"Errori riscontrati durante l'indicizzazione: {len(errors)}")
                    print("\nDettagli per il primo documento fallito:")
                    
                    error_info = errors[0]
                    error_details = error_info.get('index', {})
                    failed_id = error_details.get('_id')
                    error_reason = error_details.get('error', {})
                    
                    print(f"  ID Documento Fallito: {failed_id}")
                    print(f"  Causa Principale: {error_reason.get('type')}")
                    print(f"  Dettaglio Causa: {error_reason.get('reason')}")
                    
                    if failed_id:
                        try:
                            df['id_originale_str'] = df['id_originale'].astype(str)
                            failed_row = df[df['id_originale_str'] == str(failed_id)]
                            
                            if not failed_row.empty:
                                print("  Dati Originali della Riga Fallita nel CSV:")
                                print(failed_row.to_string())
                            else:
                                print(f"  Impossibile trovare la riga con id '{failed_id}' nel DataFrame.")
                        except Exception as find_e:
                            print(f"  (Impossibile recuperare la riga originale dal CSV per l'id '{failed_id}': {find_e})")
                else:
                    print("Nessun errore riscontrato.")
                
            except FileNotFoundError:
                print(f"ERRORE: Il file di input '{INPUT_CSV_FILE}' non è stato trovato.")
            except Exception as e:
                print(f"Si è verificato un errore generale non gestito: {e}")