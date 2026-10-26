# Système de Reconnaissance de Plaques d'Immatriculation Tunisiennes

Ce projet implémente un pipeline de vision par ordinateur pour détecter et lire les plaques d'immatriculation tunisiennes à partir d'images de véhicules. Il combine la puissance de **YOLOv8** pour la détection d'objets et des **modèles de langage visuels (VLM)** via l'API Groq pour une reconnaissance de texte précise et structurée.

## 🚀 Pipeline du Projet

Le traitement d'une image suit les étapes suivantes :

1.  **Entrée** : Une image contenant un véhicule (formats supportés : jpg, png, webp, etc.).
2.  **Détection (YOLOv8)** :
    *   Le modèle YOLO (`best-1 (1).pt`) analyse l'image globale.
    *   Il localise la plaque d'immatriculation et génère une "bounding box".
    *   L'image est rognée (cropped) autour de la plaque détectée.
3.  **Encodage** :
    *   L'image rognée de la plaque est convertie en format Base64.
4.  **Reconnaissance (VLM - Groq)** :
    *   L'image encodée est envoyée à l'API Groq (modèle `llama-4-scout` ou équivalent vision).
    *   Un prompt spécifique demande au modèle d'analyser l'image, d'extraire le texte et de classer la plaque selon les formats tunisiens (TN, RS, GV).
5.  **Sortie** :
    *   Le système retourne un objet JSON structuré contenant le numéro lu, le type de plaque et le score de confiance.

## 📋 Prérequis

*   Python 3.8+
*   Une clé API Groq (gratuite en bêta ou payante).

### Installation des dépendances

```bash
pip install -r requirements.txt
```

*Contenu de `requirements.txt` :*
*   `ultralytics` (YOLO)
*   `opencv-python` (Traitement d'image)
*   `numpy`
*   `groq` (Client API VLM)

## ⚙️ Configuration

Le script utilise par défaut une clé API de démonstration ou celle configurée dans le code. Pour une utilisation en production, passez votre propre clé en argument.

## 💻 Utilisation

Exécutez le script principal en ligne de commande :

```bash
python license_plate_recognizer.py <chemin_image> [--api_key VOTRE_CLE_GROQ] [--model CHEMIN_MODELE_YOLO]
```

### Exemples

**Utilisation simple :**
```bash
python license_plate_recognizer.py img/voiture.jpg
```

**Avec une clé API spécifique :**
```bash
python license_plate_recognizer.py img/voiture.jpg --api_key gsk_VotreCleApi...
```

## 📦 Structure de la Sortie (JSON)

Le script affiche le résultat au format JSON standardisé :

```json
{
  "plate_text": "123 تونس 4567",    // Le texte normalisé lu sur la plaque
  "plate_type": "TN",               // Type : TN (Standard), RS, GV, ou Unknown
  "confidence": 0.95,               // Confiance estimée par le modèle VLM
  "plate_detected": true,           // Si une plaque a été trouvée par YOLO
  "yolo_confidence": 0.88           // Confiance de la détection YOLO
}
```

## 🗂 Structure du Projet

*   `license_plate_recognizer.py` : Script principal contenant la classe `LicensePlateRecognizer` et la logique du pipeline.
*   `best-1 (1).pt` : Poids du modèle YOLO entraîné pour détecter les plaques.
*   `requirements.txt` : Liste des librairies Python nécessaires.
*   `img/` : Dossier contenant des images de test.
