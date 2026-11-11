# Ingestion Avancée : Camelot + Ollama

## Architecture
Le pipeline d'ingestion avancé (activé pour les PDF > 50 pages) s'appuie sur une combinaison d'heuristiques classiques et d'intelligence sémantique locale.

### 1. Tableaux via Camelot
Les bibliothèques classiques peinent sur les tableaux sans bordures ou avec des fusions complexes. Camelot-py en mode `stream` ou `lattice` permet une extraction très fiable des données structurées.

### 2. Sémantique via Ollama (Local LLM)
Les données non tabulaires (paragraphes descriptifs) sont découpées et passées à un modèle LLM local (ex: `llama3.1:8b`) tournant via l'API REST Ollama.
Le prompt système (défini dans `prompts.py`) contraint le modèle à produire un JSON strict correspond aux attributs du `Project Requirement Object (PRO)`.

## Workflow de Feedback (Human in the Loop)
Pour éviter les hallucinations :
1. **Extraction** : L'API `/uploads` crée les lignes avec un statut `draft` et stocke le niveau de confiance (llm, table).
2. **Review** : Le frontend (page `/review/[id]`) affiche ces lignes. L'utilisateur peut modifier les champs erronés.
3. **Confirmation** : Lors de la soumission (`/confirm`), les modifications manuelles sont enregistrées dans la table SQL `extraction_feedback` pour apprentissage futur, et le workflow asynchrone LangGraph est enfin déclenché.

## Robustesse
Le `OllamaClient` inclut un retry avec backoff exponentiel. Si Ollama n'est pas joignable (serveur arrêté), le pipeline renvoie un dictionnaire vide et le pipeline global ne plante pas.
