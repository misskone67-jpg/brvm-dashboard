"""
scraper.py — BRVM Dividendes
==============================
✅ Basé sur la vraie structure HTML de brvm.org :
   - Emetteur  : td.views-field-field-emetteur-esv
   - Exercice  : td.views-field-field-exercice-comptable-esv
   - Paiement  : td.views-field-field-date-de-paiement-esv
   - Ex-div    : td.views-field-field-date-ex-dividende
   - Dividende : td.views-field-field-montant-du-dividende-net
   - Pagination : ?page=0 à ?page=39

Dépendances :
    pip install requests beautifulsoup4 pandas lxml urllib3
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import logging
import urllib3
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.brvm.org"
LIST_URL = f"{BASE_URL}/fr/esv/paiement-de-dividendes"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.brvm.org/",
    "Connection": "keep-alive",
}

COLONNES = [
    "Emetteur", "Exercice", "Date_paiement",
    "Date_ex_dividende", "Dividende_net",
    "Prix_action", "Rendement",
    "Date_scraping"
]


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def _parse_montant(val) -> float:
    """
    '1 320 FCFA'   → 1320.0
    '85,56 FCFA'   → 85.56
    '2 375 FCFA'   → 2375.0
    '513,012 FCFA' → 513.012
    '700 F CFA'    → 700.0
    """
    if not val:
        return 0.0
    txt = str(val).strip()
    txt = re.sub(r"[Ff]\s*CFA|FCFA|CFA", "", txt, flags=re.IGNORECASE).strip()
    # Supprimer les espaces (séparateurs de milliers : "1 320" → "1320")
    txt = txt.replace(" ", "").strip()
    # Remplacer la virgule décimale française par un point ("85,56" → "85.56")
    # La virgule est décimale si elle est UNIQUE dans le nombre
    if txt.count(",") == 1:
        txt = txt.replace(",", ".")
    else:
        txt = txt.replace(",", "")
    try:
        v = float(txt)
        if v > 0:
            return v
    except ValueError:
        pass
    return 0.0


def _get_text(td) -> str:
    """Extrait le texte propre d'une cellule td."""
    if td is None:
        return ""
    # Chercher dans les spans (dates avec date-display-single)
    span = td.find("span", class_="date-display-single")
    if span:
        # Utiliser l attribut content pour avoir la date ISO
        iso = span.get("content", "")
        if iso:
            # Extraire juste l année pour le champ Exercice si c est le 1er janvier
            year_match = re.match(r"(\d{4})-01-01", iso)
            if year_match:
                return year_match.group(1)
            return iso[:10]  # YYYY-MM-DD
        return span.get_text(strip=True)
    return td.get_text(strip=True)


def scraper_page(page: int = 0, visible: bool = False, avec_prix: bool = True) -> pd.DataFrame:
    """
    Scrape une page de la liste des dividendes BRVM.
    Utilise les vraies classes CSS du tableau.
    """
    url     = f"{LIST_URL}?page={page}" if page > 0 else LIST_URL
    session = _session()
    log.info(f"Scraping page {page} → {url}")

    # 3 tentatives
    for tentative in range(1, 4):
        try:
            r = session.get(url, timeout=20, verify=False)
            r.raise_for_status()
            break
        except requests.RequestException as e:
            log.warning(f"Tentative {tentative}/3 : {e}")
            if tentative == 3:
                log.error(f"Page {page} abandonnée.")
                return pd.DataFrame(columns=COLONNES)
            time.sleep(2 * tentative)

    soup = BeautifulSoup(r.text, "lxml")

    records = []
    # Parcourir chaque ligne du tableau
    for tr in soup.find_all("tr"):
        # Extraire chaque champ via sa classe CSS exacte
        emetteur  = tr.find("td", class_=lambda c: c and "field-emetteur-esv" in c)
        exercice  = tr.find("td", class_=lambda c: c and "field-exercice-comptable-esv" in c)
        date_pay  = tr.find("td", class_=lambda c: c and "field-date-de-paiement-esv" in c)
        date_ex   = tr.find("td", class_=lambda c: c and "field-date-ex-dividende" in c)
        dividende = tr.find("td", class_=lambda c: c and "field-montant-du-dividende-net" in c)

        if not emetteur:
            continue

        records.append({
            "Emetteur"          : _get_text(emetteur),
            "Exercice"          : _get_text(exercice),
            "Date_paiement"     : _get_text(date_pay),
            "Date_ex_dividende" : _get_text(date_ex),
            "Dividende_net"     : _parse_montant(_get_text(dividende)),
            "Prix_action"       : 0.0,
            "Rendement"         : 0.0,
            "Date_scraping"     : datetime.now().strftime("%d/%m/%Y %H:%M"),
        })

    log.info(f"  {len(records)} lignes extraites sur la page {page}")

    if not records:
        return pd.DataFrame(columns=COLONNES)

    df = pd.DataFrame(records)

    # Charger TOUS les prix en une seule requête puis associer
    if avec_prix:
        global _PRIX_CACHE
        if not _PRIX_CACHE:
            log.info("  Chargement des prix depuis brvm.org...")
            _PRIX_CACHE = _charger_tous_les_prix(session)

        for idx, row in df.iterrows():
            prix = get_prix_action(row["Emetteur"], session)
            df.at[idx, "Prix_action"] = prix
            if prix > 0 and row["Dividende_net"] > 0:
                df.at[idx, "Rendement"] = round(row["Dividende_net"] / prix * 100, 2)

    log.info(f"  ✅ Page {page} : {len(df)} enregistrements")
    return df


def scraper_toutes_pages(nb_pages: int = 40, visible: bool = False,
                          avec_prix: bool = True, callback=None) -> pd.DataFrame:
    """Scrape toutes les pages 0 à nb_pages-1."""
    frames  = []
    erreurs = []
    log.info(f"🚀 Démarrage : {nb_pages} pages")

    for page in range(nb_pages):
        log.info(f"📄 Page {page + 1}/{nb_pages}")
        try:
            df_page = scraper_page(page, visible, avec_prix)
            if not df_page.empty:
                frames.append(df_page)
        except Exception as e:
            log.error(f"Erreur page {page} : {e}")
            erreurs.append(page)

        if callback:
            callback(page, nb_pages, frames[-1] if frames else pd.DataFrame())

        time.sleep(0.3)

    if not frames:
        return pd.DataFrame(columns=COLONNES)

    df_final = pd.concat(frames, ignore_index=True)
    df_final = df_final.drop_duplicates(subset=["Emetteur", "Exercice"], keep="last")
    df_final = df_final.sort_values(["Emetteur", "Exercice"]).reset_index(drop=True)
    log.info(f"✅ {len(df_final)} lignes | {len(erreurs)} erreurs")
    return df_final


# Prix des actions depuis le site officiel brvm.org
COURS_URL = "https://www.brvm.org/fr/cours-actions/0"

_PRIX_CACHE = {}


def _charger_tous_les_prix(session=None):
    """Charge tous les cours depuis brvm.org/fr/cours-actions/0 en une seule requête."""
    if session is None:
        session = _session()
    prix = {}
    try:
        r = session.get(COURS_URL, timeout=20, verify=False)
        if r.status_code != 200:
            log.warning(f"cours-actions status: {r.status_code}")
            return prix
        soup = BeautifulSoup(r.text, "lxml")
        # La table 4 (index 3) contient tous les cours
        # Format : Symbole | Nom | Volume | Veille | Ouverture | Clôture | Variation
        tables = soup.find_all("table")
        table_cours = tables[3] if len(tables) >= 4 else soup

        for tr in table_cours.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) >= 6:
                symbole = cells[0].get_text(strip=True).upper()
                nom     = cells[1].get_text(strip=True).upper()
                cours   = _parse_montant(cells[5].get_text(strip=True))
                if cours > 0 and symbole:
                    prix[symbole] = cours
                    prix[nom]     = cours
        log.info(f"✅ {len(prix)} cours chargés depuis brvm.org")
    except Exception as e:
        log.warning(f"Erreur chargement prix : {e}")
    return prix


# Mapping symbole BRVM → noms d'émetteurs
SYMBOLE_TO_NOM = {
    "SNTS": ["SONATEL"], "ORAC": ["ORANGE CI", "ORANGE"],
    "STBC": ["SITAB"], "PALC": ["PALM CI", "PALM"],
    "FTSC": ["FILTISAC CI", "FILTISAC"], "PRSC": ["TRACTAFRIC CI", "TRACTAFRIC"],
    "SDSC": ["BOLLORE TRANSPORT & LOGISTICS", "BOLLORE", "AGL"],
    "TTLC": ["TOTAL", "TOTAL CI"], "TTLS": ["TOTAL SN", "TOTAL SENEGAL"],
    "SHEC": ["VIVO ENERGY CI", "VIVO ENERGY"],
    "SMBC": ["SMB"], "BICB": ["BIIC"], "BICC": ["BICI CI", "BICI"],
    "SGBC": ["SGB CI", "SGCI"], "ABJC": ["SERVAIR ABIDJAN CI", "SERVAIR"],
    "BOAB": ["BOA BENIN"], "BOABF": ["BOA BURKINA"],
    "BOAC": ["BOA CI"], "BOAM": ["BOA MALI"],
    "BOAN": ["BOA NIGER"], "BOAS": ["BOA SENEGAL"],
    "ECOC": ["ECOBANK CI"], "ETIT": ["ECOBANK TI"],
    "NSBC": ["NSIA BANQUE"], "CBIBF": ["CORIS BANK"],
    "ORGT": ["ORAGROUP"], "SAFC": ["SAFCA"],
    "SIBC": ["SIB", "SOCIETE IVOIRIENNE DE BANQUE"],
    "ONTBF": ["ONATEL"], "CIEC": ["CIE"],
    "SDCC": ["SODECI", "SODE CI"], "NTLC": ["NESTLE CI", "NESTLE"],
    "UNLC": ["UNILEVER CI"], "SLBC": ["SOLIBRA"],
    "SOGC": ["SOGB"], "SPHC": ["SAPH"],
    "SCRC": ["SUCRIVOIRE"], "SICC": ["SICOR"],
    "CFAC": ["CFAO", "CFAO MOTORS"], "BNBC": ["BERNABE"],
    "NEIC": ["NEI CEDA"], "UNXC": ["UNIWAX"],
    "SEMC": ["CROWN SIEM"], "SIVC": ["ERIUM", "AIR LIQUIDE"],
    "STAC": ["SETAO"], "CABC": ["SICABLE"],
    "LNBB": ["LOTERIE BENIN", "LNB"],
}

def get_prix_action(nom_action: str, session=None) -> float:
    """Récupère le cours de clôture depuis brvm.org (site officiel)."""
    global _PRIX_CACHE
    if not nom_action or not isinstance(nom_action, str):
        return 0.0

    if not _PRIX_CACHE:
        _PRIX_CACHE = _charger_tous_les_prix(session)

    nom_upper = nom_action.upper().strip()

    # Recherche exacte
    if nom_upper in _PRIX_CACHE:
        return _PRIX_CACHE[nom_upper]

    # Recherche via mapping symbole → nom
    for symbole, noms in SYMBOLE_TO_NOM.items():
        if nom_upper in [n.upper() for n in noms] or any(nom_upper in n.upper() for n in noms):
            if symbole in _PRIX_CACHE:
                return _PRIX_CACHE[symbole]

    # Recherche partielle
    for key, val in _PRIX_CACHE.items():
        if nom_upper in key or key in nom_upper:
            return val

    return 0.0


# Alias compatibilité
def scraper_page_edge(page: int = 0, driver_path=None) -> pd.DataFrame:
    return scraper_page(page)

def scraper_toutes_pages_edge(driver_path=None) -> pd.DataFrame:
    return scraper_toutes_pages(nb_pages=40)

def get_prix_action_edge(action_name: str, driver_path=None) -> float:
    return get_prix_action(action_name)


if __name__ == "__main__":
    print("Test page 0...")
    df = scraper_page(page=0, avec_prix=False)
    print(df.to_string())
    print(f"\n✅ {len(df)} enregistrements trouvés")