from typing import List, Dict, Optional, Pattern
from pydantic import BaseModel, Field
import re


class MarketPack(BaseModel):
    """
    Spécification déclarative d'un marché régional d'éclairage.
    Permet au moteur d'ingestion et de matching d'opérer de façon agnostique.
    """
    code: str = Field(..., description="Code marché ISO ou identifiant unique (ex: 'MA', 'FR', 'US')")
    label: str = Field(..., description="Nom complet du marché régional")
    language: str = Field(default="fr", description="Langue principale du marché ('fr', 'en', 'ar')")
    
    # 1. Triage documentaire (Agent 1)
    triage_include_keywords: List[str] = Field(default_factory=list, description="Mots-clés de chapitres pertinents")
    triage_exclude_keywords: List[str] = Field(default_factory=list, description="Mots-clés de corps d'état hors-sujet")
    
    # 2. Découpage et repérage d'articles (Agent 2)
    item_header_patterns: List[str] = Field(default_factory=list, description="Expressions régulières de repérage d'articles")
    
    # 3. MicroRAG & Glossaire technique (Agent 3)
    glossary: Dict[str, str] = Field(default_factory=dict, description="Définitions contextuelles pour le MicroRAG")
    
    # 4. Normes & Réglementations électriques (Agent 4)
    grid_voltage_default: int = Field(default=230, description="Tension nominale standard du réseau (V)")
    grid_frequency_hz: int = Field(default=50, description="Fréquence standard du réseau (Hz)")
    regulatory_certifications: List[str] = Field(default_factory=list, description="Normes et labels officiels (ex: CE, NM, NF, UL)")
    
    # 5. Unités de mesure & Devise
    units_system: str = Field(default="metric", description="'metric' (lux, mm) ou 'imperial' (foot-candles, inches)")
    currency: str = Field(default="MAD", description="Devise par défaut du marché")

    def compile_item_regex(self) -> Optional[Pattern]:
        """Compile l'ensemble des motifs d'articles en une expression régulière optimisée."""
        if not self.item_header_patterns:
            return None
        combined = "|".join(f"(?:{p})" for p in self.item_header_patterns)
        return re.compile(combined, re.IGNORECASE)
