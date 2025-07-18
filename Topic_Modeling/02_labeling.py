import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Importa le configurazioni dal file config.py
from config import (
    DOCUMENT_TOPICS_EN_CSV,
    DOCUMENT_TOPICS_IT_CSV,
    DISTRIBUTION_TOPIC_CHART_EN_PNG,
    DISTRIBUTION_TOPIC_CHART_IT_PNG
)

# --- CONFIGURAZIONE SPECIFICA (mantenuta qui o spostata se utile altrove) ---
# Labels dei topic per le due lingue
# Assicurati che questi ID corrispondano ai topic nel modello LDA.
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

# --- FUNZIONE DI ANALISI E VISUALIZZAZIONE ---
def analizza_e_visualizza_distribuzione(filepath, topic_labels, lingua, output_filename):
    """
    Carica i dati, calcola la distribuzione dei topic per fonte e crea un grafico.
    """
    print(f"\n--- Inizio Analisi Distribuzione Topic per la Lingua: {lingua.upper()} ---")
    
    try:
        df = pd.read_csv(filepath)
        colonna_topic = [col for col in df.columns if 'topic_dominante' in col][0]
        print(f"  File caricato: {filepath}. Trovata colonna topic: '{colonna_topic}'")
    except FileNotFoundError:
        print(f"  ERRORE: File '{filepath}' non trovato. Salto questa analisi.")
        return
    except IndexError:
        print(f"  ERRORE: Nessuna colonna 'topic_dominante' trovata in '{filepath}'. Salto questa analisi.")
        return
    except Exception as e:
        print(f"  ERRORE durante il caricamento di '{filepath}': {e}")
        return

    df.dropna(subset=[colonna_topic], inplace=True)
    df['topic_label'] = df[colonna_topic].map(topic_labels)
    df.dropna(subset=['topic_label'], inplace=True)
    
    distribuzione_percentuale = pd.crosstab(df['fonte'], df['topic_label'], normalize='index') * 100
    
    print("\nTabella: Distribuzione Percentuale dei Topic per Fonte (%)")
    print(distribuzione_percentuale.round(2))

    print("\nCreazione del grafico a barre impilate...")
    try:
        sns.set_theme(style="whitegrid")
        
        ax = distribuzione_percentuale.plot(
            kind='bar', 
            stacked=True, 
            figsize=(16, 10),
            colormap='viridis'
        )

        plt.title(f'Distribuzione dei Topic per Fonte (Lingua: {lingua.upper()})', fontsize=18, pad=20)
        plt.ylabel('Percentuale di Documenti (%)', fontsize=12)
        plt.xlabel('Fonte dei Dati', fontsize=12)
        plt.xticks(rotation=45, ha="right")
        
        plt.legend(title='Topic', bbox_to_anchor=(1.02, 1), loc='upper left')
        
        plt.tight_layout(rect=[0, 0, 0.85, 1])
        
        plt.savefig(output_filename, dpi=300, bbox_inches='tight')
        print(f"Grafico salvato con successo in '{output_filename}'")
        plt.show()
    except Exception as e:
        print(f"Si è verificato un errore durante la creazione del grafico: {e}")

# --- FLUSSO PRINCIPALE ---
if __name__ == "__main__":
    # Analisi per l'inglese
    analizza_e_visualizza_distribuzione(
        filepath=DOCUMENT_TOPICS_EN_CSV,
        topic_labels=TOPIC_LABELS_EN,
        lingua="Inglese",
        output_filename=DISTRIBUTION_TOPIC_CHART_EN_PNG
    )

    # Analisi per