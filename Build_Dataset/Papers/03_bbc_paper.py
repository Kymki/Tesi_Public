import requests
from bs4 import BeautifulSoup
import csv
import time
import datetime
from urllib.parse import urljoin, urlparse
import re

# Importa le configurazioni dal file config.py
from config import (
    BBC_NEWS_ARCHIVE_URLS_CSV,
    GLOBAL_START_DATE,
    SCRAPING_MAX_PAGES_TO_SCRAPE,
    SCRAPING_DELAY_BETWEEN_REQUESTS
)

# --- CONFIGURAZIONE SPECIFICA (mantenuta qui o spostata se utile altrove) ---
NOME_SITO = "BBC_News"
STARTING_ARCHIVE_URL = "https://www.bbc.com/news/war-in-ukraine" 
BASE_URL = "https://www.bbc.com" 

# Ora queste variabili sono importate da config.py
OUTPUT_CSV_URLS = BBC_NEWS_ARCHIVE_URLS_CSV

# Converte la data di inizio da tupla a oggetto datetime
START_DATE_LIMIT = datetime.datetime(*GLOBAL_START_DATE, tzinfo=datetime.timezone.utc)
MAX_PAGES_TO_SCRAPE = SCRAPING_MAX_PAGES_TO_SCRAPE
DELAY_TRA_RICHIESTE = SCRAPING_DELAY_BETWEEN_REQUESTS

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-GB,en;q=0.5'
}

# --- FUNZIONI ---

def scarica_pagina(url):
    """Scarica il contenuto HTML di una pagina."""
    print(f"  Download pagina: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"    ERRORE durante il download di {url}: {e}")
        return None

def parse_datetime_bbc_archive(date_str_on_page):
    """
    Tenta di parsare stringhe di data relative o assolute dalla pagina archivio BBC.
    Esempi: "18 hrs ago", "2 days ago", "24 May 2025"
    Restituisce un oggetto datetime timezone-aware (UTC) o la stringa originale.
    """
    if not date_str_on_page:
        return None
    
    cleaned_date_str = date_str_on_page.strip().lower()
    cleaned_date_str = re.sub(r'\(updated:.*\)', '', cleaned_date_str, flags=re.IGNORECASE).strip()
    
    now = datetime.datetime.now(datetime.timezone.utc)

    formats_to_try = ["%d %b %Y", "%d %B %Y"]
    for fmt in formats_to_try:
        try:
            dt_obj = datetime.datetime.strptime(cleaned_date_str, fmt)
            return dt_obj.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            continue
            
    match = re.search(r'(\d+)\s*hr(s)?\s*ago', cleaned_date_str)
    if match:
        try:
            hours = int(match.group(1))
            return now - datetime.timedelta(hours=hours)
        except: pass
    
    match = re.search(r'(\d+)\s*min(s)?\s*ago', cleaned_date_str)
    if match:
        try:
            mins = int(match.group(1))
            return now - datetime.timedelta(minutes=mins)
        except: pass

    match = re.search(r'(\d+)\s*day(s)?\s*ago', cleaned_date_str)
    if match:
        try:
            days = int(match.group(1))
            return now - datetime.timedelta(days=days)
        except: pass
    
    if "yesterday" in cleaned_date_str:
        return (now - datetime.timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)

    print(f"    Avviso: Impossibile parsare la data dalla pagina archivio BBC: '{date_str_on_page}' con i metodi attuali.")
    return date_str_on_page 

def estrai_link_e_date_da_pagina_bbc(html_content, base_url):
    """Estrae URL e date (come stringhe o datetime) dalla pagina archivio/topic della BBC."""
    if not html_content:
        return []
    soup = BeautifulSoup(html_content, 'html.parser')
    articoli_nella_pagina = []

    article_cards = soup.find_all('div', attrs={'data-testid': ['london-card', 'dundee-card', 'liverpool-card']})
    
    print(f"    Trovati {len(article_cards)} potenziali contenitori di articoli (basati su data-testid).")

    for card in article_cards:
        link_tag = card.find('a', href=True) 
        url_articolo = None
        data_articolo_obj = None

        if link_tag and link_tag['href']:
            href = link_tag['href']
            parsed_href = urlparse(href)
            if (not parsed_href.scheme and href.startswith('/news/')) or \
               (parsed_href.scheme and parsed_href.netloc in ['www.bbc.com', 'www.bbc.co.uk'] and '/news/' in href):
                url_articolo = urljoin(base_url, href)
            else:
                continue
        
        date_tag = card.find('span', {'data-testid': 'card-metadata-lastupdated'})
        if date_tag:
            data_articolo_str = date_tag.get_text(strip=True)
            data_articolo_obj = parse_datetime_bbc_archive(data_articolo_str)
        
        if url_articolo:
            articoli_nella_pagina.append({'url': url_articolo, 'date_on_archive': data_articolo_obj})

    print(f"    Estratti {len(articoli_nella_pagina)} link ad articoli/video da questa pagina.")
    return articoli_nella_pagina

def trova_url_pagina_successiva_bbc(html_content, current_page_base_url):
    """Trova l'URL della pagina successiva usando il tag <link rel='next'> o la paginazione numerica."""
    if not html_content:
        return None
    soup = BeautifulSoup(html_content, 'html.parser')
    
    link_rel_next = soup.find('link', rel='next')
    if link_rel_next and link_rel_next.get('href'):
        next_url = urljoin(current_page_base_url, link_rel_next['href'])
        print(f"    Trovato link pagina successiva (da <link rel='next'>): {next_url}")
        return next_url
        
    next_button_tag = soup.find('a', {'data-testid': 'pagination-next-button', 'href': True})

    if next_button_tag:
        next_url = urljoin(current_page_base_url, next_button_tag['href'])
        print(f"    Trovato link pagina successiva (da tag 'a' con data-testid): {next_url}")
        return next_url
        
    print("    Nessun link 'pagina successiva' (<link rel='next'> o tag <a> con data-testid) trovato.")
    return None

def salva_url_csv(lista_url_dati, nome_file):
    """Salva gli URL e le date (se disponibili) in un file CSV."""
    if not lista_url_dati:
        print("Nessun URL da salvare.")
        return
    try:
        with open(nome_file, 'w', newline='', encoding='utf-8') as file_csv:
            writer = csv.writer(file_csv)
            writer.writerow(['url', 'date_on_archive_utc_iso'])
            for item in lista_url_dati:
                date_info = item['date_on_archive']
                date_str = date_info.isoformat() if isinstance(date_info, datetime.datetime) else (str(date_info) if date_info else 'N/A_DATE')
                writer.writerow([item['url'], date_str])
        print(f"URL raccolti salvati con successo in '{nome_file}'")
    except IOError as e:
        print(f"Errore durante il salvataggio del CSV '{nome_file}': {e}")

# --- FLUSSO PRINCIPALE DELLO SCRIPT ---
if __name__ == "__main__":
    tutti_gli_articoli_info = []
    url_visitati = set() 
    current_page_url = STARTING_ARCHIVE_URL
    pagine_scansionate = 0
    
    print(f"Inizio scraping degli URL degli articoli da: {STARTING_ARCHIVE_URL}")

    while current_page_url and current_page_url not in url_visitati and pagine_scansionate < MAX_PAGES_TO_SCRAPE:
        url_visitati.add(current_page_url)
        pagine_scansionate += 1
        
        parsed_current_url = urlparse(current_page_url)
        current_base = f"{parsed_current_url.scheme}://{parsed_current_url.netloc}"

        print(f"\nProcesso Pagina Archivio #{pagine_scansionate}: {current_page_url}")
        
        contenuto_pagina_archivio = scarica_pagina(current_page_url)
        if not contenuto_pagina_archivio:
            print(f"  Impossibile scaricare la pagina {current_page_url}, interruzione paginazione.")
            break

        articoli_nella_pagina_corrente = estrai_link_e_date_da_pagina_bbc(contenuto_pagina_archivio, current_base)
        
        if not articoli_nella_pagina_corrente and pagine_scansionate > 1 :
            print("  Nessun articolo trovato in questa pagina. Potrebbe essere la fine dell'archivio o un errore nei selettori.")
            break
        
        pagina_contiene_solo_articoli_vecchi = True if articoli_nella_pagina_corrente else False
        articoli_validi_aggiunti_da_pagina = 0

        for art_info in articoli_nella_pagina_corrente:
            data_obj = art_info.get('date_on_archive')
            url_art = art_info.get('url')

            if url_art in (item['url'] for item in tutti_gli_articoli_info):
                continue

            if isinstance(data_obj, datetime.datetime):
                if data_obj >= START_DATE_LIMIT:
                    tutti_gli_articoli_info.append(art_info)
                    articoli_validi_aggiunti_da_pagina +=1
                    pagina_contiene_solo_articoli_vecchi = False 
                else:
                    print(f"    Articolo '{url_art}' datato {data_obj.date()} è troppo vecchio.")
            else:
                print(f"    Articolo '{url_art}' ha una data non parsabile/mancante ('{data_obj}'), lo includo per ora.")
                tutti_gli_articoli_info.append(art_info)
                articoli_validi_aggiunti_da_pagina +=1
                pagina_contiene_solo_articoli_vecchi = False 

        if pagina_contiene_solo_articoli_vecchi and articoli_nella_pagina_corrente and articoli_validi_aggiunti_da_pagina == 0:
             print(f"  Tutti gli articoli validi con data in questa pagina ({current_page_url}) sembrano essere più vecchi di {START_DATE_LIMIT.date()}. Interruzione paginazione.")
             break
        
        current_page_url = trova_url_pagina_successiva_bbc(contenuto_pagina_archivio, current_base)
        
        if current_page_url:
            print(f"Attesa di {DELAY_TRA_RICHIESTE} secondi prima della prossima pagina...")
            time.sleep(DELAY_TRA_RICHIESTE)
        else:
            print("Fine della paginazione: nessun link 'pagina successiva' valido trovato.")

    if tutti_gli_articoli_info:
        url_visti_per_salvataggio = set()
        lista_univoca_articoli = []
        for item in tutti_gli_articoli_info:
            if item['url'] not in url_visti_per_salvataggio:
                lista_univoca_articoli.append(item)
                url_visti_per_salvataggio.add(item['url'])
        
        print(f"\nTotale URL univoci raccolti: {len(lista_univoca_articoli)}")
        salva_url_csv(lista_univoca_articoli, OUTPUT_CSV_URLS)
    else:
        print("Nessun URL di articolo è stato raccolto.")

    print(f"\nScraping degli URL dall'archivio BBC completato. Pagine scansionate: {pagine_scansionate}.")