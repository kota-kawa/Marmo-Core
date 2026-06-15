# Vibe_OS Design System (v2.0)

## 1. Philosophie & Identité
**Concept :** "Cockpit Mode" / Technical Precision.
L'interface est conçue comme un outil de pilotage professionnel. Elle privilégie la densité d'information, la précision des contrôles et une esthétique futuriste et industrielle.

**Paramètres Fondamentaux :**
*   **DESIGN_VARIANCE: 2** (Symétrie, Structure rigide, Alignement parfait)
*   **MOTION_INTENSITY: 5** (Transitions fluides "Physique", Réactif, Pas de distractions inutiles)
*   **VISUAL_DENSITY: 8** (Haute densité, Pas de cartes "aérées", Séparateurs fins, Information compacte)

---

## 2. Palette de Couleurs (Mode Sombre Natif)

| Usage | Couleur | Hex | Notes |
| :--- | :--- | :--- | :--- |
| **Fond Global** | Ultra Black | `#050505` | Pas de noir absolu (#000), mais très profond. |
| **Surfaces** | Technical Black | `#0a0a0a` | Pour les headers, sidebars. Souvent avec `backdrop-blur`. |
| **Bordures** | Dark Grey | `#171717` | Structure principale. |
| **Séparateurs** | Soft Grey | `#262626` | Pour diviser les sections internes. |
| **Texte Principal** | Off-White | `#e5e5e5` | Jamais de blanc pur (#fff) pour éviter la fatigue oculaire. |
| **Texte Secondaire** | Muted Grey | `#737373` | Pour les labels et sous-titres. |
| **Accent Actif** | Indigo | `#6366f1` | Indicateurs d'état, curseurs, boutons primaires. |
| **Accent Danger** | Red | `#ef4444` | Actions destructives. |

---

## 3. Typographie

*   **Police Principale (UI) :** `Inter` (Sans-serif) - Utilisé pour le contenu général.
*   **Police Technique (Data/Labels) :** `Monospace` (ex: `ui-monospace`, `SFMono-Regular`) - **CRUCIAL**.
    *   Utilisation obligatoire pour : Titres de sections, Valeurs numériques, Boutons d'action, Labels de sliders.
    *   Style : `uppercase`, `tracking-widest`, `text-[10px]` ou `text-xs`.

---

## 4. Composants & Géométrie

### Formes
*   **Rayons (Radius) :** Strictement `rounded-none` ou `rounded-sm` (max 2-4px). Pas de `rounded-xl` ou `rounded-2xl` "doux".
*   **Coins "Coupés" :** Utilisation de `clip-path` pour les boutons d'action principaux (effet sci-fi).
*   **Bordures :** Fines (1px). Pas d'ombres portées diffuses (`box-shadow`). Privilégier les bordures ou les "Glows" internes.

### Sliders (Contrôles)
*   **Track :** Ligne fine (2px), couleur sombre `#333`.
*   **Thumb :** Rectangulaire ou très petit (4px x 12px), couleur Accent.
*   **Interaction :** Agrandissement vertical au survol (`scaleY`).

### Boutons
*   **Style :** Ghost (Transparent avec Bordure) ou Flat (Aplat couleur).
*   **Hover :** Remplissage progressif ou soulignement animé (`width: 0% -> 100%`).
*   **Feedback :** `active:scale-[0.98]` pour un retour tactile.

### Conteneurs
*   **Pas de "Cartes" :** Éviter les blocs flottants avec ombres.
*   **Grilles :** Utiliser des grilles délimitées par des bordures (`border-r`, `border-b`) pour structurer l'espace.
*   **Background :** Motif de grille technique (`bg-grid-pattern`) pour les zones vides.

---

## 5. Mouvement & Interaction

*   **Courbe d'animation :** `cubic-bezier(0.16, 1, 0.3, 1)` (Fluide, départ rapide, atterrissage doux).
*   **Durée :** Rapide (~150ms - 300ms).
*   **Type :**
    *   Micro-interactions au survol (opacité, couleur, échelle légère).
    *   Apparition des panneaux latéraux par glissement (`slide-in`).

---

## 6. Règles d'Implémentation pour Nouvelles Fonctionnalités

Pour toute nouvelle fonctionnalité ajoutée à Vibe_OS, suivez ces règles :

1.  **Structure :** N'ajoutez pas de `padding` excessif. Compactez l'information.
2.  **Labels :** Tous les labels doivent être en `font-mono`, `uppercase`, `text-[10px]`.
3.  **Inputs :** Les champs de saisie (text/number) doivent ressembler à des terminaux (fond transparent, soulignement ou bordure fine, font-mono).
4.  **Icônes :** Utilisez `lucide-react` avec une taille petite (`size={14}` ou `{16}`).
5.  **Markers :** Si vous créez une zone de visualisation, ajoutez des "Corner Markers" (coins techniques) pour encadrer le contenu.

---

*Généré par Vibe_OS System Architect.*
