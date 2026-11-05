# Cartographie facile

Copyright (C) 2026 Mamadou Thiam

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version. See [LICENSE](./LICENSE).

Short English description: Cartographie facile helps QGIS users compose
print-ready map layouts from project layers and export them to PDF, PNG or SVG.

Extension pour QGIS 3.28 ou supérieur, créée par **Mamadou Thiam**.

## Objectif, méthode et avantages

**Cartographie facile** réduit le travail répétitif de préparation d'une mise en page. Elle ne remplace ni l'analyse SIG ni la vérification cartographique : elle aide à assembler les éléments courants d'une carte à partir des données déjà ouvertes dans QGIS.

La méthode est la suivante :

1. L'extension lit les couches vectorielles et raster du projet QGIS courant et reprend leurs styles.
2. Vous choisissez la couche principale, les couches de contexte, le SCR, le format et les options de mise en page.
3. L'extension construit une mise en page QGIS avec la carte et les éléments choisis.
4. Elle exporte cette mise en page en PDF et, si demandé, en PNG. La mise en page reste dans le projet pour être relue et modifiée.

Cela permet de gagner du temps, d'obtenir une présentation cohérente, de choisir parmi plusieurs formats et designs, et de garder le contrôle dans QGIS après la génération.

## Installation depuis un fichier ZIP

1. Dans QGIS, ouvrez **Extensions → Installer/Gérer les extensions…**.
2. Choisissez **Installer depuis un ZIP**.
3. Sélectionnez `cartographie_facile.zip`, puis confirmez l'installation.
4. Activez **Cartographie facile** dans la liste des extensions installées.

Si l'extension n'apparaît pas tout de suite, redémarrez QGIS.

Après publication et validation dans le dépôt officiel QGIS, recherchez **Cartographie facile**
dans **Extensions → Installer/Gérer les extensions…** pour l'installer directement, sans
télécharger le ZIP manuellement. La mise en ligne officielle doit d'abord être approuvée.

## Création d'une carte

1. Ouvrez votre projet QGIS et vérifiez les noms, styles et systèmes de coordonnées des couches.
2. Lancez **Extensions → Cartographie facile → Créer une carte…**.
3. Sélectionnez un modèle dans la liste et cliquez sur **Charger** pour appliquer ses réglages, ou choisissez vos options manuellement. Quatre modèles d'exemple sont inclus dès l'installation.
4. Choisissez où enregistrer le PDF, puis cliquez sur **Créer la carte**.
5. Si un PDF ou un PNG du même nom existe déjà, l'extension demande confirmation avant de le remplacer.

La mise en page est ajoutée au projet QGIS ouvert. Enregistrez le projet pour la conserver et la modifier plus tard. Les résolutions PDF et PNG sont configurables (300 et 180 dpi par défaut). Le fichier SVG est facultatif.

## Paramètres disponibles

- Couches principales et couches de contexte : vecteurs et rasters chargés dans le projet.
- Formats A4/A3 en paysage ou portrait.
- Huit designs : classique vert, moderne bleu, nature terre, épuré noir et blanc, métropole ardoise, océan turquoise, Sahel ocre et clair.
- Quatre modèles d'exemple sont disponibles dès l'installation : Atlas moderne, Thématique océan, Territoire du Sahel et Rapport épuré. Ils apparaissent dans la liste avec une étoile ; sélectionnez-en un et cliquez sur **Charger**. Le bouton **Supprimer** reste désactivé pour ces modèles intégrés.
- Modèles personnalisés sauvegardés dans les réglages QGIS de l'utilisateur : enregistrer, charger ou supprimer un ensemble de paramètres. Les modèles ne contiennent ni données, ni couches, ni chemin de sortie. Les modèles intégrés ne peuvent pas être supprimés.
- Personnalisation de la police, de la couleur d'accent et ajout d'un logo PNG, JPG ou SVG.
- Emprise calculée depuis les couches sélectionnées, la couche principale ou la vue actuelle du canevas.
- Marge autour de l'emprise et échelle d'impression fixe facultative.
- Légende, flèche nord, échelle graphique et grille de coordonnées activables séparément.
- Option pour conserver ou masquer les étiquettes dans la mise en page sans changer les réglages des couches du projet.
- Unités de l'échelle en kilomètres, mètres, miles ou pieds.
- Pas du quadrillage exprimé dans les unités du SCR : les mètres pour un SCR projeté, les degrés pour un SCR géographique.
- Aperçu de la carte avant export, annulable sans produire les fichiers finaux.
- Export PDF, aperçu PNG et fichier SVG facultatifs, avec résolution réglable.

La légende utilise les symboles et catégories du style QGIS courant. Pour une légende par classes, appliquez d'abord une symbologie catégorisée ou graduée dans QGIS. La somme d'un champ numérique n'est utile que si ses unités sont connues et homogènes. Pour un raster à SCR mal attribué, corrigez son SCR dans QGIS avant de créer la carte.

L'extension propose plusieurs mises en page générales, et non une composition spécialisée pour chaque métier. Relisez le SCR, l'intervalle de grille, les sources, la légende, l'échelle et le contenu avant de diffuser ou d'imprimer la carte.

## Protection et limites

- L'extension fonctionne localement dans QGIS : elle n'envoie pas de données sur Internet et ne lance pas de commandes externes.
- Elle produit des fichiers PDF/PNG/SVG ; elle n'édite pas les géométries ni les fichiers des couches sources.
- Elle refuse de créer un export au même emplacement que le fichier du projet ou celui d'une couche locale du projet.
- Si un export PDF, PNG ou SVG existe déjà, elle demande une confirmation avant son remplacement.
- Les fichiers sont préparés temporairement dans le dossier choisi, puis publiés une fois l'export réussi. En cas d'erreur, un message explique le problème.
- Les emprises de couches et du canevas sont vérifiées avant de calculer l'échelle ; les coordonnées `NaN` ou infinies déclenchent un message indiquant de vérifier les couches et leur SCR.
- Vérifiez les données, le SCR, les unités, les sources et la lisibilité de la carte avant de l'utiliser comme document officiel.
