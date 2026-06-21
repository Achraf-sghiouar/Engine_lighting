import pdfplumber
import re
import logging
from typing import List, Dict, Any
from models.schemas import ExtractedField, SourceRef, RawLineItem

logger = logging.getLogger(__name__)

def extract_from_pdf(file_path: str) -> List[Dict[str, Any]]:
    """
    Extrait les lignes d'un PDF en gérant les tableaux et le texte libre.
    """
    raw_lines = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            # 1. Tentative d'extraction des tableaux
            tables = page.extract_tables({
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "snap_tolerance": 3,
                "intersection_tolerance": 3,
            })

            if tables:
                for table in tables:
                    cleaned_table = _clean_table(table)
                    if cleaned_table and len(cleaned_table) > 1:
                        headers = cleaned_table[0]
                        indices = _detect_columns(headers)
                        for row in cleaned_table[1:]:
                            line = _extract_line_from_row(row, indices)
                            if line:
                                raw_lines.append(line)
            else:
                # 2. Fallback : extraction du texte brut
                text = page.extract_text()
                if text:
                    lines = _parse_free_text(text)
                    raw_lines.extend(lines)

    # 3. Supprimer les doublons
    return _deduplicate_lines(raw_lines)

def _clean_table(table):
    """Supprime les lignes complètement vides."""
    cleaned = []
    for row in table:
        if row and any(cell and str(cell).strip() for cell in row):
            cleaned.append([str(cell).strip() if cell else "" for cell in row])
    return cleaned

def _detect_columns(headers):
    """Détecte les colonnes Mark, Quantity, Description par mots-clés."""
    idx = {"mark": -1, "quantity": -1, "description": -1}
    patterns = {
        "mark": re.compile(r"code|ref|mark|tag|id|luminaire|réf", re.I),
        "quantity": re.compile(r"qty|quantity|quantité|unité|pcs|piece|nb|qt", re.I),
        "description": re.compile(r"description|desc|model|modele|spec|caractéristique|designation", re.I),
    }
    for i, header in enumerate(headers):
        header_clean = re.sub(r"\s+", " ", header).strip()
        for key, pat in patterns.items():
            if pat.search(header_clean):
                idx[key] = i
                break
    # Fallback si aucune colonne trouvée
    if idx["mark"] == -1 and idx["description"] == -1:
        idx["mark"] = 0
        if len(headers) >= 3:
            idx["description"] = 1
            idx["quantity"] = 2
        elif len(headers) >= 2:
            idx["description"] = 1
    return idx

def _extract_line_from_row(row, indices):
    """
    Construit un RawLineItem à partir d'une ligne de tableau.
    """
    mark = row[indices["mark"]] if indices["mark"] != -1 and indices["mark"] < len(row) else ""
    qty_raw = row[indices["quantity"]] if indices["quantity"] != -1 and indices["quantity"] < len(row) else ""
    desc_raw = row[indices["description"]] if indices["description"] != -1 and indices["description"] < len(row) else ""

    # Nettoyer la marque
    mark = re.sub(r"[^A-Za-z0-9\-]", "", mark).strip()

    # --- Extraction et validation de la quantité ---
    qty_match = re.search(r"\d+", qty_raw)
    if qty_match:
        qty = int(qty_match.group())
        # Ignorer les nombres trop grands (téléphones, codes)
        if qty > 10000:
            logger.warning(f"Quantité trop grande '{qty}' dans la colonne quantité → remplacée par 1")
            qty = 1
    else:
        qty = 1

    # Si la description est vide, on assemble les autres colonnes
    if not desc_raw:
        exclude_indices = {indices["mark"], indices["quantity"]}
        desc_parts = [row[i] for i in range(len(row)) if i not in exclude_indices and i < len(row) and row[i]]
        desc_raw = " ".join(desc_parts) if desc_parts else ""

    # Si la marque est vide, essayer de l'extraire de la description
    if not mark and desc_raw:
        fallback_mark = _extract_mark_from_description(desc_raw)
        if fallback_mark:
            mark = fallback_mark
            desc_raw = desc_raw.replace(fallback_mark, "", 1).strip()

    # Ne garder que les lignes avec une marque et une description
    if mark and desc_raw:
        return RawLineItem(
            mark=ExtractedField(value=mark, confidence="extracted"),
            quantity=ExtractedField(value=str(qty), confidence="extracted"),
            description=ExtractedField(value=desc_raw, confidence="extracted")
        )
    return None

def _extract_mark_from_description(desc):
    """Extrait un code (ex: L02a, D1) depuis le début de la description."""
    match = re.search(r"^([A-Z]{1,3}\d+[a-z]?)", desc)
    if match:
        return match.group(1)
    return ""

def _parse_free_text(text):
    """Extrait des lignes depuis du texte brut (fallback)."""
    lines = []
    pattern = r"([A-Z]{1,3}\d+[a-z]?)\s*(.*?)(\d+)\s*(un|pcs|piece|unité|pce)"
    for match in re.finditer(pattern, text, re.IGNORECASE):
        mark = match.group(1)
        desc = match.group(2).strip()
        qty = int(match.group(3))
        lines.append(RawLineItem(
            mark=ExtractedField(value=mark, confidence="extracted"),
            quantity=ExtractedField(value=str(qty), confidence="extracted"),
            description=ExtractedField(value=desc, confidence="extracted")
        ))
    return lines

def _deduplicate_lines(lines):
    """Élimine les doublons basés sur (mark, description)."""
    seen = set()
    unique = []
    for line in lines:
        key = (line.mark.value if line.mark else "", line.description.value if line.description else "")
        if key not in seen:
            seen.add(key)
            unique.append(line)
    return unique