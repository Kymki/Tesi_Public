import telethon.sync
from telethon import TelegramClient, functions, types
from telethon.tl.types import PeerChannel
import csv
import datetime
import time
import asyncio

# Importa le configurazioni dal file config.py
from config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_SESSION_NAME,
    TELEGRAM_MESSAGE_LIMIT_PER_ENTITY,
    TELEGRAM_MESSAGES_COLLECTED_CSV,
    TELEGRAM_START_DATE
)

# --- CONFIGURAZIONE SPECIFICA (mantenuta qui o spostata se utile altrove) ---
# TARGET_ENTITIES = [""] # Lista degli username o ID numerici di canali/supergruppi pubblici
# Esempio: ["ClashReport", "militarylandnet", "WarTranslated", "Edizione_Straordinaria", "militaresemplice"]
# Assicurati che questi canali siano pubblici o che il tuo account abbia accesso.
TARGET_ENTITIES = ["ClashReport", "militarylandnet", "WarTranslated", "Edizione_Straordinaria", "militaresemplice"] # Esempio di canali (modifica secondo le tue esigenze)


# Lista di parole chiave in Inglese per il filtraggio
KEYWORDS_EN = [
    "ukraine", "ukrainian", "russia", "russian", "war", "conflict", "attack",
    "military", "troops", "soldiers", "putin", "zelensky", "nato", "drone",
    "invasion", "forces", "defense", "weapon", "sanction", "peace",
    "refugee", "casualty", "territory", "frontline", "kyiv", "moscow", "kremlin",
    "donbas", "crimea", "kharkiv", "kherson", "mariupol", "bakhmut", "shelling",
    "artillery", "wagner", "himars"
]

# Lista di parole chiave in Italiano per il filtraggio
KEYWORDS_IT = [
    "ucraina", "ucraino", "russia", "russo", "guerra", "conflitto", "attacco",
    "militare", "truppe", "soldati", "putin", "zelensky", "nato", "drone",
    "invasione", "forze", "difesa", "arma", "sanzione", "pace",
    "profugo", "vittima", "territorio", "fronte", "kiev", "mosca", "cremlino",
    "donbas", "crimea", "kharkiv", "kherson", "mariupol", "bakhmut",
    "bombardamento", "artiglieria", "wagner"
]

# Unisce le due liste per creare il filtro completo.
# Lo script salverà un messaggio se contiene ALMENO UNA di queste parole.
KEYWORDS_FILTER = KEYWORDS_EN + KEYWORDS_IT

# Converte la data di inizio da tupla a oggetto datetime
START_DATE = datetime.datetime(*TELEGRAM_START_DATE, tzinfo=datetime.timezone.utc)

# --- FUNZIONE DI RACCOLTA DATI --- #

async def raccogli_dati_telegram():
    """Funzione principale asincrona per la raccolta dei dati da Telegram."""
    
    # Inizializzazione del client Telegram
    client = TelegramClient(TELEGRAM_SESSION_NAME, TELEGRAM_API_ID, TELEGRAM_API_HASH)

    print("Tentativo di connessione a Telegram...")
    try:
        await client.connect()
    except Exception as e:
        print(f"ERRORE: Impossibile connettersi a Telegram. Dettagli: {e}")
        return

    if not await client.is_user_authorized():
        print("Autenticazione richiesta.")
        phone_number_input = input("Inserisci il tuo numero di telefono (formato internazionale, es. +39...): ")
        
        try:
            sent_code_info = await client.send_code_request(phone_number_input)
            code_input = input("Inserisci il codice che hai ricevuto via Telegram: ")
            await client.sign_in(
                phone=phone_number_input,
                code=code_input,
                phone_code_hash=sent_code_info.phone_code_hash
            )
        except telethon.errors.SessionPasswordNeededError:
            password_2fa = input("Inserisci la tua password di autenticazione a due fattori (2FA): ")
            try:
                await client.sign_in(password=password_2fa)
            except Exception as e_pass:
                print(f"Si è verificato un errore durante l'inserimento della password 2FA: {e_pass}")
                if client.is_connected(): await client.disconnect()
                return
        except telethon.errors.PhoneNumberInvalidError:
            print(f"ERRORE: Il numero di telefono '{phone_number_input}' non è valido. Riprova.")
            if client.is_connected(): await client.disconnect()
            return
        except telethon.errors.PhoneCodeInvalidError:
            print(f"ERRORE: Il codice di accesso inserito non è valido. Riprova il processo di autenticazione.")
            if client.is_connected(): await client.disconnect()
            return
        except telethon.errors.PhoneCodeExpiredError:
            print(f"ERRORE: Il codice di accesso è scaduto. Richiedine uno nuovo.")
            if client.is_connected(): await client.disconnect()
            return
        except Exception as e_auth:
            print(f"Si è verificato un errore generale durante l'autenticazione: {e_auth}")
            if client.is_connected(): await client.disconnect()
            return
            
        print("Autenticazione riuscita!")
    else:
        print("Autenticazione già presente e valida.")

    # Preparazione del file CSV
    try:
        with open(TELEGRAM_MESSAGES_COLLECTED_CSV, 'w', newline='', encoding='utf-8') as file_csv:
            writer = csv.writer(file_csv)
            writer.writerow([
                "message_id", "chat_id", "chat_title", "sender_id", 
                "text", "timestamp_utc", "reply_to_message_id", "views"
            ])

            for entity_identifier in TARGET_ENTITIES:
                print(f"\n--- Inizio analisi entità: {entity_identifier} ---")
                try:
                    entity = await client.get_entity(entity_identifier)
                    
                    chat_title = getattr(entity, 'title', None)
                    if not chat_title:
                        chat_title = getattr(entity, 'username', None)
                    if not chat_title:
                         chat_title = str(getattr(entity, 'id', 'ID_Sconosciuto'))
                    
                    print(f"  Canale/Gruppo trovato: '{chat_title}' (ID: {entity.id})")

                    message_count_for_entity = 0
                    async for message in client.iter_messages(entity, limit=TELEGRAM_MESSAGE_LIMIT_PER_ENTITY, reverse=False):
                        if message.date < START_DATE:
                            print(f"  Raggiunta la data di inizio ({START_DATE.date()}), interruzione per '{chat_title}'.")
                            break
                        
                        if message.text and message.text.strip():
                            text_content = message.text.strip()
                            
                            if KEYWORDS_FILTER:
                                keyword_present_in_message = False
                                for keyword in KEYWORDS_FILTER:
                                    if keyword.lower() in text_content.lower():
                                        keyword_present_in_message = True
                                        break
                                if not keyword_present_in_message:
                                    continue
                            
                            sender_id_val = getattr(message, 'sender_id', None)
                            reply_to_val = getattr(message.reply_to, 'reply_to_msg_id', None) if hasattr(message, 'reply_to') else None
                            views_val = getattr(message, 'views', None)

                            writer.writerow([
                                message.id,
                                entity.id, 
                                chat_title,
                                sender_id_val, 
                                text_content,
                                message.date.timestamp(), 
                                reply_to_val,
                                views_val
                            ])
                            message_count_for_entity +=1
                            if message_count_for_entity % 50 == 0 : 
                                print(f"    ...raccolti {message_count_for_entity} messaggi da '{chat_title}' (ultimo del {message.date.date()})")
                    
                    print(f"  Raccolti {message_count_for_entity} messaggi da '{chat_title}' che corrispondono ai criteri.")

                except ValueError as ve:
                    print(f"ERRORE: Impossibile trovare o processare l'entità '{entity_identifier}'. Dettagli: {ve}")
                except telethon.errors.FloodWaitError as fwe:
                    print(f"ERRORE FloodWait sull'entità '{entity_identifier}': attesa di {fwe.seconds} secondi...")
                    time.sleep(fwe.seconds)
                except telethon.errors.ChannelPrivateError as cpe:
                    print(f"ERRORE: L'entità '{entity_identifier}' è privata o non accessibile. Dettagli: {cpe}")
                except Exception as e_msg_loop:
                    print(f"Errore non gestito durante la raccolta da '{entity_identifier}': {e_msg_loop.__class__.__name__} - {e_msg_loop}")
                
                print("Breve pausa di 5 secondi prima della prossima entità...")
                time.sleep(5) 
    except IOError as ioe:
        print(f"ERRORE: Impossibile scrivere sul file CSV '{TELEGRAM_MESSAGES_COLLECTED_CSV}'. Dettagli: {ioe}")
    except Exception as e_outer:
        print(f"Si è verificato un errore generale esterno al loop delle entità: {e_outer}")
    finally:
        if client.is_connected():
            await client.disconnect()
            print("Disconnesso da Telegram.")
        else:
            print("Il client non era connesso o è già stato disconnesso.")

# --- BLOCCO DI ESECUZIONE PRINCIPALE ---
if __name__ == "__main__":
    if TELEGRAM_API_ID == 12345678 or TELEGRAM_API_HASH == "IL_TUO_API_HASH" or TELEGRAM_API_ID == 0:
        print("ERRORE: Per favore, inserisci il tuo API_ID e API_HASH reali e validi nello script di configurazione (config.py).")
    else:
        asyncio.run(raccogli_dati_telegram())