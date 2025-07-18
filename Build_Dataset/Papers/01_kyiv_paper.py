import requests
from bs4 import BeautifulSoup
import csv
import time
import datetime
from urllib.parse import urljoin
import re

# Importa le configurazioni dal file config.py
from config import (
    KYIV_INDEPENDENT_ARCHIVE_URLS_CSV,
    GLOBAL_START_DATE,
    SCRAPING_MAX_PAGES_TO_SCRAPE,
    SCRAPING_DELAY_BETWEEN_REQUESTS
)

# --- CONFIGURAZIONE SPECIFICA (mantenuta qui o spostata se utile altrove) ---
NOME_SITO = "Kyiv_Independent"
STARTING_ARCHIVE_URL = "https://kyivindependent.com/news-archive/"
BASE_URL = "https://kyivindependent.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Converte la data di inizio da tupla a oggetto datetime
START_DATE_LIMIT = datetime.datetime(*GLOBAL_START_DATE, tzinfo=datetime.timezone.utc)
MAX_PAGES_TO_SCRAPE = SCRAPING_MAX_PAGES_TO_SCRAPE
DELAY_TRA_RICHIESTE = SCRAPING_DELAY_BETWEEN_REQUESTS

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
    
def parse_datetime_from_data_archive_id(date_str_on_page):
    """
    Tenta di parsare una stringa di data dall'attributo 'data-archive-id'.
    Gestisce il formato ISO 8601 (es. "2025-06-03T13:43:00.000Z")
    e il formato precedentemente osservato (es. "Tue Jun 03 2025 13:18:00 GMT+0000 (Coordinated Universal Time)").
    """
    if not date_str_on_page:
        return None
    
    dt_obj = None
    
    try:
        if date_str_on_page.endswith('Z'):
            if '.' in date_str_on_page:
                parts = date_str_on_page.split('.')
                if len(parts) > 1 and 'Z' in parts[1]:
                    date_str_on_page = parts[0] + 'Z' 
            
            dt_obj = datetime.datetime.fromisoformat(date_str_on_page.replace('Z', '+00:00'))
        
        if dt_obj:
            if dt_obj.tzinfo is None:
                dt_obj = dt_obj.replace(tzinfo=datetime.timezone.utc)
            return dt_obj
            
    except ValueError:
        pass
    except Exception as e_iso:
        print(f"    Avviso durante il parsing ISO della data '{date_str_on_page}': {e_iso}")
        pass

    try:
        date_string_to_parse = date_str_on_page.split('(')[0].strip()
        dt_obj = datetime.datetime.strptime(date_string_to_parse, "%a %b %d %Y %H:%M:%S GMT%z")
        return dt_obj
    except ValueError:
        print(f"    Avviso: Impossibile parsare la data '{date_str_on_page}' con i formati noti.")
        return date_str_on_page
    except Exception as e_other:
        print(f"    ERRORE INASPETTATO nel parsing della data '{date_str_on_page}': {e_other}")
        return date_str_on_page

def estrai_link_e_date_da_pagina_archivio(html_content, base_url):
    """
    Estrae URL degli articoli e date (dall'attributo data-archive-id) da una pagina di archivio.
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    articoli_trovati_nella_pagina = []
    
    article_blocks = soup.find_all('article', class_=['js-card', 'archiveCard'])
    
    if not article_blocks:
        print("    Avviso: Nessun blocco articolo ('article.js-card.archiveCard') trovato sulla pagina.")

    for block in article_blocks:
        url_articolo = None
        data_articolo_obj = None

        link_tag = block.find('h3', class_='archiveCard__title')
        if link_tag:
            actual_a_tag = link_tag.find('a', class_='archiveCard__link')
            if actual_a_tag and actual_a_tag.get('href'):
                url_articolo = urljoin(base_url, actual_a_tag['href'])

        data_archive_id_str = block.get('data-archive-id')
        if data_archive_id_str:
            data_articolo_obj = parse_datetime_from_data_archive_id(data_archive_id_str)
        else:
            print(f"    Avviso: Attributo 'data-archive-id' non trovato per un articolo.")

        if url_articolo:
            articoli_trovati_nella_pagina.append({'url': url_articolo, 'date_on_archive': data_articolo_obj})
        else:
            pass

    print(f"    Trovati {len(articoli_trovati_nella_pagina)} link ad articoli in questa pagina.")
    return articoli_trovati_nella_pagina

def trova_url_pagina_successiva(html_content, base_url_per_join):
    """Trova l'URL della pagina successiva usando il tag <link rel='next'>."""
    if not html_content:
        return None
    soup = BeautifulSoup(html_content, 'html.parser')
    
    next_page_tag = soup.find('link', rel='next')
    
    if next_page_tag and next_page_tag.get('href'):
        next_page_url = urljoin(base_url_per_join, next_page_tag['href'])
        print(f"    Trovato link pagina successiva (da <link rel='next'>): {next_page_url}")
        return next_page_url
    else:
        print("    Nessun link 'pagina successiva' (<link rel='next'>) trovato nell'head.")
        return None

def salva_url_raccolti_csv(lista_url_dati, nome_file):
    """Salva gli URL e le date (se disponibili) in un file CSV."""
    if not lista_url_dati:
        print("Nessun URL da salvare.")
        return

    try:
        with open(nome_file, 'w', newline='', encoding='utf-8') as file_csv:
            writer = csv.writer(file_csv)
            writer.writerow(['url', 'date_on_archive_utc_iso'])
            for item in lista_url_dati:
                date_str = item['date_on_archive'].isoformat() if isinstance(item['date_on_archive'], datetime.datetime) else (item['date_on_archive'] if item['date_on_archive'] else 'N/A_DATE')
                writer.writerow([item['url'], date_str])
        print(f"URL raccolti salvati con successo in '{nome_file}'")
    except IOError as e:
        print(f"Errore durante il salvataggio del file CSV '{nome_file}': {e}")

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
        print(f"\nProcesso Pagina Archivio #{pagine_scansionate}: {current_page_url}")
        
        contenuto_pagina_archivio = scarica_pagina(current_page_url)
        if not contenuto_pagina_archivio:
            print(f"  Impossibile scaricare la pagina {current_page_url}, interruzione paginazione.")
            break

        articoli_nella_pagina_corrente = estrai_link_e_date_da_pagina_archivio(contenuto_pagina_archivio, BASE_URL)
        
        if not articoli_nella_pagina_corrente and pagine_scansionate > 1 :
            print("  Nessun articolo trovato in questa pagina, possibile fine dell'archivio o errore nei selettori.")
            break
        
        pagina_contiene_solo_articoli_vecchi = True if articoli_nella_pagina_corrente else False

        for art_info in articoli_nella_pagina_corrente:
            if isinstance(art_info['date_on_archive'], datetime.datetime):
                if art_info['date_on_archive'] >= START_DATE_LIMIT:
                    tutti_gli_articoli_info.append(art_info)
                    pagina_contiene_solo_articoli_vecchi = False
                else:
                    print(f"    Articolo '{art_info['url']}' datato {art_info['date_on_archive'].date()} (più vecchio di {START_DATE_LIMIT.date()}).")
            else:
                tutti_gli_articoli_info.append(art_info)
                pagina_contiene_solo_articoli_vecchi = False

        if pagina_contiene_solo_articoli_vecchi and articoli_nella_pagina_corrente:
             print(f"  Tutti gli articoli in questa pagina sembrano essere più vecchi di {START_DATE_LIMIT.date()}. Interruzione paginazione.")
             break
        
        current_page_url = trova_url_pagina_successiva(contenuto_pagina_archivio, BASE_URL)
        
        if current_page_url:
            print(f"Attesa di {DELAY_TRA_RICHIESTE} secondi prima della prossima pagina...")
            time.sleep(DELAY_TRA_RICHIESTE)
        else:
            print("Fine della paginazione o link 'pagina successiva' non trovato.")

    if tutti_gli_articoli_info:
        url_visti_per_salvataggio = set()
        lista_univoca_articoli = []
        for item in tutti_gli_articoli_info:
            if item['url'] not in url_visti_per_salvataggio:
                lista_univoca_articoli.append(item)
                url_visti_per_salvataggio.add(item['url'])
        
        print(f"\nTotale URL univoci raccolti: {len(lista_univoca_articoli)}")
        salva_url_raccolti_csv(lista_univoca_articoli, KYIV_INDEPENDENT_ARCHIVE_URLS_CSV)
        print(f"Gli URL raccolti sono pronti per essere usati con lo script di estrazione del contenuto.")
    else:
        print("Nessun URL di articolo è stato raccolto.")

    print(f"\nScraping degli URL dall'archivio completato. Pagine scansionate: {pagine_scansionate}.")