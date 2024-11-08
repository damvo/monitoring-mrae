import requests
import json
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration
KEYWORDS = ["IEL", "IEL ENR", "IEL exploitation", "Moalic"]
API_BASE_URL = "https://www.projets-environnement.gouv.fr/api/records/1.0/search/"
DATASET = "projets-environnement"

def fetch_from_api(keyword):
    """
    Recherche un mot-clé via l'API projets-environnement.gouv.fr
    """
    params = {
        'dataset': DATASET,
        'q': keyword,
        'rows': 100,  # nombre de résultats par requête
    }
    
    try:
        response = requests.get(API_BASE_URL, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Erreur lors de la requête API pour '{keyword}': {e}")
        return None

def load_previous_results():
    """Charge les résultats précédents depuis le fichier JSON."""
    try:
        with open('previous_results_projets.json', 'r') as f:
            return set(tuple(x) for x in json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_results(results):
    """Sauvegarde les résultats dans un fichier JSON."""
    try:
        with open('previous_results_projets.json', 'w') as f:
            json.dump([list(x) for x in results], f)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des résultats: {e}")

def send_email(new_matches):
    """Envoie un email avec les nouveaux résultats."""
    try:
        smtp_server = "smtp.gmail.com"
        port = 587
        sender_email = os.environ["SENDER_EMAIL"]
        password = os.environ["EMAIL_PASSWORD"]
        receiver_email = os.environ["RECEIVER_EMAIL"]

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = f"Nouveaux résultats Projets-Environnement - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        body = "Nouveaux projets trouvés sur projets-environnement.gouv.fr :\n\n"
        for match in new_matches:
            body += f"Mot-clé trouvé : {match['keyword']}\n"
            body += f"Titre : {match['title']}\n"
            body += f"Description : {match['description']}\n"
            body += f"Commune : {match['commune']}\n"
            body += f"Département : {match['departement']}\n"
            body += f"URL : {match['url']}\n"
            body += "-" * 50 + "\n\n"

        message.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(message)
            print(f"Email envoyé à {receiver_email}")

    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email: {e}")

def main():
    """Fonction principale."""
    try:
        # Charger les résultats précédents
        previous_results = load_previous_results()
        current_results = set()
        new_matches_for_email = []

        # Rechercher chaque mot-clé
        for keyword in KEYWORDS:
            print(f"Recherche du mot-clé: {keyword}")
            data = fetch_from_api(keyword)
            
            if data and 'records' in data:
                for record in data['records']:
                    fields = record.get('fields', {})
                    
                    # Extraire les informations pertinentes
                    result_tuple = (
                        fields.get('titre', ''),
                        fields.get('commune', ''),
                        fields.get('departement', '')
                    )
                    
                    # Si c'est un nouveau résultat
                    if result_tuple not in previous_results:
                        current_results.add(result_tuple)
                        new_matches_for_email.append({
                            'keyword': keyword,
                            'title': fields.get('titre', ''),
                            'description': fields.get('description', ''),
                            'commune': fields.get('commune', ''),
                            'departement': fields.get('departement', ''),
                            'url': f"https://www.projets-environnement.gouv.fr/pages/fiche-projet/?tx_eaprojets_pi1[fiche]={record['recordid']}"
                        })

        if new_matches_for_email:
            print(f"Nombre de nouveaux résultats trouvés: {len(new_matches_for_email)}")
            send_email(new_matches_for_email)
            # Mettre à jour les résultats précédents avec tous les résultats actuels
            previous_results.update(current_results)
            save_results(previous_results)
        else:
            print("Aucun nouveau résultat trouvé")

    except Exception as e:
        print(f"Erreur dans la fonction principale: {e}")

if __name__ == "__main__":
    print(f"Démarrage de la surveillance Projets-Environnement - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    main()
