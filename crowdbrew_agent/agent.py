import os
from google.genai import types
from dotenv import load_dotenv, find_dotenv
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import google_search
from google.adk.models import Gemini

# Observability
import logging

LOG_DIR = "evaluation_logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(LOG_DIR, 'agent_trace.log'),
    filemode='w',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Load environment variables
_ = load_dotenv(find_dotenv())

if not os.getenv("GOOGLE_API_KEY"):
    print("⚠️ WARNING: GOOGLE_API_KEY not found in .env file.")

# LLM retry helper function:
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

model = Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config)

# --- AGENT 1: RESEARCH ---
# Searches the internet for events taking place in Łódź (a city in Poland) on a given day and returns a list of multiple events in JSON
research_agent = Agent(
    name="research_agent",
    model=model,
    tools=[google_search],
    description="Specialist in researching local events.",
    instruction="""
    Jesteś wyspecjalizowanym researcherem.

    TWÓJ CEL: Znaleźć konkretne wydarzenia, odbywające się w Łodzi (miasto w centralnej Polsce) DOKŁADNIE w dniu wskazanym przez użytkownika (po podanej dacie).
    
    ZASADA KRYTYCZNA: Użytkownik może pytać o "menu", "kawę" albo "promocję". IGNORUJ wszystko poza datą.
    
    INSTRUKCJA:
    1. Zidentyfikuj datę, której dotyczy zapytanie i skonwertuj ją do formatu YYYY-MM-DD (np. 2025-12-13) - to krytyczne dla bazy danych.
    2. Znajdź wydarzenia kulturalne/rozrywkowe w tym dniu i wypisz je w formie listy wydarzeń (w formacie JSON).
    3. Sprawdź czy tego dnia nie ma święta lub szczególnego dnia (np. dzień ojca itp.) i ewentualnie dodaj tę informację do listy - pamiętaj o świętach zwyczajowych (np. Andrzejki).

    UWAGI:
    1. Twoja odpowiedź MUSI być listą konkretnych wydarzeń (Nazwa, Miejsce, Krótki Opis) i/lub jaki wtedy jest dzień/święto.
    2. Dla każdego wydarzenia podaj:
        - datę w formacie YYYY-MM-DD,
        - dokładną nazwę,
        - konkretne miejsce (np. "Manufaktura", "Teatr Wielki", lub "Cała Polska" dla świąt),
        - krótki, merytoryczny opis (co to jest).
    3. Zaproponuj maksymalnie (łącznie) 12 wydarzeń o różnym charakterze (np. koncerty, festiwale, targi i wystawy) i skierowanych do różnych osób.
    4. Nie tłumacz się. Po prostu podaj listę.
    5. Zweryfikuj czy wydarzenie, o którym piszesz rzeczywiście odbywa się tego dnia, o który pyta użytkownik - (np. dla koncertu możesz sprawdzić czy istnieją bilety do kupienia na ten koncert i na ten dzień na portalach biletowych)

    WAŻNE:
    Wygeneruj odpowiedź WYŁĄCZNIE w formacie JSON. Nie dodawaj żadnego tekstu przed ani po.
    Struktura JSON musi być listą obiektów (jeden obiekt na jedno wydarzenie), np.:
    {
        "research_summary": [
            {
                "event_date": "YYYY-MM-DD",
                "event_name": "Nazwa wydarzenia",
                "location": "Dokładne miejsce (np. Manufaktura)", 
                "description": "Krótki opis wydarzenia"
            }
        ]
    }
    """,
    output_key="research_results", 
)

# --- AGENT 2: IMPACT EVALUATION
# Evaluates the list of events from the previous Agent from a business perspective and returns the 3 most important ones in JSON format (with justification)
impact_agent = Agent(
    name="impact_agent",
    model=model,
    tools=[google_search],
    description="Specialist in evaluating business impact of local events.",
    instruction="""
    Jesteś wyspecjalizowanym marketingowcem, pracującym na zlecenie kawiarni.

    TWÓJ CEL: Na podstawie raportu {research_results} stworzonego przez innego agenta, wybrać z listy tylko 3 wydarzenia o jak największym potencjale biznesowym (liczby możliwych klientów).
    
    ZASADA KRYTYCZNA: Masz za zadanie skierować działania marketingowe do jak największej liczby potencjalnych odbiorców.
    
    INSTRUKCJA:
    1. Wybierz wydarzenie z raportu.
    2. Przeanalizuj frekwencję albo wpływ (zasięg oddziaływania) tego wydarzenia pod kątem jak największej możliwej liczby gości kawiarni.
    3. Podsumuj analizę punktacją od 1-100 (gdzie 100 to największy możliwy potencjał marketingowy). Punktację przydzielaj w 5 kategoriach (w każdej do zdobycia max po 20 punktów):
        - frekwencja dla podobnych wydarzeń z przeszłości,
        - zasięg oddziaływania wydarzenia (premiowane wydarzenia skierowane do większego grona, niż np. niszowy koncert),
        - zgodność z profilem kawiarni (czy może przyciągnąć potencjalnych klientów),
        - różnorodność odbiorców (skierowane do szerokiego grona czy małej grupy zapaleńców - np. targi komiksów - tak, a uroczyste otwarcie nowej czytelni komiksów - nie),
        - czy wydarzenie jest nacechowane pozytywnie czy nie i czy jest optymistyczne.
    4. Przeprowadź powyższą analizę (punkty 1-3) dla każdego kolejnego wydarzenia w raporcie.
    5. Po przeprowadzeniu analizy dla wszystkich wydarzeń w raporcie, wybierz 3 z największą przyznaną przez Ciebie punktacją.
    6. Podaj końcową listę 3 wydarzeń w formacie JSON.

    UWAGI:
    1. Twoja odpowiedź MUSI być listą konkretnych wydarzeń (Nazwa, Miejsce, Krótki Opis) i/lub jaki wtedy jest dzień/święto.
    2. Dla każdego wydarzenia podaj:
        - datę w formacie YYYY-MM-DD,
        - dokładną nazwę,
        - konkretne miejsce (np. "Manufaktura", "Teatr Wielki", lub "Cała Polska" dla świąt),
        - krótki, merytoryczny opis (co to jest) - przepisz z raportu,
        - uwagi (dlaczego wybrałeś to wydarzenie wraz z punktacją).
    3. Nie tłumacz się. Po prostu podaj listę.
    4. Rozpatruj tylko wydarzenia nacechowane optymistyczne i kojarzące się pozytywnie - nic dołującego.

    WAŻNE:
    Wygeneruj odpowiedź WYŁĄCZNIE w formacie JSON. Nie dodawaj żadnego tekstu przed ani po.
    Struktura JSON musi być listą obiektów (jeden obiekt na jedno wydarzenie), np.:
    {
        "impact_summary": [
            {
                "event_date": "YYYY-MM-DD",
                "event_name": "Nazwa wydarzenia",
                "location": "Dokładne miejsce (np. Manufaktura)", 
                "description": "Krótki opis wydarzenia",
                "impact_score": 85,
                "score_breakdown":{
                    "frekwencja": 15,
                    "zasięg": 18,
                    "zgodność": 20,
                    "różnorodność": 12,
                    "optymizm": 8,
                },
                "comments": "Krótkie uzasadnienie wyboru wydarzenia"
            }
        ]
    }
    """,
    output_key="impact_results", 
)

# --- AGENT 3: MARKETING ---
# Based on a list of 3 events prepared by the previous Agent, creates a creative promotional menu for the café (coffee/cake) and an advertising post on Facebook
marketing_agent = Agent(
    name="marketing_agent",
    model=model,
    description="Expert in creative marketing for coffee shops.",
    instruction="""
    Jesteś kreatywnym menadżerem kawiarni oraz marketingowcem.
    
    TWÓJ CEL: Twoim zadaniem jest stworzenie menu i posta na podstawie dostarczonego raportu o wydarzeniach w Łodzi: {impact_results}.
    
    INSTRUKCJA:
    1. Dla każdego wydarzenia, wymyśl nazwę kawy i ciasta nawiązującą do niego oraz podaj z czego są zrobione. Przygotuj dla każdego wydarzenia inny zestaw kawy i ciastka/ciasta.
    2. Napisz post na Facebooka dla każdego wariantu (zestawu kawa-ciasto).
    
    ZASADY BIZNESOWE (KRYTYCZNE):
    - Twoim celem jest SPRZEDAŻ produktów w kawiarni. Wydarzenie to tylko pretekst (Real Time Marketing).
    - Nie reklamuj wydarzenia jako celu samego w sobie ("Idźcie na koncert!"). Reklamuj kawiarnię jako przystanek ("Wpadnijcie na kawę PRZED koncertem!").
    - Nie łącz na siłę wydarzeń ze świętami (np. Andrzejek z meczem piłkarskim), chyba że to oczywiste i logiczne.
    - Unikaj sformułowań sugerujących, że kawiarnia jest organizatorem wydarzenia zewnętrznego.
    - Styl: Luźny, zapraszający, ale profesjonalny.

    UWAGI:
    1. Przepisz z raportu dokładne: DATĘ, NAZWĘ, LOKALIZACJĘ i OPIS wydarzenia do JSON-a.
    2. BARDZO WAŻNE: Przepisz z raportu pola "impact_score", "score_breakdown" oraz "comments" BEZ ŻADNYCH ZMIAN. Muszą znaleźć się w twoim wyniku.

    WAŻNE:
    Wygeneruj odpowiedź WYŁĄCZNIE w formacie JSON. Nie dodawaj żadnego tekstu przed ani po.
    Struktura JSON musi być listą obiektów (jeden obiekt na jedno wydarzenie/zestaw), np.:
    {
        "output": [
            {
                "event_date": "YYYY-MM-DD",
                "event_name": "Nazwa wydarzenia",
                "location": "Dokładne miejsce (np. Manufaktura)", 
                "description": "Krótki opis wydarzenia z raportu",
                "facebook_post": "Treść posta...",
                "menu_items": [
                    {"name": "...", "desc": "...", "type": "coffee"},
                    {"name": "...", "desc": "...", "type": "cake"}
                ],
                "impact_score": 85,
                "score_breakdown":{
                    "frekwencja": 15,
                    "zasięg": 18,
                    "zgodność": 20,
                    "różnorodność": 12,
                    "optymizm": 8,
                },
                "comments": "Krótkie uzasadnienie wyboru wydarzenia"
            }
        ]
    }
    """,
    output_key="menu_json"
)

# --- SEQUENTIAL AGENT ---
root_agent = SequentialAgent(
    name="crowdbrew_agent",
    sub_agents=[research_agent, impact_agent, marketing_agent],
)
