import re
import os
import pandas as pd
import pdfplumber
import docx
from models.schemas import ExtractedItem
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class OmniDocumentExtractor:

    def __init__(self):
        # 1. DÉCOUPEUR UNIVERSEL DE PRIX 
        self.split_pattern = re.compile(r'(?i)(?:PRIX|ARTICLE|ITEM|REP\.?)\s*(?:N\s*[°ºoO0*]?\s*)?(\d+)')

        # 2. BASE DE CONNAISSANCES MARQUES
        self.known_brands = [
            "philips", "schréder", "schreder", "disano", "leds c4", "thorn", "mazda", "iguzzini", "gmr", "nexia", 
            "prilux", "bega", "artemide", "targetti", "indal", "holophane", "sammode", "ruud", "cree", "siteco", "lavov", "neko"
        ]

        # 3. CATÉGORISATION
        self.cat_exterieur = r'\b(?:ext[eé]rieur|fa[çc]ades?|parkings?|voiries?|stades?|terrains?|corniche|lampadaires?|urbain|routier|projecteurs?)\b'
        self.cat_securite = r'\b(?:secours|incendie|anti-panique|baes|baeh|sati|bapi|blocs?\s+autonomes?|[eé]vacuation|eclairage\s+de\s+s[eé]curit[eé])\b'
        self.cat_interieur = r'\b(?:int[eé]rieur|lustrerie|b[aâ]timents?|salles?|couverts?|bureaux?|locaux|downlights?|dalles?|plafonniers?|r[eé]glettes?|profil[eé]s?|encastr[eé]s? plafond)\b'

        self.chapitre_pattern = re.compile(r'(?i).*(?:ECLAIRAGE|LUSTRERIE|S[EÉ]CURIT[EÉ]|EXT[EÉ]RIEUR|INT[EÉ]RIEUR).*')

        # 4. FILTRES D'INCLUSION (Doit désigner une source de lumière ou un support)
        # 💡 "Projecteur" ne doit pas être suivi de "de son"
        self.cibles_pattern = re.compile(
            r'\b(?:luminaires?|projecteurs?(?!\s+de\s+son)|leds?|lanternes?|foyers?|encastr[eé]s?|spots?|hublots?|'
            r'blocs?(?!\s+autonomes?\s+portatifs)|baes|baeh|sati|bapi|ambiance|[eé]vacuation|rubans?|appliques?|dalles?|r[eé]glettes?|downlights?|'
            r'bornes?\s+lumineuses?|lampadaires?|panneaux?(?!\s+solaires?)|panels?|suspensions?|'
            r'tubes?(?!\s+annel[eé])|ampoules?|eclairage|m[aâ]ts?|cand[eé]labres?)\b', 
            re.IGNORECASE
        )

        self.exclus_pattern = re.compile(
            r'\b(?:sonorisation|audio|son\b|cam[eé]ras?|vid[eé]osurveillance|vid[eé]o|vms|'
            r'climatisation|plomberie|peinture|menuiserie|'
            r'c[aâ]bles?|conducteurs?|fils?|cuivre|tranch[eé]es?|fourreaux?|buses?|regards?|chambres?|'
            r'massifs?|terrassement|d[eé]blais?|remblais?|b[eé]ton|transformateurs?|tgbt|'
            r'disjoncteurs?|onduleurs?|armoires?|coffrets?|batteries?|mise\s+[aà]\s+la\s+terre|terre|'
            r'prestation|limite|assurance|installation|cellules?(?!\s+phot[oe])|'
            r'd[eé]tecteurs?|prises?|courants?\s+forts?|electricit[eé]|postes?\s+de\s+transformation|'
            r'd[eé]pose|transfert|d[eé]montage|plaques?\s+[aà]\s+bornes?|portes?\s+de\s+visite|borniers?|bo[iî]tes?\s+de\s+jonction|raccordements?|'
            r'prescriptions?|goulottes?|groupes?\s+[eé]lectrog[eè]nes?|centrales?|capteurs?|pressostats?|horloges?|'
            r'serveurs?|imprimantes?|tourniquets?|portillons?|ordinateurs?|mini\s*pc|switch|baies?|brassage|cartes?|convertisseurs?|fibres?|optiques?|pigtails?|r[eé]seaux?|travers[eé]es?|'
            r'enceintes?|haut[- ]?parleurs?|amplificateurs?|diffuseurs?|retours?|subwoofers?|'
            r'palans?|supports?\s+structure|[eé]crans?|pitch|streaming|plate\s*formes?|unit[eé]s?\s+centrales?)\b',
            re.IGNORECASE
        )

        self.bpu_memory: Dict[str, Dict[str, str]] = {}

    def _extract_bpu_from_dataframe(self, df: pd.DataFrame):
        if df.empty: return
        header_row_index = -1
        for idx, row in df.iterrows():
            row_str = " ".join([str(x).lower() for x in row.values])
            if re.search(r'\b(?:prix|rep(?:[eè]re)?|n[°ºo]|article)\b', row_str) and re.search(r'\b(?:quantit[eé]s?|qte|qt[eé]|q\.)\b', row_str):
                header_row_index = idx
                break
                
        if header_row_index != -1:
            df.columns = [str(c).lower().replace('\n', ' ').strip() for c in df.iloc[header_row_index]]
            df = df.iloc[header_row_index+1:] 
            col_prix, col_qte, col_unite = None, None, None
            for col in df.columns:
                if re.search(r'\b(?:prix|rep(?:[eè]re)?|n[°ºo]|article)\b', col): col_prix = col
                if re.search(r'\b(?:quantit[eé]s?|qte|qt[eé]|q\.)\b', col): col_qte = col
                if re.search(r'\b(?:unit[eé]s?|u|un\.)\b', col): col_unite = col

            if col_prix and col_qte:
                for _, row in df.iterrows():
                    try:
                        val_prix = str(row[col_prix])
                        if val_prix.lower() in ['nan', 'none', 'null']: continue
                        num_match = re.search(r'\d+', val_prix)
                        if num_match:
                            num_prix = str(int(num_match.group())) 
                            qte_brute = str(row[col_qte]).strip()
                            if pd.isna(row[col_qte]) or qte_brute.lower() in ['nan', 'none', '', 'null']: continue
                            qte_clean = re.sub(r'\s+', '', qte_brute).replace(',', '.')
                            qte_match = re.search(r'(\d+(?:\.\d+)?)', qte_clean)
                            qte_finale = str(int(float(qte_match.group(1)))) if qte_match and float(qte_match.group(1)).is_integer() else qte_match.group(1) if qte_match else qte_brute
                            unite = str(row[col_unite]).strip() if col_unite and pd.notna(row[col_unite]) else ""
                            self.bpu_memory[num_prix] = {"quantite": qte_finale, "unite": unite.upper()}
                    except: continue

        for _, row in df.iterrows():
            row_vals = [str(x).strip() for x in row.values if pd.notna(x) and str(x).strip() not in ['', 'nan', 'null']]
            if len(row_vals) >= 3:
                num_prix, quantite, unite = None, None, None
                for i, val in enumerate(row_vals):
                    if re.match(r'^(U|ML|Ens|Forfait|FF|M2|M3|KG|T|Pce)$', val, re.IGNORECASE):
                        unite = val.upper()
                        if i > 0 and re.match(r'^[\d\s.,]+$', row_vals[i-1]):
                            quantite = row_vals[i-1]
                        elif i + 1 < len(row_vals) and re.match(r'^[\d\s.,]+$', row_vals[i+1]):
                            quantite = row_vals[i+1]
                    if not num_prix and i < 3: 
                        num_match = re.match(r'^(?:Prix\s*N[°ºo]?\s*)?(\d+)$', val, re.IGNORECASE)
                        if num_match:
                            num_prix = str(int(num_match.group(1)))
                if num_prix and quantite and num_prix not in self.bpu_memory:
                    qte_clean = re.sub(r'\s+', '', quantite).replace(',', '.')
                    qte_match = re.search(r'(\d+(?:\.\d+)?)', qte_clean)
                    if qte_match:
                        qte_finale = str(int(float(qte_match.group(1)))) if float(qte_match.group(1)).is_integer() else qte_match.group(1)
                        self.bpu_memory[num_prix] = {"quantite": qte_finale, "unite": unite or ""}

    def _extract_bpu_from_text_fallback(self, full_text: str):
        match = re.search(r'(?i)(?:BORDEREAU\s+DES\s+PRIX|DETAIL\s+ESTIMATIF|CADRE\s+DU\s+DETAIL).*', full_text, re.DOTALL)
        if not match: return
        bpu_text = re.sub(r'\n\s*\|', ' |', match.group(0))
        for line in bpu_text.split('\n'):
            line = line.strip()
            num_match = re.match(r'^(\d+)(?:\s*\||\s+-|\s*\.|\b)', line)
            if num_match:
                current_prix = str(int(num_match.group(1)))
                uq_match = re.search(r'\b(U|ML|Ens|Forfait|FF|M2|M3|KG|T|Pce)\b\s*(?:\||:|-|\s)*\s*(\d+(?:[.,]\s*\d+)?)\b', line, re.IGNORECASE)
                if uq_match:
                    self.bpu_memory[current_prix] = {"quantite": uq_match.group(2).replace(' ', '').replace(',', '.'), "unite": uq_match.group(1).upper()}

    def _is_luminaire_block(self, bloc: str) -> bool:
        t = bloc.lower()

        # Termes qui DISQUALIFIENT immédiatement
        EXCLUSIONS_FORTES = [
            'cellule hta', 'cellule mt', 'poste de transformation', 'transformateur',
            'jeu de barres', 'disjoncteur', 'sectionneur', 'interrupteur général',
            'télécommande', 'coffret', 'armoire', 'tableau divisionnaire', 'tgbt',
            'câble', 'conducteur', 'regard', 'tranchée', 'candélabre'
        ]

        # 1. EXCLUSION FORTE : si le TITRE (première ligne) contient un terme exclu → rejet direct
        premiere_ligne = t.split('\n')[0] if '\n' in t else t[:150]
        if any(excl in premiere_ligne for excl in EXCLUSIONS_FORTES):
            # Exception : "candélabre solaire" AVEC luminaire intégré reste valide
            if 'solaire' in premiere_ligne and ('lumen' in t or 'led' in t):
                pass  # on garde (c'est un luminaire solaire)
            else:
                return False

        # 2. Compter les specs PHOTOMÉTRIQUES (le vrai marqueur d'un luminaire)
        specs = 0
        if re.search(r'\d+[\s.,]*\d*\s*(lm|lumen)', t): specs += 1
        if re.search(r'\d+[\s.,]*\d*\s*(w\b|watt)', t): specs += 1
        if re.search(r'ip\s*\d{2}', t): specs += 1
        if re.search(r'\d{4}\s*k\b|kelvin', t): specs += 1
        if re.search(r'\bik\s*\d{2}', t): specs += 1
        if re.search(r'\b(cri|ra|irc)\b', t): specs += 1
        if re.search(r'lm/w|lm/m', t): specs += 1

        # 3. Le bloc DOIT parler de lumière/luminaire
        has_lum = bool(re.search(
            r'(?i)(luminaire|projecteur|spot|panel|dalle|downlight|plafonnier|'
            r'applique|hublot|r[eé]glette|bandeau|ruban|bloc autonome|baes|bapi|'
            r'lampadaire|suspension|profil[eé]|balisage|encastr[eé])', t))

        # 4. Marqueur lumière fort = flux lumineux OU température couleur OU LED + spec
        has_light_marker = bool(re.search(r'flux lumineux|lumen|température de couleur|\bled\b', t))

        # RÈGLE : terme luminaire + marqueur lumière + au moins 2 specs
        return has_lum and has_light_marker and specs >= 2

    def _extract_luminaires(self, full_text: str) -> List[ExtractedItem]:
        self.last_full_text = full_text
        extracted_results = []
        blocs = re.split(self.split_pattern, full_text)

        for i in range(len(blocs)):
            if i % 2 != 0 and i + 1 < len(blocs):
                numero_prix = blocs[i].strip()
                texte_du_prix = blocs[i+1]
                
                if len(texte_du_prix.strip()) < 10: continue

                # Couper le BPU s'il est aspiré par le dernier prix
                bpu_match = re.search(r'(?i)\n\s*(BORDEREAUX?\s+DES\s+PRIX|D[EÉ]TAIL\s+ESTIMATIF|CADRE\s+DU\s+D[EÉ]TAIL)', texte_du_prix)
                if bpu_match:
                    texte_du_prix = texte_du_prix[:bpu_match.start()]

                lignes = [ligne.strip() for ligne in texte_du_prix.split('\n') if len(ligne.strip()) > 3]
                designation = lignes[0] if lignes else f"Prix {numero_prix}"

                # Filtre agressif sur le titre
                if re.search(r'(?i)(d[eé]pose|transfert|c[aâ]bles?|tranch[eé]es?|massifs?|regards?|fourreaux?|armoires?|d[eé]montage|terre|cuivre)', designation):
                    continue
                
                if not self._is_luminaire_block(texte_du_prix):
                    continue

                qte_val, unite_val = None, None
                num_prix_match = re.search(r'\d+', numero_prix)
                if num_prix_match:
                    num_prix = str(int(num_prix_match.group())) 
                    if num_prix in self.bpu_memory:
                        qte_val = self.bpu_memory[num_prix]["quantite"]
                        unite_val = self.bpu_memory[num_prix]["unite"]

                item = ExtractedItem(
                    Rep=f"Prix N° {numero_prix}",
                    Designation=designation,
                    Quantite=qte_val, 
                    Unite=unite_val,
                    Texte_Source=texte_du_prix.strip()
                )
                
                if not any(existing_item.Rep == item.Rep for existing_item in extracted_results):
                    extracted_results.append(item)
                    
        return extracted_results

    def _process_native(self, reader, total_pages):
        """Texte natif : pypdf lit tout, rapide même sur 872 pages."""
        logger.info("CPC: lecture native (pypdf)...")
        full_text = ""
        for i, page in enumerate(reader.pages):
            try:
                full_text += (page.extract_text() or "") + "\n"
            except Exception as e:
                logger.error(f"Page {i}: {e}")
        logger.info(f"CPC: {len(full_text)} caractères lus")
        return full_text

    def _process_scanned(self, file_path, total_pages):
        """
        Scanné : 
        1. OCR LÉGER (dpi=100) pour REPÉRER les pages luminaires
        2. OCR QUALITÉ (dpi=200) SEULEMENT sur ces pages
        """
        import concurrent.futures
        
        logger.info(f"CPC: document scanné de {total_pages} pages — phase repérage")

        # Mots qui indiquent une page luminaire
        luminaire_keywords = re.compile(
            r'(?i)(luminaire|projecteur|spot|panel|dalle|downlight|'
            r'plafonnier|applique|hublot|r[eé]glette|bloc autonome|baes|'
            r'\d+\s*(lm|lumen|watt|w\b)|ip\s*\d+|flux lumineux)'
        )

        def ocr_light(page_num):
            """OCR rapide basse résolution pour repérage, timeout strict."""
            def _do():
                imgs = convert_from_path(file_path, dpi=100,
                        first_page=page_num, last_page=page_num)
                return pytesseract.image_to_string(imgs[0], lang='fra') if imgs else ""
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as s:
                try:
                    return s.submit(_do).result(timeout=15)
                except Exception as e:
                    logger.error(f"Repérage page {page_num}: {e}")
                    return ""

        # PHASE 1 : Repérage léger en parallèle
        pages_luminaires = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            light_results = list(ex.map(ocr_light, range(1, total_pages + 1)))

        for i, txt in enumerate(light_results):
            if luminaire_keywords.search(txt):
                pages_luminaires.append(i + 1)

        logger.info(f"CPC: {len(pages_luminaires)} pages luminaires repérées sur {total_pages} : {pages_luminaires}")

        # Si aucune page repérée, prendre tout (fallback) mais limité
        if not pages_luminaires:
            logger.warning("CPC: aucune page luminaire repérée")
            pages_luminaires = list(range(1, min(total_pages, 30) + 1))

        # PHASE 2 : OCR qualité SEULEMENT sur les pages luminaires
        def ocr_quality(page_num):
            def _do():
                imgs = convert_from_path(file_path, dpi=200,
                        first_page=page_num, last_page=page_num)
                return pytesseract.image_to_string(imgs[0], lang='fra') if imgs else ""
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as s:
                try:
                    txt = s.submit(_do).result(timeout=25)
                    logger.info(f"CPC OCR qualité page {page_num} OK")
                    return txt
                except Exception as e:
                    logger.error(f"OCR qualité page {page_num}: {e}")
                    return ""

        full_text = ""
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            quality_results = list(ex.map(ocr_quality, pages_luminaires))
        full_text = "\n".join(quality_results)

        logger.info("CPC: OCR ciblé terminé")
        return full_text

    def process_pdf(self, file_path: str) -> List[ExtractedItem]:
        from pypdf import PdfReader
        try:
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
        except Exception as e:
            logger.error(f"Lecture PDF impossible: {e}")
            raise ValueError("PDF illisible ou corrompu.")
        
        logger.info(f"CPC: {total_pages} pages par pypdf")

        # Détecter scanné via échantillon (pages 1, milieu, fin)
        sample_pages = [0, total_pages // 2, total_pages - 1]
        sample_text = ""
        for idx in sample_pages:
            if idx < total_pages:
                try:
                    sample_text += (reader.pages[idx].extract_text() or "")
                except Exception:
                    pass

        is_scanned = len(sample_text.strip()) < 100
        logger.info(f"CPC: is_scanned={is_scanned}")

        if is_scanned:
            if total_pages > 400:
                raise ValueError(
                    f"Document scanné de {total_pages} pages. Maximum 400 pages "
                    f"pour le traitement OCR. Fournissez le chapitre concerné."
                )
            if OCR_AVAILABLE:
                full_text = self._process_scanned(file_path, total_pages)
            else:
                raise ValueError("OCR non disponible sur le serveur.")
        else:
            full_text = self._process_native(reader, total_pages)

        if not self.bpu_memory:
            self._extract_bpu_from_text_fallback(full_text)

        logger.info("CPC: regex split...")
        return self._extract_luminaires(full_text)

    def process_word(self, file_path: str) -> List[ExtractedItem]:
        doc = docx.Document(file_path)
        full_text = "\n".join([p.text for p in doc.paragraphs if p.text])
        for table in doc.tables:
            data = [[cell.text for cell in row.cells] for row in table.rows]
            if len(data) > 1:
                df = pd.DataFrame(data[1:], columns=data[0])
                self._extract_bpu_from_dataframe(df)
        if not self.bpu_memory: self._extract_bpu_from_text_fallback(full_text)
        return self._extract_luminaires(full_text)

    def process_excel(self, file_path: str) -> List[ExtractedItem]:
        try:
            xls = pd.ExcelFile(file_path)
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                self._extract_bpu_from_dataframe(df)
        except Exception as e:
            logger.error(f"OmniExtractor erreur: {e}", exc_info=True)
        return []
