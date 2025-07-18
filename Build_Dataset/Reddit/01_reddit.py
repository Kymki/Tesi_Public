import praw
import datetime
import csv
import time

# Importa le configurazioni dal file config.py
from config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    REDDIT_POSTS_COLLECTED_CSV,
    REDDIT_COMMENTS_COLLECTED_CSV
)

# --- CONFIGURAZIONE SPECIFICA (mantenuta qui o spostata se utile altrove) ---
# Elenco dei subreddit da cui raccogliere i dati
SUBREDDITS_LISTA = ["worldnews", "europe", "ukraine", "UkraineWarReport", "RussiaUkraineWarNews"]
# Parole chiave per filtrare i post all'interno dei subreddit
KEYWORDS = ["ukraine", "russia", "zelensky", "putin", "nato" ]
# Limite di post da raccogliere per ogni combinazione subreddit/keyword
POST_LIMIT_PER_QUERY = 200

# --- FUNZIONI ---

def inizializza_praw():
    """Inizializza e restituisce un'istanza di PRAW."""
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )
    print("Autenticazione a Reddit riuscita (modalità read-only o utente).")
    return reddit

def raccogli_dati_reddit(reddit_instance):
    """Funzione principale per la raccolta dei dati da Reddit."""
    
    print(f"Inizio raccolta dati da Reddit per i subreddit: {', '.join(SUBREDDITS_LISTA)}")
    print(f"Parole chiave utilizzate: {', '.join(KEYWORDS)}")

    # Preparazione dei file CSV
    with open(REDDIT_POSTS_COLLECTED_CSV, 'w', newline='', encoding='utf-8') as file_posts, \
         open(REDDIT_COMMENTS_COLLECTED_CSV, 'w', newline='', encoding='utf-8') as file_comments:
        
        writer_posts = csv.writer(file_posts)
        writer_comments = csv.writer(file_comments)

        # Intestazioni dei file CSV
        writer_posts.writerow([
            "post_id", "subreddit", "titolo", "testo_post", 
            "autore_post", "timestamp_utc_post", "score_post", 
            "num_commenti_post", "url_post", "parola_chiave_ricerca"
        ])
        writer_comments.writerow([
            "commento_id", "post_id_riferimento", "subreddit", "autore_commento", 
            "testo_commento", "timestamp_utc_commento", "score_commento"
        ])

        for nome_subreddit in SUBREDDITS_LISTA:
            print(f"\n--- Inizio analisi subreddit: r/{nome_subreddit} ---")
            subreddit = reddit_instance.subreddit(nome_subreddit)
            
            query_ricerca = ' OR '.join(KEYWORDS)

            try:
                print(f"Eseguo ricerca con query: '{query_ricerca}' in r/{nome_subreddit}")
                for submission in subreddit.search(query=query_ricerca, limit=POST_LIMIT_PER_QUERY, sort='relevant'):
                    print(f"  Trovato post: {submission.id} - {submission.title[:50]}...")
                    
                    autore_post = submission.author.name if submission.author else "[eliminato]"
                    writer_posts.writerow([
                        submission.id,
                        nome_subreddit,
                        submission.title,
                        submission.selftext,
                        autore_post,
                        submission.created_utc,
                        submission.score,
                        submission.num_comments,
                        submission.permalink,
                        query_ricerca
                    ])

                    submission.comments.replace_more(limit=5)
                    comment_count = 0
                    for comment in submission.comments.list():
                        if comment_count >= 50:
                            break
                        
                        autore_commento = comment.author.name if comment.author else "[eliminato]"
                        writer_comments.writerow([
                            comment.id,
                            submission.id,
                            nome_subreddit,
                            autore_commento,
                            comment.body,
                            comment.created_utc,
                            comment.score
                        ])
                        comment_count += 1
                    
            except Exception as e:
                print(f"Errore durante la raccolta da r/{nome_subreddit} con query '{query_ricerca}': {e}")
                continue
            
            print(f"--- Fine analisi subreddit: r/{nome_subreddit} ---")

    print("\nRaccolta dati da Reddit completata.")
    print(f"I dati dei post sono stati salvati in: {REDDIT_POSTS_COLLECTED_CSV}")
    print(f"I dati dei commenti sono stati salvati in: {REDDIT_COMMENTS_COLLECTED_CSV}")

# --- BLOCCO DI ESECUZIONE PRINCIPALE ---
if __name__ == "__main__":
    if REDDIT_CLIENT_ID == "IL_TUO_CLIENT_ID" or REDDIT_CLIENT_SECRET == "IL_TUO_CLIENT_SECRET":
        print("ERRORE: Per favore, inserisci le tue credenziali API di Reddit nello script di configurazione (config.py).")
    else:
        reddit = inizializza_praw()
        if reddit:
            raccogli_dati_reddit(reddit)