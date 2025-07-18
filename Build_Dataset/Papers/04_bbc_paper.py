import csv
from newspaper import Article, Config
import datetime
import time

# Importa le configurazioni dal file config.py
from config import (
    BBC_NEWS_ARCHIVE_URLS_CSV,
    BBC_NEWS_ARTICLES_EXTRACTED_CSV,
    GLOBAL_START_DATE,
    SCRAPING_DELAY_BETWEEN_REQUESTS
)


# --- CONFIGURAZIONE SPECIFICA (mantenuta qui o spostata se utile altrove) ---
NOME_SITO = "BBC_News"

# Ora queste variabili sono importate da config.py
INPUT_URL_CSV_FILE = BBC_NEWS_ARCHIVE_URLS_CSV
OUTPUT_ARTICLES_CSV_FILE = BBC_NEWS_ARTICLES_EXTRACTED_CSV

# Converte la data di inizio da tupla a oggetto datetime
START_DATE_LIMIT = datetime.datetime(*GLOBAL_START_DATE, tzinfo=datetime.timezone.utc)

# Configurazione per newspaper3k
config = Config()
config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
config.request_timeout = 20
config.memoize_articles = True

DELAY_PER_ARTICLE = SCRAPING_DELAY_BETWEEN_REQUESTS

# --- FUNZIONI ---

def carica_url_da_csv(filename, url_column, date_column=None):
    """Carica gli URL e opzionalmente le date dal file CSV specificato."""
    urls_data = []
    try:
        with open(filename, 'r', newline='', encoding='utf-8') as file_csv:
            reader = csv.DictReader(file_csv)
            if url_column not in reader.fieldnames:
                print(f"ERRORE: La colonna URL '{url_column}' non è stata trovata nel file '{filename}'. Colonne disponibili: {reader.fieldnames}")
                return None
            if date_column and date_column not in reader.fieldnames:
                print(f"AVVISO: La colonna data '{date_column}' non è stata trovata. Si procederà senza date pre-filtrate.")
                date_column = None

            for row in reader:
                url = row.get(url_column)
                date_info = row.get(date_column) if date_column else None
                if url:
                    urls_data.append({'url': url, 'date_from_archive': date_info})
        print(f"Caricati {len(urls_data)} URL da '{filename}'.")
    except FileNotFoundError:
        print(f"ERRORE: Il file '{filename}' non è stato trovato.")
        return None
    except Exception as e:
        print(f"ERRORE durante la lettura del file CSV degli URL: {e}")
        return None
    return urls_data

def estrai_contenuto_articolo_newspaper(url, newspaper_config):
    """Estrae titolo, testo, autori e data di pubblicazione usando newspaper3k."""
    try:
        print(f"  Download e parsing articolo: {url}")
        article = Article(url, config=newspaper_config)
        article.download()
        article.parse()
        
        publish_date_obj = None
        if article.publish_date:
            if isinstance(article.publish_date, datetime.datetime):
                if article.publish_date.tzinfo is None:
                    publish_date_obj = article.publish_date.replace(tzinfo=datetime.timezone.utc)
                else:
                    publish_date_obj = article.publish_date.astimezone(datetime.timezone.utc)
            else:
                print(f"    Avviso: data di pubblicazione per {url} non è un oggetto datetime: {article.publish_date}")
        
        authors_list = article.authors if article.authors else []

        dati_estratti = {
            "url": url,
            "titolo": article.title,
            "autori": ", ".join(authors_list),
            "data_pubblicazione_newspaper": publish_date_obj,
            "testo_articolo": article.text,
            "immagine_principale": article.top_image,
        }
        return dati_estratti
    except Exception as e:
        print(f"    ERRORE durante l'elaborazione di {url} con newspaper3k: {e}")
        return None

def salva_articoli_estratti_csv(lista_dati_articoli, nome_file):
    """Salva i dati degli articoli estratti in un file CSV."""
    if not lista_dati_articoli:
        print("Nessun dato articolo da salvare.")
        return

    fieldnames = [
        "url", "titolo", "autori", "data_pubblicazione_iso", 
        "testo_articolo", "immagine_principale"
    ]
    
    try:
        with open(nome_file, 'w', newline='', encoding='utf-8') as file_csv:
            writer = csv.DictWriter(file_csv, fieldnames=fieldnames)
            writer.writeheader()
            for articolo_data in lista_dati_articoli:
                riga_da_scrivere = {
                    "url": articolo_data.get("url"),
                    "titolo": articolo_data.get("titolo"),
                    "autori": articolo_data.get("autori"),
                    "data_pubblicazione_iso": articolo_data.get("data_pubblicazione_newspaper").isoformat() if isinstance(articolo_data.get("data_pubblicazione_newspaper"), datetime.datetime) else "DATA NON TROVATA",
                    "testo_articolo": articolo_data.get("testo_articolo"),
                    "immagine_principale": articolo_data.get("immagine_principale"),
                }
                writer.writerow(riga_da_scrivere)
        print(f"Contenuti articoli salvati con successo in '{nome_file}'")
    except IOError as e:
        print(f"Errore durante il salvataggio del file CSV '{nome_file}': {e}")

# --- FLUSSO PRINCIPALE DELLO SCRIPT ---
if __name__ == "__main__":
    # URL_COLUMN_NAME_IN_CSV e DATE_COLUMN_NAME_IN_CSV sono nomi di colonne, non percorsi.
    # Sono passati come stringhe litereali nella funzione carica_url_da_csv.
    lista_url_data = carica_url_da_csv(INPUT_URL_CSV_FILE, "url", "date_on_archive_utc_iso")
    
    contenuti_articoli_finali = []

    if lista_url_data:
        print(f"\nInizio estrazione contenuto per {len(lista_url_data)} URL da {NOME_SITO}...")
        for i, url_info in enumerate(lista_url_data):
            url_articolo = url_info['url']
            print(f"\nProcesso articolo {i+1}/{len(lista_url_data)}: {url_articolo}")
            
            data_estratta_da_archivio = None
            if url_info.get('date_from_archive') and isinstance(url_info['date_from_archive'], str) and url_info['date_from_archive'] not in ['N/A_DATE', 'DATA NON TROVATA']:
                try:
                    data_estratta_da_archivio = datetime.datetime.fromisoformat(url_info['date_from_archive'].replace('Z', '+00:00'))
                    if data_estratta_da_archivio.tzinfo is None:
                        data_estratta_da_archivio = data_estratta_da_archivio.replace(tzinfo=datetime.timezone.utc)
                except ValueError:
                    print(f"  Avviso: la data dall'archivio '{url_info['date_from_archive']}' per {url_articolo} non è in formato ISO valido, si tenterà di estrarla dalla pagina articolo.")
            
            if data_estratta_da_archivio and data_estratta_da_archivio < START_DATE_LIMIT:
                print(f"  Articolo ignorato (data da archivio: {data_estratta_da_archivio.date()} - precedente a {START_DATE_LIMIT.date()})")
                time.sleep(0.1)
                continue

            dati_articolo_estratto = estrai_contenuto_articolo_newspaper(url_articolo, config)
            
            if dati_articolo_estratto:
                data_pub_newspaper = dati_articolo_estratto.get('data_pubblicazione_newspaper')
                
                data_finale_da_usare = data_pub_newspaper if isinstance(data_pub_newspaper, datetime.datetime) else data_estratta_da_archivio
                
                if isinstance(data_finale_da_usare, datetime.datetime):
                    if data_finale_da_usare >= START_DATE_LIMIT:
                        dati_articolo_estratto['data_pubblicazione_newspaper'] = data_finale_da_usare
                        contenuti_articoli_finali.append(dati_articolo_estratto)
                        print(f"    -> Articolo '{dati_articolo_estratto.get('titolo', 'N/A')[:50]}...' aggiunto (Data: {data_finale_da_usare.date()})")
                    else:
                        print(f"    -> Articolo '{dati_articolo_estratto.get('titolo', 'N/A')[:50]}...' ignorato (Data: {data_finale_da_usare.date()} - precedente a {START_DATE_LIMIT.date()})")
                else:
                    print(f"    -> Articolo '{dati_articolo_estratto.get('titolo', 'N/A')[:50]}...' aggiunto, MA DATA DI PUBBLICAZIONE NON TROVATA o NON PARSABILE.")
                    dati_articolo_estratto['data_pubblicazione_newspaper'] = None
                    contenuti_articoli_finali.append(dati_articolo_estratto)
            
            print(f"Attesa di {DELAY_PER_ARTICLE} secondi...")
            time.sleep(DELAY_PER_ARTICLE)

    if contenuti_articoli_finali:
        salva_articoli_estratti_csv(contenuti_articoli_finali, OUTPUT_ARTICLES_CSV_FILE)
    else:
        print("Nessun contenuto articolo è stato estratto o ha superato i filtri.")
    
    print("\nEstrazione contenuti completata.")