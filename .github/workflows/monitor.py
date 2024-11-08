import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
import json

# Configuration des constantes
URL = "https://www.mrae.developpement-durable.gouv.fr"
KEYWORDS = ["IEL", "IEL ENR", "IEL exploitation", "Moalic"]
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def load_previous_results():
    """Charge les résultats précédents depuis le fichier JSON."""
    try:
        with open('previous_results.json', 'r') as f:
            return set(tuple(x) for x in json.load(f))
    except FileNotFoundError:
        return set()
    except json.JSONDecodeError:
        print("Erreur de lecture du fichier JSON, création d'un nouveau fichier.")
        return set()

def save_results(results):
    """Sauvegarde les résultats dans un fichier JSON."""
    try:
        with open('previous_results.json', 'w') as f:
            # Convertit les tuples en listes pour la sérialisation JSON
            json.dump([list(x) for x in results], f)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des résultats: {e}")

def send_email(new_matches):
    """
    Envoie un email avec les nouveaux résultats trouvés.
    
    Args:
        new_matches (list): Liste des nouveaux résultats trouvés
    """
    try:
        smtp_server = "smtp.gmail.com"
        port = 587
        sender_email = os.environ["SENDER_EMAIL"]
        password = os.environ["EMAIL_PASSWORD"]
        receiver_email = os.environ["RECEIVER_EMAIL"]

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = f"Nouveaux résultats MRAE - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Construction du corps de l'email
        body = "Nouveaux résultats trouvés sur le site MRAE :\n\n"
        for match in new_matches:
            body += f"Mot-clé trouvé : {match['keyword']}\n"
            body += f"Texte : {match['text']}\n"
            body += f"URL : {match['url']}\n"
            body += "-" * 50 + "\n\n"

        message.attach(MIMEText(body, "plain"))

        # Envoi de l'email
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(message)
            print(f"Email envoyé à {receiver_email}")

    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email: {e}")

def search_keywords():
    """
    Recherche les mots-clés sur le site MRAE.
    
    Returns:
        list: Liste des résultats trouvés
    """
    try:
        response = requests.get(URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        # Recherche chaque mot-clé
        for keyword in KEYWORDS:
            elements = soup.find_all(text=lambda text: text and keyword.lower() in text.lower())
            
            for element in elements:
                # Recherche du lien le plus proche
                parent = element.find_parent('a')
                if parent and 'href' in parent.attrs:
                    url = parent['href']
                    if not url.startswith('http'):
                        url = f"{URL}{url}"
                    
                    result = {
                        'text': element.strip(),
                        'url': url,
                        'keyword': keyword
                    }
                    results.append(result)
                    print(f"Trouvé: {keyword} - {url}")
        
        return results
    
    except requests.RequestException as e:
        print(f"Erreur lors de la requête HTTP: {e}")
        return []
    except Exception as e:
        print(f"Erreur inattendue lors de la recherche: {e}")
        return []

def main():
    """Fonction principale du script."""
    try:
        # Charger les résultats précédents
        previous_results = load_previous_results()
        
        # Rechercher les nouveaux résultats
        current_results = search_keywords()
        
        # Convertir les résultats en tuples pour pouvoir les comparer
        current_result_tuples = {(r['text'], r['url'], r['keyword']) for r in current_results}
        
        # Trouver les nouveaux résultats
        new_results = current_result_tuples - previous_results
        
        if new_results:
            print(f"Nombre de nouveaux résultats trouvés: {len(new_results)}")
            # Convertir les nouveaux résultats en format complet pour l'email
            new_results_full = [
                r for r in current_results
                if (r['text'], r['url'], r['keyword']) in new_results
            ]
            send_email(new_results_full)
        else:
            print("Aucun nouveau résultat trouvé")
        
        # Sauvegarder tous les résultats actuels
        save_results(current_result_tuples)
        
    except Exception as e:
        print(f"Erreur dans la fonction principale: {e}")

if __name__ == "__main__":
    print(f"Démarrage de la surveillance MRAE - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    main()
