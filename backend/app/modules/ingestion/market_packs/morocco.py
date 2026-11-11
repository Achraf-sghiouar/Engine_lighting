from .base import MarketPack

MOROCCO_PACK = MarketPack(
    code="MA",
    label="Maroc (CPS Marchés Publics & Privés, CCAG-T)",
    language="fr",
    
    # Mots-clés de triage documentaire (Agent 1)
    triage_include_keywords=[
        "electricite", "électricité", "courants forts", "cfo",
        "lustrerie", "eclairage", "éclairage", "luminaire",
        "securite", "sécurité", "bloc autonome", "baes"
    ],
    triage_exclude_keywords=[
        "gros oeuvre", "gros œuvre", "peinture", "plomberie",
        "menuiserie", "terrassement", "vrd", "etancheite", "étanchéité",
        "climatisation", "cvc", "ascenseur", "sonorisation"
    ],
    
    # Motifs d'articles du BPU / CPS (Agent 2)
    item_header_patterns=[
        r"Prix\s*N°\s*(\d+)",
        r"Article\s*N°\s*(\d+)",
        r"BPU\s*N°\s*(\d+)",
        r"Poste\s*N°\s*(\d+)"
    ],
    
    # Glossaire MicroRAG (Agent 3)
    glossary={
        "sati": "SATI: Système Automatique de Test Intégré pour blocs de secours.",
        "baes": "BAES: Bloc Autonome d'Éclairage de Sécurité (famille 'secours').",
        "baeh": "BAEH: Bloc Autonome d'Éclairage pour Habitation.",
        "bapi": "BAPI: Bloc Autonome Portatif d'Intervention.",
        "dali": "DALI: Protocole de gradation et commande d'éclairage numérique.",
        "ugr": "UGR: Taux d'éblouissement d'inconfort unifié (norme bureaux UGR < 19)."
    },
    
    # Normes et réseau électrique
    grid_voltage_default=230,
    grid_frequency_hz=50,
    regulatory_certifications=["NM", "CE", "ENEC", "ISO 9001"],
    
    # Système de mesures et devise
    units_system="metric",
    currency="MAD"
)
