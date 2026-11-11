# 📋 Master Development Roadmap & Project Supervision

> **Project Name:** Engine_lighting (LAE Substitution Engine)  
> **Architecture:** Multi-Agent Swarm (4 Specialized Agents) + AI Harness + Market Packs + Fullstack Dashboard

---

## 🧭 BLOC 1 : L'Essaim des 4 Agents IA & l'AI Harness

- [x] **Tâche 1 : Agent 1 — Document Analysis & Triage Agent (`analysis_agent.py`)**
  - **Statut :** ✅ Validé sur CPS de 316 pages (Berkane). Triage en 4.09 secondes, élimination de 227 pages hors-sujet (-72% de charge).
  - Cascade à 4 niveaux (Bookmarks natifs $\to$ Sommaire/TOC $\to$ Scan d'en-têtes $\to$ Fallback sécurisé).
- [x] **Tâche 2 : Agent 2 — Retrieval & Evidence Agent (`retrieval_agent.py`)**
  - **Statut :** ✅ Validé sur AO Publics (Berkane 316 p.) et AO Privés (Hilton Rabat 6 p.).
  - Détection multi-formats (fiches unitaires en tableaux/grilles, listes tabulaires, découpage par articles/prix).
  - Scellement de preuve documentaire : attachement du numéro de page exact (`page_number`) certifié à chaque luminaire (`📍 p.X`).
- [x] **Tâche 3 : Agent 3 — Extraction Agent avec SLM Local (`extraction_agent.py`)**
  - **Statut :** ✅ Validé localement sur Qwen 2.5:3b (Ollama) en 1.23 seconde par luminaire, contexte borné (`num_ctx: 2048`), température `0.0`.
  - 25/25 tests unitaires passés.
- [x] **Tâche 4 : Agent 4 — Validation & Reflection Agent (`validation_agent.py`)**
  - **Statut :** ✅ Validé localement.
  - Vérification des règles physiques fondamentales : ratio $lm/W \in [25, 250]$, CCT $\in [1800K, 10000K]$, CRI $\in [50, 100]$, formats IP/IK.
  - Arbitrage à 3 états : `AUTO_ACCEPTED`, `TEACHER_CORRECTED`, `HUMAN_REVIEW`. Retry réflexif borné à 2 tentatives.
- [x] **Tâche 5 : AI Harness & Orchestration Globale (`harness.py`)**
  - **Statut :** ✅ Validé localement. Machine à états : `IDLE` $\to$ `TRIAGING` $\to$ `RETRIEVING` $\to$ `EXTRACTING` $\to$ `VALIDATING` $\to$ `COMPLETED`.
  - Timeout strict de 15 secondes par bloc avec bascule de secours. Spans de télémétrie (`TelemetrySpan`).

---

## 🌍 BLOC 2 : Market Packs & Généralisation Internationale

- [x] **Market Pack Maroc (`MA`) :** Isolation du premier pack déclaratif (termes CCAG-T, CPS, 230V, métrique, MAD).
- [ ] **Market Pack France (`FR`) :** DPGF/CCTP, norme NF EN 12464-1, EN 13201, EUR.
- [ ] **Market Pack Anglophone / US (`US`) :** Schedule 26 51 00, 120-277V, foot-candles, Title 24, UL/DLC.
- [ ] **Couche de normalisation d'unités automatique :** Conversion lux $\leftrightarrow$ foot-candles, mm $\leftrightarrow$ pouces, tension réseau.

---

## 📦 BLOC 3 : Catalogue Multi-Tenant & Moteur de Substitution

- [ ] **Tâche 7 : Ingestion & Indexation Multi-Tenant du Catalogue (`catalog_importer.py`)**
  - Import Excel/CSV par client/distributeur avec cloisonnement strict des données (`tenant_id`).
  - Indexation des attributs : famille, lumens, watts, CCT, IP, IK, prix d'achat, stock, marge.
  - Objectif : Requête catalogue en moins de 5 millisecondes.
- [ ] **Tâche 8 : Moteur de Substitution & Matching Multicritères (`matching/`)**
  - *Hard Filter :* Élimination des produits incompatibles (IP insuffisant, tolérance flux $\pm 30\%$, tension, montage).
  - *Soft Scoring :* Classement par efficacité $lm/W$, fidélité des couleurs (CRI), cohérence CCT.
  - *Business Overlay :* Optimisation de la marge commerciale et pénalité sur stock critique.
  - *Checklist de conformité :* Extraction des certificats requis (CE, ENEC, attestations IP/IK).

---

## 🖥️ BLOC 4 : Interface Utilisateur, Evidence & Observabilité

- [ ] **Tâche 6 : Affichage de l'Evidence & Trace d'un Upload (Frontend Next.js)**
  - Frise chronologique d'exécution des agents : Triage $\to$ Retrieval $\to$ Extraction $\to$ Validation $\to$ Matching.
  - Affichage de la page source certifiée (`📍 p.X`), du badge d'origine (`🤖 Qwen Local` vs `⚡ Escaladé Groq`) et de l'extrait de preuve.
- [ ] **Tâche 9 : Matrice de Comparaison Visuelle & Sélection**
  - Écran de sélection `/line/[id]` présentant le luminaire demandé face aux 3 à 5 équivalents du catalogue.
  - Calcul en direct des watts économisés, des écarts de specs et du bilan carbone $\text{CO}_2e$.

---

## 📊 BLOC 5 : Restitution Commerciale & Boucle Active Learning

- [ ] **Tâche 10 : Générateur de Livrables (BOM Excel & Dossier PDF)**
  - Exportation du bordereau chiffré Excel (références, quantités, prix unitaire, marge totale).
  - Génération du rapport technique PDF avec fiches de conformité côte-à-côte.
- [ ] **Tâche 11 : Boucle d'Auto-Amélioration (Active Learning Flywheel)**
  - Persistance des corrections d'estimateurs dans `extraction_feedback`.
  - Script d'exportation `dataset_exporter.py` en JSONL pour le fine-tuning LoRA sur petits modèles spécialisés.
