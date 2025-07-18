import spacy
import re
from langdetect import detect, LangDetectException
import pandas as pd
import datetime

# Importa le configurazioni dal file config.py
# Assicurati che config.py sia accessibile da questo script (stessa directory o un percorso noto)
from config import (
    PROCESSED_CONSOLIDATED_CSV, # Il file di output consolidato
    KYIV_INDEPENDENT_ARTICLES_EXTRACTED_CSV, # Input per Kyiv Independent
    BBC_NEWS_ARTICLES_EXTRACTED_CSV, # Input per BBC News
    REDDIT_COMMENTS_COLLECTED_CSV, # Input per Reddit
    TELEGRAM_MESSAGES_COLLECTED_CSV # Input per Telegram
)


# --- LISTA DI STOPWORDS PERSONALIZZATE PER L'ITALIANO ---
# Mantiene questa sezione qui se le stopwords sono specifiche di questo script
CUSTOM_STOPWORDS_IT = {
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una",
    "di", "a", "da", "in", "con", "su", "per", "tra", "fra",
    "e", "o", "ma", "se", "che", "non", "si", "ciò", "cui", "né",
    "mi", "ti", "ci", "vi", "ne", "ed", "ad",
    "del", "al", "dal", "nel", "col", "sul", "dello", "allo", "dallo", "nello", "nella", "sullo", "sulla",
    "dei", "ai", "dai", "nei", "coi", "sui", "degli", "agli", "dagli", "negli", "sugli",
    "della", "alla", "dalla", "nella", "colla", "sulla", "delle", "alle", "dalle", "nelle", "colle", "sulle",
    "essere", "avere", "fare", "dire", "potere", "volere", "dovere", "andare", "venire", "sapere", "vedere", # Verbi comuni
    "questo", "quello", "codesto", "tale", "quale", "stesso", "medesimo",
    "io", "tu", "lui", "lei", "noi", "voi", "loro", "egli", "ella", "essi", "esse",
    "mio", "tuo", "suo", "nostro", "vostro", "loro", # Aggettivi e pronomi possessivi
    "ancora", "sempre", "anche", "pure", "allora", "quindi", "infatti", "però", "tuttavia", "mentre", "quando",
    "molto", "poco", "tanto", "troppo", "più", "meno", "ogni", "alcuni", "nessuno",
    "cosa", "fatto", "esempio", "caso", "parte", "punto", "modo", "tempo", "giorno", "anno", "uomo", "donna",
    "ah", "oh", "eh", "mah", "boh", # Interiezioni comuni
    "essere" # Lemma di 'è', 'sono', 'sarà', ecc.
}

# --- CARICAMENTO MODELLI SPACY ---
nlp_en = None
nlp_it = None
print("Caricamento modelli spaCy...")
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
print("-" * 30)

# --- FUNZIONI DI PULIZIA BASE ---
def remove_urls(text):
    """Rimuove gli URL dal testo."""
    return re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)

def remove_social_media_tags(text):
    """Rimuove mentions (@utente) e hashtags (#topic)."""
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'#\w+', '', text)
    return text

def remove_special_chars_and_digits(text, keep_basic_accented=True):
    """
    Rimuove caratteri speciali e numeri.
    Se keep_basic_accented è True, cerca di mantenere lettere accentate comuni italiane/europee.
    """
    text = re.sub(r'\d+', '', text) # Rimuove numeri
    if keep_basic_accented:
        # Mantiene lettere a-z, A-Z, e caratteri accentati comuni, più spazi
        text = re.sub(r'[^a-zA-ZàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞß\s]', '', text, flags=re.IGNORECASE)
    else:
        text = re.sub(r'[^a-zA-Z\s]', '', text, flags=re.IGNORECASE) # Solo lettere inglesi base e spazi
    text = re.sub(r'\s+', ' ', text).strip() # Normalizza spazi multipli
    return text

# --- FUNZIONE DI RILEVAMENTO LINGUA ---
def detect_language(text_to_detect):
    """Rileva la lingua del testo. Restituisce il codice lingua (es. 'en', 'it') o None."""
    if not text_to_detect or not isinstance(text_to_detect, str):
        return None

    text_cleaned_for_detection = remove_urls(text_to_detect)
    text_cleaned_for_detection = remove_social_media_tags(text_cleaned_for_detection)
    text_cleaned_for_detection = re.sub(r'\d+', '', text_cleaned_for_detection) # Rimuove anche i numeri
    
    text_cleaned_for_detection = text_cleaned_for_detection.strip()

    if len(text_cleaned_for_detection) < 15:
        return None
    try:
        lang = detect(text_cleaned_for_detection)
        return lang
    except LangDetectException:
        return "lingua_non_rilevata"
    except Exception as e:
        print(f"    Errore generico durante il rilevamento lingua: {e} per testo: '{text_cleaned_for_detection[:50]}...'")
        return "errore_rilevamento"

# --- FUNZIONE DI PREPROCESSING PRINCIPALE (AGGIORNATA CON CUSTOM STOPWORDS) ---
def preprocess_full_text(raw_text, language_code):
    """
    Applica il pipeline completo di preprocessing a un singolo testo.
    raw_text: il testo originale.
    language_code: 'en' per inglese, 'it' per italiano.
    """
    if not raw_text or not isinstance(raw_text, str) or not raw_text.strip():
        return "", ""

    text_cleaned_base = remove_urls(str(raw_text))
    text_cleaned_base = remove_social_media_tags(text_cleaned_base)
    text_for_spacy = text_cleaned_base.lower()

    text_originale_pulito_base_val = remove_special_chars_and_digits(text_for_spacy, keep_basic_accented=True)
    
    nlp_model = None
    current_custom_stopwords = set()

    if language_code == 'en' and nlp_en:
        nlp_model = nlp_en
    elif language_code == 'it' and nlp_it:
        nlp_model = nlp_it
        current_custom_stopwords = CUSTOM_STOPWORDS_IT
    
    if not nlp_model:
        return text_originale_pulito_base_val, text_originale_pulito_base_val

    doc = nlp_model(text_for_spacy)
    
    lemmatized_tokens = []
    for token in doc:
        is_custom_stop = token.lemma_ in current_custom_stopwords or token.lower_ in current_custom_stopwords
        
        if not token.is_stop and \
           not is_custom_stop and \
           not token.is_punct and \
           not token.is_space and \
           len(token.lemma_) > 1 and token.is_alpha:
            lemmatized_tokens.append(token.lemma_)            
    return text_originale_pulito_base_val, " ".join(lemmatized_tokens)

# --- FLUSSO PRINCIPALE DI ELABORAZIONE ---
if __name__ == "__main__":
    if not nlp_en and not nlp_it:
        print("\nERRORE CRITICO: Nessun modello spaCy è stato caricato correttamente. Impossibile procedere con il preprocessing NLP.")
        print("Assicurarsi di aver scaricato 'en_core_web_sm' e 'it_core_news_sm'.")
        exit()
    elif not nlp_en:
        print("\nAVVISO: Modello spaCy per l'inglese non caricato. I testi in inglese avranno solo pulizia base.")
    elif not nlp_it:
        print("\nAVVISO: Modello spaCy per l'italiano non caricato. I testi in italiano avranno solo pulizia base.")

    # Definiamo le informazioni per ciascun file di input usando i percorsi da config.py
    files_da_processare = [
        {
            "percorso_file": BBC_NEWS_ARTICLES_EXTRACTED_CSV, #
            "colonne_testo": ["titolo", "testo_articolo"],
            "colonna_id": "url",
            "colonna_data": "data_pubblicazione_iso",
            "tipo_fonte": "BBC_News"
        },
        {
            "percorso_file": KYIV_INDEPENDENT_ARTICLES_EXTRACTED_CSV, #
            "colonne_testo": ["titolo", "testo_articolo"],
            "colonna_id": "url",
            "colonna_data": "data_pubblicazione_iso",
            "tipo_fonte": "Kyiv_Independent"
        },
        {
            "percorso_file": REDDIT_COMMENTS_COLLECTED_CSV, # Modificato da 'reddit_posts_raccolti.csv'
            "colonne_testo": ["testo_commento"], # Modificato da 'titolo', 'testo_post'
            "colonna_id": "commento_id",
            "colonna_data": "timestamp_utc_commento",
            "tipo_fonte": "Reddit_Commento"
        },
        {
            "percorso_file": TELEGRAM_MESSAGES_COLLECTED_CSV, #
            "colonne_testo": ["text"],
            "colonna_id": "message_id",
            "colonna_data": "timestamp_utc",
            "tipo_fonte": "Telegram"
        }
    ]

    dati_processati_consolidati = []
    documenti_processati_tot = 0
    documenti_saltati_lingua = 0
    documenti_saltati_testo_mancante = 0

    for file_info in files_da_processare:
        print(f"\n--- Inizio elaborazione file: {file_info['percorso_file']} ---")
        try:
            df = pd.read_csv(file_info['percorso_file'], low_memory=False)
            print(f"  Caricate {len(df)} righe da {file_info['percorso_file']}.")
            
            colonne_testo_effettive = [col for col in file_info['colonne_testo'] if col in df.columns]
            if not colonne_testo_effettive:
                print(f"    ERRORE: Nessuna delle colonne testo specificate ({file_info['colonne_testo']}) trovata in {file_info['percorso_file']}. Salto il file.")
                continue
            if file_info['colonna_id'] not in df.columns:
                print(f"    ERRORE: Colonna ID '{file_info['colonna_id']}' non trovata in {file_info['percorso_file']}. Salto il file.")
                continue
            if file_info['colonna_data'] not in df.columns:
                print(f"    ERRORE: Colonna Data '{file_info['colonna_data']}' non trovata in {file_info['percorso_file']}. Salto il file.")
                continue

            for index, riga in df.iterrows():
                documenti_processati_tot += 1
                if documenti_processati_tot % 500 == 0:
                    print(f"  Processati {documenti_processati_tot} documenti totali...")

                testo_originale_completo = ""
                for col_testo in colonne_testo_effettive:
                    testo_parziale = riga.get(col_testo)
                    if pd.notna(testo_parziale) and isinstance(testo_parziale, str):
                        testo_originale_completo += testo_parziale + " "
                testo_originale_completo = testo_originale_completo.strip()

                if not testo_originale_completo:
                    documenti_saltati_testo_mancante +=1
                    continue
                        
                id_originale = riga.get(file_info['colonna_id'])
                data_originale_val = riga.get(file_info['colonna_data'])
                
                data_originale_str = str(data_originale_val)
                if isinstance(data_originale_val, (int, float)):
                    try:
                        dt_obj = datetime.datetime.fromtimestamp(data_originale_val, tz=datetime.timezone.utc)
                        data_originale_str = dt_obj.isoformat()
                    except ValueError: 
                        data_originale_str = f"timestamp_invalido_{data_originale_val}"
                elif isinstance(data_originale_val, str):
                    pass


                lingua_rilevata = detect_language(testo_originale_completo)
                testo_originale_pulito_base_out = ""
                testo_processato_lemmatizzato_out = ""

                if lingua_rilevata in ['en', 'it']:
                    testo_originale_pulito_base_out, testo_processato_lemmatizzato_out = preprocess_full_text(testo_originale_completo, lingua_rilevata)
                elif lingua_rilevata:
                    documenti_saltati_lingua += 1
                    testo_originale_pulito_base_out, _ = preprocess_full_text(testo_originale_completo, "lingua_sconosciuta")
                    testo_processato_lemmatizzato_out = ""
                else:
                    documenti_saltati_lingua += 1
                    testo_originale_pulito_base_out, _ = preprocess_full_text(testo_originale_completo, "lingua_sconosciuta")
                    testo_processato_lemmatizzato_out = ""

                dati_processati_consolidati.append({
                    'id_originale': id_originale,
                    'fonte': file_info['tipo_fonte'],
                    'data_originale_str': data_originale_str,
                    'lingua_rilevata': lingua_rilevata if lingua_rilevata else 'non_rilevata',
                    'testo_pulito_base': testo_originale_pulito_base_out,
                    'testo_lemmatizzato': testo_processato_lemmatizzato_out
                })

            print(f"  Completata elaborazione di {file_info['percorso_file']}. Documenti aggiunti: {len(df) - documenti_saltati_testo_mancante - (documenti_saltati_lingua if file_info['percorso_file'] == files_da_processare[-1]['percorso_file'] else 0)}")

        except FileNotFoundError:
            print(f"    ERRORE: File {file_info['percorso_file']} non trovato. Sarà saltato.")
        except pd.errors.EmptyDataError:
            print(f"    AVVISO: File {file_info['percorso_file']} è vuoto. Sarà saltato.")
        except Exception as e:
            print(f"    ERRORE GRAVE durante l'elaborazione del file {file_info['percorso_file']}: {e}")

    if dati_processati_consolidati:
        df_consolidato = pd.DataFrame(dati_processati_consolidati)
        df_consolidato.to_csv(PROCESSED_CONSOLIDATED_CSV, index=False, encoding='utf-8')
        print(f"\n--- Preprocessing completato ---")
        print(f"Processati {documenti_processati_tot} documenti totali.")
        print(f"Documenti con testo mancante/non valido saltati: {documenti_saltati_testo_mancante}")
        print(f"Documenti in lingue non target (o non rilevate) con solo pulizia base: {documenti_saltati_lingua}")
        print(f"Totale documenti salvati nel file consolidato: {len(df_consolidato)}")
        print(f"I dati sono stati salvati in '{PROCESSED_CONSOLIDATED_CSV}'.")
        print(f"Colonne output: {df_consolidato.columns.tolist()}")
    else:
        print("\nNessun dato è stato processato o aggiunto al file consolidato.")