import csv
import re
from collections import Counter

# Importa le configurazioni dal file config.py
from config import REDDIT_POSTS_COLLECTED_CSV

# --- CONFIGURAZIONE SPECIFICA (mantenuta qui o spostata se utile altrove) ---
# Questo è l'elenco di termini di cui vogliamo verificare la presenza e l'impatto
KEYWORDS_ANALISI = ["ukraine", "russia", "zelensky", "putin", "nato"]
# Quanti post di esempio mostrare per ogni parola chiave per l'analisi qualitativa
NUM_SAMPLE_POSTS_PER_KEYWORD = 5

# Colonne nel CSV che contengono il testo da analizzare
COLONNA_TITOLO = "titolo"
COLONNA_TESTO_POST = "testo_post"

# --- FUNZIONI ---

def carica_post_da_csv(filename):
    """Carica i post dal file CSV specificato."""
    posts = []
    try:
        with open(filename, 'r', newline='', encoding='utf-8') as file_csv:
            reader = csv.DictReader(file_csv)
            for row in reader:
                posts.append(row)
        print(f"Caricati {len(posts)} post da '{filename}'.")
    except FileNotFoundError:
        print(f"ERRORE: Il file '{filename}' non è stato trovato. Assicurati che sia nella directory corretta.")
        return None
    except Exception as e:
        print(f"ERRORE durante la lettura del file CSV: {e}")
        return None
    return posts

def analizza_frequenza_keyword(posts_data, keywords):
    """
    Analizza la frequenza di ciascuna keyword nei titoli e nei testi dei post.
    Conta il numero di post in cui appare almeno una volta ogni keyword.
    Conta anche il numero totale di occorrenze di ogni keyword.
    """
    if not posts_data:
        return None, None

    keyword_post_appearance_count = Counter()
    keyword_total_occurrence_count = Counter()

    print("\nAnalisi frequenza parole chiave...")
    for keyword in keywords:
        regex = r"\b" + re.escape(keyword) + r"\b" 
        for post in posts_data:
            testo_da_analizzare = (post.get(COLONNA_TITOLO, "") + " " + 
                                   post.get(COLONNA_TESTO_POST, "")).lower()
            
            occorrenze_nel_post = re.findall(regex, testo_da_analizzare, re.IGNORECASE)
            
            if occorrenze_nel_post:
                keyword_post_appearance_count[keyword] += 1
                keyword_total_occurrence_count[keyword] += len(occorrenze_nel_post)
        
        print(f"  Keyword '{keyword}': trovata in {keyword_post_appearance_count[keyword]} post, "
              f"con un totale di {keyword_total_occurrence_count[keyword]} occorrenze.")

    print("\n--- Riepilogo Frequenza Parole Chiave ---")
    if not keyword_post_appearance_count:
        print("Nessuna delle parole chiave specificate è stata trovata nei post analizzati.")
        return keyword_post_appearance_count, keyword_total_occurrence_count

    print("Numero di POST in cui ogni parola chiave appare (almeno una volta):")
    for keyword, count in keyword_post_appearance_count.most_common():
        print(f"  - '{keyword}': {count} post")

    print("\nNumero TOTALE di OCCORRENZE di ogni parola chiave (in tutti i post):")
    for keyword, count in keyword_total_occurrence_count.most_common():
        print(f"  - '{keyword}': {count} occorrenze")
        
    return keyword_post_appearance_count, keyword_total_occurrence_count

def mostra_post_di_esempio_per_keyword(posts_data, keywords, num_esempi=3):
    """Mostra alcuni titoli di post di esempio per ogni keyword."""
    if not posts_data:
        return

    print(f"\n--- Esempi di Titoli di Post per Parola Chiave (max {num_esempi} per keyword) ---")
    for keyword in keywords:
        regex = r"\b" + re.escape(keyword) + r"\b"
        esempi_trovati = []
        print(f"\n  Esempi per la parola chiave '{keyword}':")
        
        count = 0
        for post in posts_data:
            titolo = post.get(COLONNA_TITOLO, "")
            testo_post = post.get(COLONNA_TESTO_POST, "")
            
            if re.search(regex, titolo, re.IGNORECASE) or re.search(regex, testo_post, re.IGNORECASE):
                esempi_trovati.append(titolo)
                count += 1
                if count >= num_esempi:
                    break
        
        if esempi_trovati:
            for i, titolo_esempio in enumerate(esempi_trovati):
                print(f"    {i+1}. {titolo_esempio[:150]}...")
        else:
            print(f"    Nessun post di esempio trovato contenente '{keyword}' nel titolo o nel testo.")

# --- BLOCCO DI ESECUZIONE PRINCIPALE ---
if __name__ == "__main__":
    posts = carica_post_da_csv(REDDIT_POSTS_COLLECTED_CSV)
    
    if posts:
        frequenza_post_keyword, frequenza_totale_keyword = analizza_frequenza_keyword(posts, KEYWORDS_ANALISI)
        mostra_post_di_esempio_per_keyword(posts, KEYWORDS_ANALISI, NUM_SAMPLE_POSTS_PER_KEYWORD)

        print("\n\nAnalisi preliminare completata.")