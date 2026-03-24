"""
diagnostic.py — Voir la structure HTML de brvm.org
====================================================
Lance : python diagnostic.py
"""

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.brvm.org/",
}

url = "https://www.brvm.org/fr/esv/paiement-de-dividendes"

print("=" * 60)
print("Connexion à brvm.org...")
print("=" * 60)

r = requests.get(url, headers=HEADERS, timeout=20, verify=False)
print(f"Status HTTP : {r.status_code}")
print(f"Taille réponse : {len(r.text)} caractères")
print()

soup = BeautifulSoup(r.text, "lxml")

# Tables
tables = soup.find_all("table")
print(f"Nombre de tables <table> : {len(tables)}")
for i, t in enumerate(tables):
    rows = t.find_all("tr")
    print(f"  Table {i+1} : {len(rows)} lignes")

print()

# Views Drupal
views = soup.select(".views-row, .view-row")
print(f"Nombre de .views-row : {len(views)}")

print()

# Classes principales
divs = soup.find_all("div", class_=True)
classes = set()
for d in divs:
    for c in d.get("class", []):
        if "view" in c.lower() or "dividend" in c.lower() or "esv" in c.lower() or "paiement" in c.lower():
            classes.add(c)
print(f"Classes CSS pertinentes : {classes}")

print()

# Sauvegarder le HTML pour inspection
with open("brvm_page.html", "w", encoding="utf-8") as f:
    f.write(r.text)
print("HTML sauvegardé dans : brvm_page.html")
print("Ouvre ce fichier dans un éditeur pour voir la structure exacte.")

print()
print("=" * 60)
print("Extrait du HTML (500 premiers caractères du body) :")
print("=" * 60)
body = soup.find("body")
if body:
    print(body.get_text()[:500])