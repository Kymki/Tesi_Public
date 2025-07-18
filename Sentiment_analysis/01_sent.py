import pandas as pd
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch
import time

# Importa le configurazioni dal file config.py
from config import (
    SENTIMENT_ANALYSIS_INPUT_CSV,
    SENTIMENT_FINAL_CSV,
    SENTIMENT_MODEL_NAME
)

# --- CONFIGURAZIONE SPECIFICA (mantenuta qui o spostata se utile altrove) ---
# Nomi delle colonne nel CSV
COLONNA_TESTO_PER_SENTIMENT = "testo_pulito_base" 
COLONNA_LINGUA = "lingua_rilevata"
# Ora il nome del modello è importato da config.py
MODEL_NAME = SENTIMENT_MODEL_NAME

MAX_ROWS_TO_PROCESS = None # Impostare un numero (es. 200) per testare, o a 0 (None) per processare tutto.

# --- CARICAMENTO MODELLO E TOKENIZER (con selezione dispositivo corretta) ---
print(f"Caricamento del modello e tokenizer: {MODEL_NAME}...")
tokenizer = None
model = None
label_mapping = {}
label_mapping_reverse = {}
device = None

try:
    if torch.cuda.is_available():
        device = torch.device("cuda")
        print("Trovata GPU NVIDIA (CUDA). Verrà utilizzata questa.")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
        print("Trovata GPU Apple (MPS). Verrà utilizzata questa.")
    else:
        device = torch.device("cpu")
        print("Nessuna GPU compatibile trovata. Verrà utilizzata la CPU (più lento).")
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    
    model.to(device)
    model.eval()

    print(f"Modello spostato su dispositivo: {device}")
    
    label_mapping = model.config.id2label
    label_mapping_reverse = {v.lower(): k for k, v in label_mapping.items()}
    print(f"Mapping delle etichette del modello: {label_mapping}")

except Exception as e:
    print(f"ERRORE GRAVE durante il caricamento del modello: {e}")

# --- FUNZIONE DI ANALISI SENTIMENT (con troncamento e gestione dispositivo) ---
def analizza_sentiment_testo_esplicito(text, tokenizer, model, device, label_map, label_map_reverse):
    """
    Analizza il sentiment usando tokenizzazione esplicita con troncamento.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return "nessun_testo", None, None, None

    try:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
        
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            logits = model(**inputs).logits

        scores = torch.nn.functional.softmax(logits, dim=1)[0]
        
        predicted_class_id = torch.argmax(scores).item()
        sentiment_label = label_map.get(predicted_class_id, "sconosciuto")

        score_negative = scores[label_map_reverse.get('negative', 0)].item()
        score_neutral = scores[label_map_reverse.get('neutral', 1)].item()
        score_positive = scores[label_map_reverse.get('positive', 2)].item()

        return sentiment_label, score_positive, score_negative, score_neutral
            
    except Exception as e:
        print(f"    ERRORE durante l'analisi del sentiment per il testo: '{text[:70]}...'. Errore: {e.__class__.__name__} - {e}")
        return "errore_generico_analisi", None, None, None

# --- FLUSSO PRINCIPALE DELLO SCRIPT ---
if __name__ == "__main__":
    if not tokenizer or not model:
        print("Tokenizer o modello non caricati correttamente. Uscita dallo script.")
        exit()

    print(f"\nCaricamento dati da: {SENTIMENT_ANALYSIS_INPUT_CSV}")
    try:
        df = pd.read_csv(SENTIMENT_ANALYSIS_INPUT_CSV, low_memory=False)
        if MAX_ROWS_TO_PROCESS:
            print(f"Processo limitato alle prime {MAX_ROWS_TO_PROCESS} righe per test.")
            df = df.head(MAX_ROWS_TO_PROCESS)
        print(f"Caricate {len(df)} righe per l'analisi del sentiment.")
    except FileNotFoundError:
        print(f"ERRORE: File '{SENTIMENT_ANALYSIS_INPUT_CSV}' non trovato.")
        exit()

    df.dropna(subset=[COLONNA_TESTO_PER_SENTIMENT], inplace=True)

    results = []
    processed_count = 0
    start_time = time.time()
    print(f"\nInizio analisi del sentiment sulla colonna '{COLONNA_TESTO_PER_SENTIMENT}'...")
    
    for index, riga in df.iterrows():
        testo = riga.get(COLONNA_TESTO_PER_SENTIMENT)
        
        if riga.get(COLONNA_LINGUA) in ['en', 'it'] and isinstance(testo, str) and testo.strip():
            label, score_p, score_n, score_u = analizza_sentiment_testo_esplicito(testo, tokenizer, model, device, label_mapping, label_mapping_reverse)
        else:
            label, score_p, score_n, score_u = "testo_mancante_o_lingua_non_analizzata", None, None, None
            
        results.append({
            'sentiment_label': label,
            'sentiment_score_positive': score_p,
            'sentiment_score_negative': score_n,
            'sentiment_score_neutral': score_u
        })
        
        processed_count += 1
        if processed_count % 100 == 0:
            elapsed_time = time.time() - start_time
            print(f"  Analizzati {processed_count}/{len(df)} documenti... (Tempo trascorso: {elapsed_time:.2f} secondi)")

    results_df = pd.DataFrame(results, index=df.index)
    df_final = pd.concat([df, results_df], axis=1)

    print(f"\nAnalisi del sentiment completata per {processed_count} documenti.")
    
    try:
        df_final.to_csv(SENTIMENT_FINAL_CSV, index=False, encoding='utf-8')
        print(f"Dati con sentiment salvati in '{SENTIMENT_FINAL_CSV}'")
    except IOError as e:
        print(f"Errore durante il salvataggio del file CSV con sentiment: {e}")