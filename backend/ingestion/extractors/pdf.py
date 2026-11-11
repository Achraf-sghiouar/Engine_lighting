import re
import logging
from typing import List, Dict, Any
from models.schemas import ExtractedField, SourceRef, RawLineItem

logger = logging.getLogger(__name__)

def extract_from_pdf(file_path: str) -> List[Dict[str, Any]]:
    """
    Extrait les lignes d'un PDF en gérant les tableaux via Camelot et le texte libre via pdfplumber en fallback.
    """
    raw_lines = []
    
    try:
        import camelot
        tables = camelot.read_pdf(file_path, flavor='stream', pages='all')
    except Exception as e:
        logger.error(f"Camelot extraction failed: {e}")
        tables = []

    if tables and len(tables) > 0:
        for t_idx, table in enumerate(tables):
            df = table.df
            if df.empty or len(df) < 2:
                continue
                
            # Scan the first 4 rows to find the actual header row
            best_row_idx = 0
            best_indices = {"mark": -1, "quantity": -1, "description": -1, "characteristics": -1}
            max_matches = -1
            
            for r_idx in range(min(4, len(df))):
                headers = [str(col) for col in df.iloc[r_idx].tolist()]
                idx = _detect_columns(headers, apply_fallback=False)
                matches = sum(1 for v in idx.values() if v != -1)
                if matches > max_matches:
                    max_matches = matches
                    best_indices = idx
                    best_row_idx = r_idx
                    
            indices = best_indices
            if indices["mark"] == -1 and indices["description"] == -1:
                headers = [str(col) for col in df.iloc[best_row_idx].tolist()]
                indices = _detect_columns(headers, apply_fallback=True)
            
            for r_idx in range(best_row_idx + 1, len(df)):
                row = [str(cell) for cell in df.iloc[r_idx].tolist()]
                
                # Skip empty rows
                if not any(row):
                    continue
                    
                # Skip administrative keywords
                row_text = " ".join([cell.lower() for cell in row if cell])
                ignore_keywords = ["cautionnement", "article", "planning", "luminaires décoratifs"]
                if any(kw in row_text for kw in ignore_keywords) and len(row_text) < 50:
                    continue

                line = _extract_line_from_row(row, indices)
                if line:
                    raw_lines.append(line)
    else:
        # Fallback : extraction du texte brut
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    lines = _parse_free_text(text)
                    raw_lines.extend(lines)

    # 3. Supprimer les doublons
    return _deduplicate_lines(raw_lines)

def _detect_columns(headers, apply_fallback=True):
    """Détecte les colonnes Mark, Quantity, Description, Characteristics par mots-clés."""
    idx = {"mark": -1, "quantity": -1, "description": -1, "characteristics": -1}
    patterns = {
        "mark": re.compile(r"code|ref|mark|tag|id|luminaire|réf", re.I),
        "quantity": re.compile(r"qty|quantity|quantité|unités|pcs|piece|nb|qt", re.I),
        "description": re.compile(r"description|desc|model|modèle|spec|designation", re.I),
        "characteristics": re.compile(r"caractéristique|caracteristique|technical|technique", re.I),
    }
    for i, header in enumerate(headers):
        header_clean = re.sub(r"\s+", " ", header).strip()
        for key, pat in patterns.items():
            if pat.search(header_clean):
                idx[key] = i
                break
                
    # Fallback si aucune colonne trouvée
    if apply_fallback and idx["mark"] == -1 and idx["description"] == -1:
        idx["mark"] = 0
        if len(headers) >= 3:
            idx["description"] = 1
            idx["quantity"] = 2
        elif len(headers) >= 2:
            idx["description"] = 1
    return idx

def _clean_text(text: str) -> str:
    """Removes newlines and excess whitespace."""
    if not text: return ""
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()

def _extract_line_from_row(row, indices):
    """
    Construit un RawLineItem à partir d'une ligne de tableau.
    """
    mark = row[indices["mark"]] if indices["mark"] != -1 and indices["mark"] < len(row) else ""
    qty_raw = row[indices["quantity"]] if indices["quantity"] != -1 and indices["quantity"] < len(row) else ""
    desc_raw = row[indices["description"]] if indices["description"] != -1 and indices["description"] < len(row) else ""
    char_raw = row[indices["characteristics"]] if indices["characteristics"] != -1 and indices["characteristics"] < len(row) else ""

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

    # Assembler desc et char
    full_desc = _clean_text(desc_raw)
    if char_raw:
        full_desc += " | " + _clean_text(char_raw)

    # Si la description est vide, on assemble les autres colonnes
    if not full_desc:
        exclude_indices = {indices["mark"], indices["quantity"]}
        desc_parts = [row[i] for i in range(len(row)) if i not in exclude_indices and i < len(row) and row[i]]
        full_desc = " ".join([_clean_text(part) for part in desc_parts]) if desc_parts else ""

    # Si la marque est vide, essayer de l'extraire de la description
    if not mark and full_desc:
        fallback_mark = _extract_mark_from_description(full_desc)
        if fallback_mark:
            mark = fallback_mark
            full_desc = full_desc.replace(fallback_mark, "", 1).strip()

    # Ne garder que les lignes avec une marque et une description
    if mark and full_desc:
        return RawLineItem(
            mark=ExtractedField(value=mark, confidence="table"),
            quantity=ExtractedField(value=str(qty), confidence="table"),
            description=ExtractedField(value=full_desc, confidence="table")
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