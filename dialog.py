from datetime import datetime
import json
import math
import os
from pathlib import Path
import tempfile

from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtGui import QColor, QFont, QPixmap
from qgis.PyQt.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QInputDialog,
    QFontComboBox,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QDoubleSpinBox,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFillSymbol,
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsLayoutItemPicture,
    QgsLayoutItemScaleBar,
    QgsLayoutItemShape,
    QgsLayoutMeasurement,
    QgsLayoutItemMapGrid,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsMapLayer,
    QgsPrintLayout,
    QgsProject,
    QgsProviderRegistry,
    QgsRasterLayer,
    QgsRectangle,
    QgsUnitTypes,
    QgsVectorLayer,
)


class CartographieDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.project = QgsProject.instance()
        self._pas_grille_personnalise = False
        self.setWindowTitle("Cartographie facile — Composer une carte")
        self.setMinimumWidth(560)
        self.setModal(False)
        self._construire_interface()
        self._actualiser_couches()
        self._ajuster_taille_fenetre()

    def _construire_interface(self):
        racine = QVBoxLayout(self)
        contenu = QWidget()
        layout = QVBoxLayout(contenu)
        intro = QLabel(
            "Choisissez une couche principale et les couches de contexte du projet ouvert. "
            "L'extension crée une mise en page et exporte un PDF et, si demandé, un aperçu PNG."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        modeles_layout = QHBoxLayout()
        self.modele = QComboBox()
        self.modele.setMinimumContentsLength(18)
        bouton_enregistrer_modele = QPushButton("Enregistrer")
        bouton_enregistrer_modele.clicked.connect(self._enregistrer_modele)
        bouton_charger_modele = QPushButton("Charger")
        bouton_charger_modele.clicked.connect(self._charger_modele)
        self.bouton_supprimer_modele = QPushButton("Supprimer")
        self.bouton_supprimer_modele.clicked.connect(self._supprimer_modele)
        self.modele.currentIndexChanged.connect(self._mettre_a_jour_bouton_supprimer)
        modeles_layout.addWidget(QLabel("Modèle :"))
        modeles_layout.addWidget(self.modele, 1)
        modeles_layout.addWidget(bouton_enregistrer_modele)
        modeles_layout.addWidget(bouton_charger_modele)
        modeles_layout.addWidget(self.bouton_supprimer_modele)
        layout.addLayout(modeles_layout)
        aide_modeles = QLabel(
            "Des modèles d’exemple sont inclus. Vos modèles gardent les réglages, "
            "pas les couches ni le chemin d’export."
        )
        aide_modeles.setWordWrap(True)
        layout.addWidget(aide_modeles)
        self._actualiser_modeles()

        formulaire = QFormLayout()
        self.couche_principale = QComboBox()
        formulaire.addRow("Couche principale :", self.couche_principale)

        self.champs_statistiques = QComboBox()
        self.champs_statistiques.addItem("Ne pas afficher de somme", "")
        formulaire.addRow("Champ numérique à sommer (facultatif) :", self.champs_statistiques)

        self.titre = QLineEdit("Carte thématique")
        formulaire.addRow("Titre :", self.titre)
        self.sous_titre = QLineEdit()
        self.sous_titre.setPlaceholderText("Sous-titre ou zone étudiée (facultatif)")
        formulaire.addRow("Sous-titre :", self.sous_titre)
        self.sources = QLineEdit("Sources : données du projet QGIS")
        formulaire.addRow("Sources :", self.sources)
        self.crs = QLineEdit()
        self.crs.setPlaceholderText("Ex. EPSG:32631")
        formulaire.addRow("SCR de la carte :", self.crs)
        self.format_page = QComboBox()
        self.format_page.addItem("A4 — paysage", ("A4", "landscape"))
        self.format_page.addItem("A3 — paysage", ("A3", "landscape"))
        self.format_page.addItem("A4 — portrait", ("A4", "portrait"))
        self.format_page.addItem("A3 — portrait", ("A3", "portrait"))
        formulaire.addRow("Format :", self.format_page)
        self.design = QComboBox()
        self.design.addItem("Classique — vert", "classic")
        self.design.addItem("Moderne — bleu", "modern")
        self.design.addItem("Nature — terre", "nature")
        self.design.addItem("Épuré — noir et blanc", "minimal")
        self.design.addItem("Métropole — ardoise", "metro")
        self.design.addItem("Océan — turquoise", "ocean")
        self.design.addItem("Sahel — ocre", "sahel")
        self.design.addItem("Clair — contraste doux", "light")
        formulaire.addRow("Design :", self.design)
        self.police = QFontComboBox()
        formulaire.addRow("Police :", self.police)
        self.couleur_accent = ""
        self.bouton_couleur = QPushButton("Choisir une couleur d’accent…")
        self.bouton_couleur.clicked.connect(self._choisir_couleur_accent)
        formulaire.addRow("Couleur :", self.bouton_couleur)
        self.emprise = QComboBox()
        self.emprise.addItem("Toutes les couches sélectionnées", "selected")
        self.emprise.addItem("Couche principale seulement", "main")
        self.emprise.addItem("Vue actuelle du canevas QGIS", "canvas")
        formulaire.addRow("Emprise de la carte :", self.emprise)
        self.unites_echelle = QComboBox()
        self.unites_echelle.addItem("Kilomètres", QgsUnitTypes.DistanceKilometers)
        self.unites_echelle.addItem("Mètres", QgsUnitTypes.DistanceMeters)
        self.unites_echelle.addItem("Miles", QgsUnitTypes.DistanceMiles)
        self.unites_echelle.addItem("Pieds", QgsUnitTypes.DistanceFeet)
        formulaire.addRow("Unités de l'échelle :", self.unites_echelle)
        self.marge_emprise = QDoubleSpinBox()
        self.marge_emprise.setDecimals(1)
        self.marge_emprise.setRange(0, 100)
        self.marge_emprise.setValue(8)
        self.marge_emprise.setSuffix(" %")
        formulaire.addRow("Marge autour de l'emprise :", self.marge_emprise)
        self.echelle_fixe = QCheckBox("Imposer une échelle d'impression")
        self.denominateur_echelle = QSpinBox()
        self.denominateur_echelle.setRange(100, 100000000)
        self.denominateur_echelle.setSingleStep(5000)
        self.denominateur_echelle.setValue(25000)
        self.denominateur_echelle.setPrefix("1 : ")
        echelle_fixe_layout = QHBoxLayout()
        echelle_fixe_layout.addWidget(self.echelle_fixe)
        echelle_fixe_layout.addWidget(self.denominateur_echelle)
        formulaire.addRow("Échelle de la carte :", echelle_fixe_layout)
        self.echelle_fixe.toggled.connect(self.denominateur_echelle.setEnabled)
        self.denominateur_echelle.setEnabled(False)
        self.exporter_png = QCheckBox("Créer aussi un aperçu PNG")
        self.exporter_png.setChecked(True)
        formulaire.addRow("Image :", self.exporter_png)
        self.exporter_svg = QCheckBox("Créer aussi un fichier SVG")
        self.exporter_svg.setChecked(False)
        formulaire.addRow("SVG :", self.exporter_svg)
        self.apercu_avant_export = QCheckBox("Afficher un aperçu avant l’export")
        self.apercu_avant_export.setChecked(True)
        formulaire.addRow("Aperçu :", self.apercu_avant_export)
        self.resolution_pdf = QSpinBox()
        self.resolution_pdf.setRange(72, 1200)
        self.resolution_pdf.setValue(300)
        self.resolution_pdf.setSuffix(" dpi")
        formulaire.addRow("Résolution du PDF :", self.resolution_pdf)
        self.resolution_png = QSpinBox()
        self.resolution_png.setRange(72, 600)
        self.resolution_png.setValue(180)
        self.resolution_png.setSuffix(" dpi")
        formulaire.addRow("Résolution du PNG :", self.resolution_png)
        self.exporter_png.toggled.connect(self.resolution_png.setEnabled)
        self.resolution_png.setEnabled(self.exporter_png.isChecked())
        self.afficher_etiquettes = QCheckBox("Afficher les étiquettes des couches")
        self.afficher_etiquettes.setChecked(True)
        formulaire.addRow("Étiquettes :", self.afficher_etiquettes)
        layout.addLayout(formulaire)

        options = QHBoxLayout()
        self.afficher_legende = QCheckBox("Légende")
        self.afficher_legende.setChecked(True)
        options.addWidget(self.afficher_legende)
        self.afficher_nord = QCheckBox("Flèche nord")
        self.afficher_nord.setChecked(True)
        options.addWidget(self.afficher_nord)
        self.afficher_echelle = QCheckBox("Échelle graphique")
        self.afficher_echelle.setChecked(True)
        options.addWidget(self.afficher_echelle)
        self.afficher_grille = QCheckBox("Grille de coordonnées")
        self.afficher_grille.setChecked(False)
        options.addWidget(self.afficher_grille)
        layout.addLayout(options)

        self.intervalle_grille = QDoubleSpinBox()
        self.intervalle_grille.setDecimals(4)
        self.intervalle_grille.setRange(0.0001, 10000000)
        self.intervalle_grille.setValue(10000)
        self.intervalle_grille.setSingleStep(1000)
        self.intervalle_grille.setToolTip(
            "Pas de la grille dans l'unité du système de coordonnées choisi."
        )
        formulaire.addRow(
            "Pas de la grille (mètres ou degrés) :", self.intervalle_grille
        )
        self.afficher_grille.toggled.connect(self.intervalle_grille.setEnabled)
        self.intervalle_grille.valueChanged.connect(
            lambda _value: setattr(self, "_pas_grille_personnalise", True)
        )
        self.crs.textChanged.connect(self._mettre_a_jour_pas_grille)
        self.intervalle_grille.setEnabled(False)

        layout.addWidget(QLabel("Couches de contexte à afficher (décochez celles à exclure) :"))
        self.couches_contexte = QListWidget()
        self.couches_contexte.setMinimumHeight(140)
        layout.addWidget(self.couches_contexte)

        bouton_actualiser = QPushButton("Actualiser les couches du projet")
        bouton_actualiser.clicked.connect(self._actualiser_couches)
        layout.addWidget(bouton_actualiser)

        choix_logo = QHBoxLayout()
        self.chemin_logo = QLineEdit()
        self.chemin_logo.setPlaceholderText("Logo facultatif (PNG, JPG ou SVG)…")
        bouton_logo = QPushButton("Choisir un logo…")
        bouton_logo.clicked.connect(self._choisir_logo)
        choix_logo.addWidget(self.chemin_logo, 1)
        choix_logo.addWidget(bouton_logo)
        layout.addLayout(choix_logo)

        choix_fichier = QHBoxLayout()
        self.chemin_pdf = QLineEdit()
        self.chemin_pdf.setPlaceholderText("Choisissez où enregistrer la carte PDF…")
        bouton_parcourir = QPushButton("Parcourir…")
        bouton_parcourir.clicked.connect(self._choisir_pdf)
        choix_fichier.addWidget(self.chemin_pdf, 1)
        choix_fichier.addWidget(bouton_parcourir)
        layout.addLayout(choix_fichier)

        self.zone_defilante = QScrollArea(self)
        self.zone_defilante.setWidgetResizable(True)
        self.zone_defilante.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.zone_defilante.setWidget(contenu)
        racine.addWidget(self.zone_defilante, 1)

        boutons = QDialogButtonBox(QDialogButtonBox.Close)
        self.bouton_creer = boutons.addButton("Créer la carte", QDialogButtonBox.AcceptRole)
        self.bouton_creer.clicked.connect(self._creer_carte)
        boutons.rejected.connect(self.close)
        racine.addWidget(boutons)

        self.couche_principale.currentIndexChanged.connect(self._couche_principale_changee)

    @staticmethod
    def _lire_modeles():
        valeur = QSettings().value("CartographieFacile/modeles", "{}")
        if isinstance(valeur, dict):
            return valeur
        try:
            modeles = json.loads(str(valeur))
        except (TypeError, ValueError) as error:
            raise ValueError(f"Les modèles enregistrés sont illisibles : {error}") from error
        if not isinstance(modeles, dict):
            raise ValueError("Le fichier des modèles n’a pas un format valide.")
        return modeles

    @staticmethod
    def _modeles_integres():
        return {
            "Atlas moderne": {
                "format": ["A4", "landscape"], "design": "metro", "margin": 8,
                "units": QgsUnitTypes.DistanceKilometers, "labels": True,
                "show_legend": True, "show_north": True, "show_scale": True,
                "show_grid": False, "export_png": True, "export_svg": False,
                "preview": True, "pdf_dpi": 300, "png_dpi": 180,
            },
            "Thématique océan": {
                "format": ["A4", "landscape"], "design": "ocean", "margin": 8,
                "units": QgsUnitTypes.DistanceKilometers, "labels": True,
                "show_legend": True, "show_north": True, "show_scale": True,
                "show_grid": True, "grid_interval": 10000, "export_png": True,
                "export_svg": False, "preview": True, "pdf_dpi": 300, "png_dpi": 180,
            },
            "Territoire du Sahel": {
                "format": ["A3", "landscape"], "design": "sahel", "margin": 10,
                "units": QgsUnitTypes.DistanceKilometers, "labels": True,
                "show_legend": True, "show_north": True, "show_scale": True,
                "show_grid": False, "export_png": True, "export_svg": False,
                "preview": True, "pdf_dpi": 300, "png_dpi": 180,
            },
            "Rapport épuré": {
                "format": ["A4", "portrait"], "design": "minimal", "margin": 5,
                "units": QgsUnitTypes.DistanceKilometers, "labels": True,
                "show_legend": True, "show_north": False, "show_scale": True,
                "show_grid": False, "export_png": True, "export_svg": False,
                "preview": True, "pdf_dpi": 300, "png_dpi": 180,
            },
        }

    def _actualiser_modeles(self, selection=None):
        try:
            modeles_enregistres = self._lire_modeles()
        except ValueError as error:
            self._afficher_erreur("Modèles illisibles", str(error))
            modeles_enregistres = {}
        modeles_integres = self._modeles_integres()
        noms = sorted(
            set(modeles_integres) | set(modeles_enregistres),
            key=str.casefold,
        )
        self.modele.blockSignals(True)
        self.modele.clear()
        for nom in noms:
            etiquette = f"★ {nom}" if nom in modeles_integres else nom
            self.modele.addItem(etiquette, nom)
        if selection:
            index = self.modele.findData(selection)
            if index >= 0:
                self.modele.setCurrentIndex(index)
        elif self.modele.count():
            self.modele.setCurrentIndex(0)
        self.modele.blockSignals(False)
        self._mettre_a_jour_bouton_supprimer()

    def _mettre_a_jour_bouton_supprimer(self, _index=None):
        nom = self.modele.currentData()
        self.bouton_supprimer_modele.setEnabled(
            bool(self.modele.currentData())
            and nom not in self._modeles_integres()
        )

    def _options_modele(self):
        return {
            "title": self.titre.text(),
            "subtitle": self.sous_titre.text(),
            "sources": self.sources.text(),
            "crs": self.crs.text(),
            "format": list(self.format_page.currentData()),
            "design": self.design.currentData(),
            "font": self.police.currentFont().family(),
            "accent": self.couleur_accent,
            "extent": self.emprise.currentData(),
            "units": self.unites_echelle.currentData(),
            "margin": self.marge_emprise.value(),
            "fixed_scale": self.echelle_fixe.isChecked(),
            "scale": self.denominateur_echelle.value(),
            "statistics_field": self.champs_statistiques.currentData(),
            "export_png": self.exporter_png.isChecked(),
            "export_svg": self.exporter_svg.isChecked(),
            "preview": self.apercu_avant_export.isChecked(),
            "pdf_dpi": self.resolution_pdf.value(),
            "png_dpi": self.resolution_png.value(),
            "labels": self.afficher_etiquettes.isChecked(),
            "show_legend": self.afficher_legende.isChecked(),
            "show_north": self.afficher_nord.isChecked(),
            "show_scale": self.afficher_echelle.isChecked(),
            "show_grid": self.afficher_grille.isChecked(),
            "grid_interval": self.intervalle_grille.value(),
            "logo": self.chemin_logo.text(),
        }

    def _appliquer_options_modele(self, options):
        controles_texte = (
            ("title", self.titre), ("subtitle", self.sous_titre),
            ("sources", self.sources), ("crs", self.crs), ("logo", self.chemin_logo),
        )
        for cle, controle in controles_texte:
            if cle in options and isinstance(options[cle], str):
                controle.setText(options[cle])
        controles_choix = (
            ("format", self.format_page), ("design", self.design),
            ("extent", self.emprise), ("units", self.unites_echelle),
            ("statistics_field", self.champs_statistiques),
        )
        for cle, controle in controles_choix:
            if cle in options:
                valeur = options[cle]
                if cle == "format" and isinstance(valeur, list):
                    valeur = tuple(valeur)
                    index = next(
                        (
                            item_index for item_index in range(controle.count())
                            if controle.itemData(item_index) == valeur
                        ),
                        -1,
                    )
                else:
                    index = controle.findData(valeur)
                if index >= 0:
                    controle.setCurrentIndex(index)
        if isinstance(options.get("font"), str):
            self.police.setCurrentFont(QFont(options["font"]))
        if isinstance(options.get("accent"), str):
            self.couleur_accent = options["accent"]
            self._actualiser_couleur_accent()
        controles_cases = (
            ("fixed_scale", self.echelle_fixe), ("export_png", self.exporter_png),
            ("export_svg", self.exporter_svg), ("preview", self.apercu_avant_export),
            ("labels", self.afficher_etiquettes), ("show_legend", self.afficher_legende),
            ("show_north", self.afficher_nord), ("show_scale", self.afficher_echelle),
            ("show_grid", self.afficher_grille),
        )
        for cle, controle in controles_cases:
            if cle in options and isinstance(options[cle], bool):
                controle.setChecked(options[cle])
        controles_numeriques = (
            ("margin", self.marge_emprise), ("scale", self.denominateur_echelle),
            ("pdf_dpi", self.resolution_pdf), ("png_dpi", self.resolution_png),
            ("grid_interval", self.intervalle_grille),
        )
        for cle, controle in controles_numeriques:
            valeur = options.get(cle)
            if isinstance(valeur, (int, float)):
                controle.setValue(valeur)

    def _enregistrer_modele(self):
        nom, valide = QInputDialog.getText(self, "Enregistrer un modèle", "Nom du modèle :")
        nom = nom.strip()
        if not valide or not nom:
            return
        try:
            modeles = self._lire_modeles()
        except ValueError as error:
            self._afficher_erreur("Modèles illisibles", str(error))
            return
        if nom in self._modeles_integres():
            QMessageBox.warning(
                self, "Nom réservé",
                "Ce nom est réservé à un modèle intégré. Choisissez un autre nom.",
            )
            return
        if nom in modeles and QMessageBox.question(
            self, "Remplacer le modèle ?", f"Le modèle « {nom} » existe. Le remplacer ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        modeles[nom] = self._options_modele()
        QSettings().setValue(
            "CartographieFacile/modeles",
            json.dumps(modeles, ensure_ascii=False, separators=(",", ":")),
        )
        self._actualiser_modeles(nom)
        QMessageBox.information(self, "Modèle enregistré", f"Le modèle « {nom} » est enregistré.")

    def _charger_modele(self):
        nom = self.modele.currentData()
        if not nom:
            QMessageBox.information(self, "Aucun modèle", "Enregistrez d’abord un modèle.")
            return
        try:
            options = self._lire_modeles().get(nom)
            if options is None:
                options = self._modeles_integres().get(nom)
        except ValueError as error:
            self._afficher_erreur("Modèles illisibles", str(error))
            return
        if not isinstance(options, dict):
            self._afficher_erreur("Modèle invalide", f"Le modèle « {nom} » est incomplet.")
            return
        self._appliquer_options_modele(options)
        QMessageBox.information(self, "Modèle chargé", f"Les réglages « {nom} » sont appliqués.")

    def _supprimer_modele(self):
        nom = self.modele.currentData()
        if not nom:
            return
        if nom in self._modeles_integres():
            QMessageBox.information(
                self, "Modèle intégré",
                "Les modèles intégrés ne peuvent pas être supprimés.",
            )
            return
        if QMessageBox.question(
            self, "Supprimer le modèle ?", f"Supprimer le modèle « {nom} » ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            modeles = self._lire_modeles()
        except ValueError as error:
            self._afficher_erreur("Modèles illisibles", str(error))
            return
        modeles.pop(nom, None)
        QSettings().setValue(
            "CartographieFacile/modeles",
            json.dumps(modeles, ensure_ascii=False, separators=(",", ":")),
        )
        self._actualiser_modeles()

    def _choisir_logo(self):
        chemin, _ = QFileDialog.getOpenFileName(
            self, "Choisir un logo", self.chemin_logo.text(),
            "Images (*.png *.jpg *.jpeg *.svg);;Tous les fichiers (*)",
        )
        if chemin:
            self.chemin_logo.setText(chemin)

    def _choisir_couleur_accent(self):
        couleur = QColorDialog.getColor(QColor(self.couleur_accent or "#73874d"), self)
        if couleur.isValid():
            self.couleur_accent = couleur.name()
            self._actualiser_couleur_accent()

    def _actualiser_couleur_accent(self):
        if self.couleur_accent:
            self.bouton_couleur.setStyleSheet(
                f"background-color: {self.couleur_accent}; color: white;"
            )
        else:
            self.bouton_couleur.setStyleSheet("")

    def _confirmer_apercu(self, exportateur):
        descripteur, chemin = tempfile.mkstemp(
            prefix="cartographie_facile_apercu_", suffix=".png"
        )
        os.close(descripteur)
        os.unlink(chemin)
        try:
            reglages = QgsLayoutExporter.ImageExportSettings()
            reglages.dpi = min(90, self.resolution_png.value())
            resultat = exportateur.exportToImage(chemin, reglages)
            if resultat != QgsLayoutExporter.Success:
                raise RuntimeError(f"Échec du rendu de l’aperçu (code QGIS {resultat}).")
            image = QPixmap(chemin)
            if image.isNull():
                raise RuntimeError("QGIS a créé un aperçu illisible.")

            dialogue = QDialog(self)
            dialogue.setWindowTitle("Aperçu de la carte")
            disposition = QVBoxLayout(dialogue)
            ecran = self.screen() or QApplication.primaryScreen()
            zone = ecran.availableGeometry() if ecran else None
            largeur = min(image.width(), zone.width() - 80) if zone else image.width()
            hauteur = min(image.height(), zone.height() - 150) if zone else image.height()
            etiquette = QLabel()
            etiquette.setAlignment(Qt.AlignCenter)
            etiquette.setPixmap(
                image.scaled(
                    max(1, largeur), max(1, hauteur),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation,
                )
            )
            disposition.addWidget(etiquette, 1)
            boutons = QDialogButtonBox(QDialogButtonBox.Cancel)
            continuer = boutons.addButton("Continuer l’export", QDialogButtonBox.AcceptRole)
            continuer.clicked.connect(dialogue.accept)
            boutons.rejected.connect(dialogue.reject)
            disposition.addWidget(boutons)
            dialogue.resize(
                min(max(480, largeur + 40), zone.width()) if zone else largeur + 40,
                min(max(320, hauteur + 90), zone.height()) if zone else hauteur + 90,
            )
            return dialogue.exec_() == QDialog.Accepted
        finally:
            if os.path.exists(chemin):
                os.unlink(chemin)

    def _ajuster_taille_fenetre(self):
        """Garde la fenêtre dans l'écran et réserve une barre d'action toujours visible."""
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            self.resize(720, 780)
            self.setMinimumSize(520, 380)
            return
        available = screen.availableGeometry()
        width = max(320, min(760, available.width() - 40))
        height = max(300, min(820, available.height() - 60))
        self.setMinimumSize(min(520, width), min(380, height))
        self.setMaximumSize(width, height)
        self.resize(min(720, width), min(760, height))

    def _couches_cartographiques(self):
        return [
            layer
            for layer in self.project.mapLayers().values()
            if layer.isValid()
            and layer.type() in (QgsMapLayer.VectorLayer, QgsMapLayer.RasterLayer)
            and (
                not isinstance(layer, QgsVectorLayer)
                or layer.featureCount() > 0
            )
        ]

    def _actualiser_couches(self):
        couche_active = self.iface.activeLayer()
        anciennes_couches = {
            self.couches_contexte.item(index).data(Qt.UserRole)
            for index in range(self.couches_contexte.count())
        } if hasattr(self, "couches_contexte") else set()
        anciens_choix = {
            self.couches_contexte.item(index).data(Qt.UserRole)
            for index in range(self.couches_contexte.count())
            if self.couches_contexte.item(index).checkState() == Qt.Checked
        } if hasattr(self, "couches_contexte") else set()

        self.couche_principale.blockSignals(True)
        self.couche_principale.clear()
        couches = self._couches_cartographiques()
        for layer in couches:
            self.couche_principale.addItem(layer.name(), layer.id())

        if couche_active and self.couche_principale.findData(couche_active.id()) >= 0:
            self.couche_principale.setCurrentIndex(
                self.couche_principale.findData(couche_active.id())
            )
        self.couche_principale.blockSignals(False)

        self.couches_contexte.clear()
        couche_principale_id = self.couche_principale.currentData()
        for layer in couches:
            if layer.id() == couche_principale_id:
                continue
            item = QListWidgetItem(layer.name())
            item.setData(Qt.UserRole, layer.id())
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            default_checked = layer.id() in anciens_choix if anciennes_couches else True
            item.setCheckState(Qt.Checked if default_checked else Qt.Unchecked)
            self.couches_contexte.addItem(item)

        if couches and not self.crs.text().strip():
            project_crs = self.project.crs()
            self.crs.setText(project_crs.authid() if project_crs.isValid() else "")
        self._couche_principale_changee()
        self._mettre_a_jour_pas_grille()

    def _mettre_a_jour_pas_grille(self):
        """Choisit un pas lisible par défaut selon les unités du SCR sélectionné."""
        if self._pas_grille_personnalise:
            return
        crs = QgsCoordinateReferenceSystem(self.crs.text().strip())
        self.intervalle_grille.blockSignals(True)
        if crs.isValid() and crs.isGeographic():
            self.intervalle_grille.setDecimals(4)
            self.intervalle_grille.setSingleStep(0.1)
            self.intervalle_grille.setValue(0.1)
        else:
            self.intervalle_grille.setDecimals(0)
            self.intervalle_grille.setSingleStep(1000)
            self.intervalle_grille.setValue(10000)
        self.intervalle_grille.blockSignals(False)

    def _couche_principale_changee(self):
        layer_id = self.couche_principale.currentData()
        layer = self.project.mapLayer(layer_id) if layer_id else None
        self.champs_statistiques.clear()
        self.champs_statistiques.addItem("Ne pas afficher de somme", "")
        if isinstance(layer, QgsVectorLayer):
            for field in layer.fields():
                if field.isNumeric():
                    self.champs_statistiques.addItem(field.name(), field.name())
            for index in range(self.champs_statistiques.count()):
                field_name = self.champs_statistiques.itemData(index)
                if field_name and field_name.lower() in {
                    "aire_ha", "surface_ha", "area_ha", "hectares", "area",
                }:
                    self.champs_statistiques.setCurrentIndex(index)
                    break
        self.champs_statistiques.setEnabled(isinstance(layer, QgsVectorLayer))
        if layer:
            if not self.titre.text().strip() or self.titre.text() == "Carte thématique":
                self.titre.setText(layer.name())
            if not self.crs.text().strip() and layer.crs().isValid():
                self.crs.setText(layer.crs().authid())

    def _choisir_pdf(self):
        chemin, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer la carte PDF", self.chemin_pdf.text(), "Document PDF (*.pdf)"
        )
        if chemin:
            if not chemin.lower().endswith(".pdf"):
                chemin += ".pdf"
            self.chemin_pdf.setText(chemin)

    def _afficher_erreur(self, titre, message):
        QMessageBox.critical(self, titre, message)

    @staticmethod
    def _chemin_canonique(chemin):
        """Résout les alias simples, les chemins relatifs et les liens symboliques."""
        return os.path.normcase(str(Path(chemin).expanduser().resolve(strict=False)))

    def _valider_chemins_export(self, chemins, couches):
        """Empêche un export de remplacer le projet QGIS ou un fichier de couche."""
        chemins_proteges = {}
        fichier_projet = self.project.fileName()
        if fichier_projet:
            chemins_proteges[self._chemin_canonique(fichier_projet)] = "le projet QGIS"

        registre = QgsProviderRegistry.instance()
        for layer in couches:
            uri = registre.decodeUri(layer.providerType(), layer.source())
            source = uri.get("path") or uri.get("database")
            if not source or "://" in str(source):
                continue
            chemins_proteges[self._chemin_canonique(source)] = (
                f"la couche « {layer.name()} »"
            )

        chemins_vus = set()
        for chemin in chemins:
            if chemin.is_dir():
                raise ValueError(f"Le chemin de sortie désigne un dossier : {chemin}")
            chemin_normalise = self._chemin_canonique(chemin)
            if chemin_normalise in chemins_vus:
                raise ValueError("Le PDF et le PNG ne peuvent pas utiliser le même fichier.")
            chemins_vus.add(chemin_normalise)
            if chemin_normalise in chemins_proteges:
                raise ValueError(
                    f"Export refusé : le fichier choisi est utilisé par "
                    f"{chemins_proteges[chemin_normalise]}. Choisissez un autre nom "
                    "pour protéger vos données."
                )

    @staticmethod
    def _creer_chemin_temporaire(chemin_final):
        """Réserve un nom temporaire dans le dossier final pour un remplacement sûr."""
        descripteur, chemin_temporaire = tempfile.mkstemp(
            prefix="cartographie_facile_",
            suffix=chemin_final.suffix,
            dir=str(chemin_final.parent),
        )
        os.close(descripteur)
        os.unlink(chemin_temporaire)
        return Path(chemin_temporaire)

    def _creer_carte(self):
        layer_id = self.couche_principale.currentData()
        principale = self.project.mapLayer(layer_id) if layer_id else None
        if not principale or not principale.isValid():
            self._afficher_erreur(
                "Couche manquante", "Choisissez une couche cartographique valide."
            )
            return
        if not self.titre.text().strip():
            self._afficher_erreur("Titre manquant", "Saisissez le titre de la carte.")
            return
        pdf_path = Path(self.chemin_pdf.text().strip()) if self.chemin_pdf.text().strip() else None
        if not pdf_path:
            self._choisir_pdf()
            return
        if pdf_path.suffix.lower() != ".pdf":
            pdf_path = pdf_path.with_suffix(".pdf")
            self.chemin_pdf.setText(str(pdf_path))
        if not pdf_path.parent.is_dir():
            self._afficher_erreur(
                "Dossier de sortie introuvable",
                f"Le dossier choisi n'existe pas : {pdf_path.parent}",
            )
            return
        logo_path = Path(self.chemin_logo.text().strip()) if self.chemin_logo.text().strip() else None
        if logo_path and (not logo_path.is_file() or logo_path.suffix.lower() not in {
            ".png", ".jpg", ".jpeg", ".svg",
        }):
            self._afficher_erreur(
                "Logo invalide", "Choisissez un fichier PNG, JPG, JPEG ou SVG existant."
            )
            return
        crs_carte = QgsCoordinateReferenceSystem(self.crs.text().strip())
        if not crs_carte.isValid():
            self._afficher_erreur(
                "SCR invalide",
                "Saisissez un code reconnu, par exemple EPSG:32631, ou le SCR du projet.",
            )
            return

        contexte_ids = {
            self.couches_contexte.item(index).data(Qt.UserRole)
            for index in range(self.couches_contexte.count())
            if self.couches_contexte.item(index).checkState() == Qt.Checked
        }
        ids_requis = contexte_ids | {principale.id()}
        ordre_couches = self.project.layerTreeRoot().layerOrder()
        couches = [
            layer for layer in ordre_couches
            if layer.id() in ids_requis and layer.isValid()
            and layer.type() in (QgsMapLayer.VectorLayer, QgsMapLayer.RasterLayer)
        ]
        if principale not in couches:
            couches.append(principale)

        png_path = pdf_path.with_suffix(".png")
        sorties = [pdf_path]
        if self.exporter_png.isChecked():
            sorties.append(png_path)
        svg_path = pdf_path.with_suffix(".svg")
        if self.exporter_svg.isChecked():
            sorties.append(svg_path)
        try:
            self._valider_chemins_export(sorties, self.project.mapLayers().values())
        except (OSError, RuntimeError, ValueError) as error:
            self._afficher_erreur("Chemin de sortie refusé", str(error))
            return

        fichiers_existants = [path for path in (
                                  pdf_path,
                                  png_path if self.exporter_png.isChecked() else None,
                                  svg_path if self.exporter_svg.isChecked() else None,
                              )
                              if path and path.exists()]
        if fichiers_existants:
            reponse = QMessageBox.question(
                self,
                "Remplacer les exports ?",
                "Les fichiers suivants existent déjà :\n"
                + "\n".join(str(path) for path in fichiers_existants)
                + "\n\nVoulez-vous les remplacer ?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reponse != QMessageBox.Yes:
                return

        nom_layout = f"Carte - {self.titre.text().strip()}"
        ancien_layout = self.project.layoutManager().layoutByName(nom_layout)
        if ancien_layout:
            reponse = QMessageBox.question(
                self,
                "Mise en page déjà présente",
                f"La mise en page « {nom_layout} » existe. La remplacer ?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reponse != QMessageBox.Yes:
                return

        try:
            mise_en_page = self._construire_mise_en_page(principale, couches, crs_carte, nom_layout)
            exportateur = QgsLayoutExporter(mise_en_page)
            if self.apercu_avant_export.isChecked() and not self._confirmer_apercu(exportateur):
                return
            pdf_settings = QgsLayoutExporter.PdfExportSettings()
            pdf_settings.dpi = self.resolution_pdf.value()
            pdf_temporaire = self._creer_chemin_temporaire(pdf_path)
            png_temporaire = (
                self._creer_chemin_temporaire(png_path)
                if self.exporter_png.isChecked() else None
            )
            svg_temporaire = (
                self._creer_chemin_temporaire(svg_path)
                if self.exporter_svg.isChecked() else None
            )
            try:
                resultat_pdf = exportateur.exportToPdf(str(pdf_temporaire), pdf_settings)
                if resultat_pdf != QgsLayoutExporter.Success:
                    raise RuntimeError(f"Échec de l'export PDF (code QGIS {resultat_pdf}).")

                if png_temporaire:
                    image_settings = QgsLayoutExporter.ImageExportSettings()
                    image_settings.dpi = self.resolution_png.value()
                    resultat_png = exportateur.exportToImage(str(png_temporaire), image_settings)
                    if resultat_png != QgsLayoutExporter.Success:
                        raise RuntimeError(f"Échec de l'export PNG (code QGIS {resultat_png}).")
                if svg_temporaire:
                    svg_settings = QgsLayoutExporter.SvgExportSettings()
                    svg_settings.dpi = self.resolution_pdf.value()
                    resultat_svg = exportateur.exportToSvg(str(svg_temporaire), svg_settings)
                    if resultat_svg != QgsLayoutExporter.Success:
                        raise RuntimeError(f"Échec de l'export SVG (code QGIS {resultat_svg}).")

                os.replace(str(pdf_temporaire), str(pdf_path))
                if png_temporaire:
                    os.replace(str(png_temporaire), str(png_path))
                if svg_temporaire:
                    os.replace(str(svg_temporaire), str(svg_path))
            finally:
                for temporaire in (pdf_temporaire, png_temporaire, svg_temporaire):
                    if temporaire and temporaire.exists():
                        temporaire.unlink()

            gestionnaire = self.project.layoutManager()
            if ancien_layout:
                gestionnaire.removeLayout(ancien_layout)
            if not gestionnaire.addLayout(mise_en_page):
                if ancien_layout:
                    gestionnaire.addLayout(ancien_layout)
                raise RuntimeError("QGIS n'a pas pu ajouter la mise en page au projet.")

            QMessageBox.information(
                self,
                "Carte créée",
                f"La carte est prête.\n\nPDF : {pdf_path}"
                + (f"\nAperçu PNG : {png_path}" if self.exporter_png.isChecked() else "")
                + (f"\nFichier SVG : {svg_path}" if self.exporter_svg.isChecked() else "")
                + "\n\nLa mise en page a été ajoutée au projet QGIS. "
                  "Enregistrez le projet pour la conserver.",
            )
            self.iface.openLayoutDesigner(mise_en_page)
        except Exception as error:
            self._afficher_erreur("Erreur de création", str(error))

    def _construire_mise_en_page(self, principale, couches, crs_carte, nom_layout):
        format_page, orientation = self.format_page.currentData()
        page_width, page_height = (420, 297) if format_page == "A3" else (297, 210)
        if orientation == "portrait":
            page_width, page_height = page_height, page_width
        marge = 10
        haut_carte = 35
        pied_page = 25
        bas_carte = page_height - pied_page - 8
        hauteur_carte = bas_carte - haut_carte
        if orientation == "portrait":
            largeur_carte = page_width * 0.60
        else:
            largeur_carte = (page_width - 3 * marge) * 0.69
        espace_panneau = 5
        x_panneau = marge + largeur_carte + espace_panneau
        largeur_panneau = page_width - marge - x_panneau
        hauteur_panneau = hauteur_carte
        palette = self._palette()

        layout = QgsPrintLayout(self.project)
        layout.initializeDefaults()
        layout.setName(nom_layout)
        layout.pageCollection().pages()[0].setPageSize(
            QgsLayoutSize(page_width, page_height)
        )
        self._ajouter_texte(
            layout, self.titre.text().strip().upper(), marge, 7,
            page_width - 2 * marge - (25 if self.chemin_logo.text().strip() else 0),
            12, 21 if format_page == "A3" else 16,
            palette["title"], True,
        )
        logo_path = self.chemin_logo.text().strip()
        if logo_path:
            logo = QgsLayoutItemPicture(layout)
            logo.setPicturePath(logo_path)
            layout.addLayoutItem(logo)
            logo.attemptMove(QgsLayoutPoint(page_width - marge - 20, 6))
            logo.attemptResize(QgsLayoutSize(20, 20))
        sous_titre = self.sous_titre.text().strip()
        if sous_titre:
            self._ajouter_texte(
                layout, sous_titre, marge + 1, 21, page_width - 2 * marge, 7,
                10 if format_page == "A3" else 8, palette["muted"],
            )
        self._ajouter_forme(layout, marge, 30, page_width - 2 * marge, 0.8,
                            palette["accent"])

        map_item = QgsLayoutItemMap(layout)
        layout.addLayoutItem(map_item)
        map_item.attemptMove(QgsLayoutPoint(marge, haut_carte))
        map_item.attemptResize(QgsLayoutSize(largeur_carte, hauteur_carte))
        map_item.setLayers(couches)
        map_item.setKeepLayerSet(True)
        map_item.setKeepLayerStyles(not self.afficher_etiquettes.isChecked())
        if not self.afficher_etiquettes.isChecked():
            etiquettes_initiales = {
                layer.id(): layer.labelsEnabled()
                for layer in couches if isinstance(layer, QgsVectorLayer)
            }
            try:
                for layer in couches:
                    if isinstance(layer, QgsVectorLayer):
                        layer.setLabelsEnabled(False)
                map_item.storeCurrentLayerStyles()
            finally:
                for layer in couches:
                    if isinstance(layer, QgsVectorLayer):
                        layer.setLabelsEnabled(etiquettes_initiales[layer.id()])
        map_item.setCrs(crs_carte)
        map_item.setBackgroundColor(QColor(palette["map"]))
        map_item.setBackgroundEnabled(True)
        map_item.setFrameEnabled(True)
        map_item.setFrameStrokeColor(QColor(palette["frame"]))
        map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.3))
        map_item.zoomToExtent(self._etendue_carte(couches, principale, crs_carte))
        if self.echelle_fixe.isChecked():
            map_item.setScale(self.denominateur_echelle.value())

        if self.afficher_grille.isChecked():
            self._ajouter_grille(map_item, crs_carte, palette)

        if self.afficher_nord.isChecked():
            fleche_x = marge + largeur_carte - 15
            self._ajouter_forme(
                layout, fleche_x, haut_carte + 5, 10, 17,
                palette["panel"], palette["frame"], "0.25",
            )
            self._ajouter_texte(
                layout, "N\n↑", fleche_x + 1, haut_carte + 5, 8, 15,
                11, palette["title"], True, Qt.AlignHCenter,
            )

        if self.afficher_echelle.isChecked():
            scale_bar = QgsLayoutItemScaleBar(layout)
            scale_bar.setStyle("Single Box")
            scale_bar.setLinkedMap(map_item)
            scale_bar.setUnits(self.unites_echelle.currentData())
            scale_bar.setUnitsPerSegment(self._segment_echelle(map_item, crs_carte))
            scale_bar.setNumberOfSegments(2)
            scale_bar.setNumberOfSegmentsLeft(0)
            scale_bar.setUnitLabel(self._libelle_unite_echelle())
            scale_bar.setHeight(2)
            scale_bar.setTextFormat(self._format_texte_echelle(palette))
            scale_bar.setFillColor(QColor(palette["title"]))
            scale_bar.setFillColor2(QColor(palette["panel"]))
            scale_bar.setLineColor(QColor(palette["title"]))
            layout.addLayoutItem(scale_bar)
            scale_bar.attemptMove(QgsLayoutPoint(marge + 5, bas_carte - 10))

        couches_contexte = [layer for layer in couches if layer.id() != principale.id()]
        if self.afficher_legende.isChecked():
            self._ajouter_legende(
                layout, principale, couches_contexte, x_panneau, haut_carte,
                largeur_panneau, hauteur_panneau, palette,
            )
        self._ajouter_pied_page(layout, marge, page_width, page_height, crs_carte, palette)
        return layout

    def _etendue_carte(self, couches, principale, crs_carte):
        """Calcule l'emprise demandée dans le SCR de la mise en page."""
        mode = self.emprise.currentData()
        if mode == "canvas":
            canvas = self.iface.mapCanvas()
            canvas_crs = canvas.mapSettings().destinationCrs()
            extent = QgsRectangle(canvas.extent())
            self._verifier_etendue(extent, "la vue du canevas")
            if canvas_crs != crs_carte:
                transform = QgsCoordinateTransform(canvas_crs, crs_carte, self.project)
                extent = transform.transformBoundingBox(extent)
            self._verifier_etendue(extent, "la vue reprojetée du canevas")
            extent.scale(1 + 2 * self.marge_emprise.value() / 100)
            self._verifier_etendue(extent, "la vue avec sa marge")
            return extent
        if mode == "main":
            couches = [principale]

        projet_crs = self.project.crs()
        union = QgsRectangle()
        union_empty = True
        for layer in couches:
            source_crs = layer.crs() if layer.crs().isValid() else projet_crs
            if not source_crs.isValid():
                continue
            extent = QgsRectangle(layer.extent())
            self._verifier_etendue(
                extent, f"la couche « {layer.name()} »", allow_empty=True
            )
            if source_crs != crs_carte:
                transform = QgsCoordinateTransform(source_crs, crs_carte, self.project)
                extent = transform.transformBoundingBox(extent)
                self._verifier_etendue(
                    extent, f"la couche « {layer.name()} » reprojetée", allow_empty=True
                )
            if extent.isEmpty():
                continue
            if union_empty:
                union = QgsRectangle(extent)
                union_empty = False
            else:
                union.combineExtentWith(extent)
        if union_empty:
            raise ValueError("Impossible de calculer une emprise pour les couches sélectionnées.")
        union.scale(1 + 2 * self.marge_emprise.value() / 100)
        self._verifier_etendue(union, "l'emprise finale")
        return union

    @staticmethod
    def _verifier_etendue(extent, description, allow_empty=False):
        valeurs = (
            extent.xMinimum(), extent.yMinimum(),
            extent.xMaximum(), extent.yMaximum(),
        )
        if not all(math.isfinite(valeur) for valeur in valeurs):
            raise ValueError(
                f"L'emprise de {description} contient une coordonnée invalide "
                "(NaN ou infini). Vérifiez la couche et son système de coordonnées."
            )
        if not allow_empty and (
            extent.isEmpty() or extent.width() <= 0 or extent.height() <= 0
        ):
            raise ValueError(
                f"L'emprise de {description} est vide ou de dimension nulle. "
                "Vérifiez que la couche contient des données géographiques valides."
            )

    def _ajouter_legende(self, layout, layer, context_layers, x, y, width, height, palette):
        """Dessine la légende de la couche principale et les symboles des couches de repère."""
        items = self._items_legende(layer)
        self._ajouter_forme(
            layout, x, y, width, height, palette["panel"], palette["frame"], "0.3"
        )
        marge = 6
        x_interne = x + marge
        largeur_interne = width - 2 * marge
        self._ajouter_texte(layout, "LÉGENDE", x_interne, y + 5, largeur_interne,
                            9, 14 if width > 100 else 11, palette["title"], True)
        self._ajouter_texte(
            layout, layer.name(), x_interne, y + 16, largeur_interne,
            7, 8, palette["muted"],
        )
        self._ajouter_forme(
            layout, x_interne, y + 24, largeur_interne, 0.35, palette["rule"]
        )

        haut_liste = y + 28
        bas_liste = y + height - 31
        groupes = [(layer, items)]
        for contexte in context_layers:
            contexte_items = self._items_legende(contexte)
            if contexte_items:
                groupes.append((contexte, contexte_items))

        nombre_lignes = sum(1 + len(group_items) for _, group_items in groupes)
        hauteur_ligne = max(5.5, min(12.0, (bas_liste - haut_liste) / max(1, nombre_lignes)))
        taille_texte = 8 if hauteur_ligne >= 8 else 7
        position_y = haut_liste
        for groupe_index, (groupe_layer, group_items) in enumerate(groupes):
            if groupe_index:
                self._ajouter_texte(
                    layout, groupe_layer.name(), x_interne, position_y,
                    largeur_interne, hauteur_ligne, taille_texte, palette["muted"], True,
                )
                position_y += hauteur_ligne
            for item in group_items:
                symbole = item.symbol() if hasattr(item, "symbol") else item[1]
                libelle = item.label() if hasattr(item, "label") else str(item[0])
                if groupe_index and (
                    not libelle.strip()
                    or libelle == groupe_layer.name()
                    or isinstance(groupe_layer, QgsRasterLayer)
                ):
                    libelle = "Entités"
                if isinstance(groupe_layer, QgsRasterLayer):
                    libelle = groupe_layer.name()
                if symbole is None and not isinstance(groupe_layer, QgsRasterLayer):
                    continue
                self._ajouter_symbole_legende(
                    layout, groupe_layer, symbole, x_interne,
                    position_y + (hauteur_ligne - 5) / 2,
                )
                self._ajouter_texte(
                    layout, libelle, x_interne + 11, position_y,
                    largeur_interne - 12, hauteur_ligne, taille_texte, palette["text"],
                )
                position_y += hauteur_ligne

        resume_y = max(position_y + 2, bas_liste + 2)
        if isinstance(layer, QgsVectorLayer) and resume_y < y + height - 14:
            self._ajouter_forme(
                layout, x_interne, resume_y, largeur_interne, 0.35, palette["rule"]
            )
            self._ajouter_texte(layout, "RÉSUMÉ", x_interne, resume_y + 3,
                                largeur_interne, 6, 8, palette["title"], True)
            self._ajouter_texte(
                layout, f"Entités : {layer.featureCount():,}".replace(",", " "),
                x_interne, resume_y + 10, largeur_interne, 6, 8, palette["text"],
            )
            field_name = self.champs_statistiques.currentData()
            if field_name:
                total = self._somme_champ(layer, field_name)
                self._ajouter_texte(
                    layout,
                    f"Somme {field_name} : {total:,.2f}".replace(",", " "),
                    x_interne, resume_y + 17, largeur_interne, 8, 7, palette["text"],
                )

    @staticmethod
    def _items_legende(layer):
        if isinstance(layer, QgsRasterLayer):
            return [(layer.name(), None)]
        items = layer.renderer().legendSymbolItems()
        if not items and layer.renderer().symbol():
            return [(layer.name(), layer.renderer().symbol())]
        return items

    def _ajouter_symbole_legende(self, layout, layer, symbol, x, y):
        """Dessine une pastille dont la forme rappelle la géométrie de la couche."""
        if symbol is None and isinstance(layer, QgsRasterLayer):
            self._ajouter_forme(layout, x + 1, y + 0.2, 7, 5, "#a9b5b8", "#66736b", "0.2")
            return
        couleur = symbol.color().name()
        if layer.geometryType() == 1:
            self._ajouter_forme(layout, x, y + 2.2, 8, 0.6, couleur)
        elif layer.geometryType() == 0:
            self._ajouter_forme(
                layout, x + 2.3, y + 0.4, 4.5, 4.5, couleur, "#66736b", "0.2",
                QgsLayoutItemShape.Ellipse,
            )
        else:
            self._ajouter_forme(layout, x + 1, y + 0.2, 6, 5, couleur, "#66736b", "0.2")

    def _ajouter_pied_page(self, layout, marge, largeur_page, hauteur_page, crs_carte, palette):
        """Ajoute SCR, sources, date et une mention sur le caractère de la carte."""
        y = hauteur_page - 23
        largeur_colonne = (largeur_page - 3 * marge) / 2
        self._ajouter_texte(layout, "SYSTÈME DE COORDONNÉES", marge, y, largeur_colonne,
                            6, 7, palette["muted"], True)
        self._ajouter_texte(
            layout,
            f"{crs_carte.description()}  •  {crs_carte.authid()}",
            marge, y + 6, largeur_colonne, 7, 8, palette["text"],
        )
        x_source = marge + largeur_colonne + marge
        self._ajouter_texte(layout, "SOURCES", x_source, y, largeur_colonne,
                            6, 7, palette["muted"], True)
        self._ajouter_texte(
            layout, self.sources.text().strip() or "Sources non renseignées",
            x_source, y + 6, largeur_colonne, 7, 8, palette["text"],
        )
        self._ajouter_texte(
            layout,
            f"Carte créée le {datetime.now().strftime('%d/%m/%Y')}  •  "
            "Les limites et surfaces dépendent des données sources.",
            marge, hauteur_page - 8, largeur_page - 2 * marge, 5,
            7, palette["muted"],
        )

    def _format_texte_echelle(self, palette):
        from qgis.core import QgsTextFormat

        text_format = QgsTextFormat()
        font = self.police.currentFont()
        font.setPointSize(8)
        text_format.setFont(font)
        text_format.setSize(8)
        text_format.setColor(QColor(palette["title"]))
        return text_format

    def _ajouter_grille(self, map_item, crs_carte, palette):
        """Ajoute un quadrillage optionnel annoté en coordonnées."""
        grille = QgsLayoutItemMapGrid("Grille de coordonnées", map_item)
        map_item.grids().addGrid(grille)
        grille.setEnabled(True)
        grille.setCrs(crs_carte)
        grille.setIntervalX(self.intervalle_grille.value())
        grille.setIntervalY(self.intervalle_grille.value())
        grille.setStyle(QgsLayoutItemMapGrid.Solid)
        grille.setLineSymbol(QgsLineSymbol.createSimple({
            "line_color": palette["grid"],
            "line_width": "0.15",
            "line_style": "dot",
        }))
        grille.setAnnotationEnabled(True)
        grille.setAnnotationFormat(QgsLayoutItemMapGrid.Decimal)
        grille.setAnnotationPrecision(0 if not crs_carte.isGeographic() else 2)
        font_grille = self.police.currentFont()
        font_grille.setPointSize(7)
        grille.setAnnotationFont(font_grille)
        grille.setAnnotationFontColor(QColor(palette["muted"]))

    def _palette(self):
        palettes = {
            "classic": {
                "title": "#26392d", "muted": "#56665b", "accent": "#73874d",
                "panel": "#f5f7f1", "frame": "#d7ded4", "rule": "#d0d8cf",
                "map": "#fbfcf8", "text": "#303b33", "grid": "#78877b",
            },
            "modern": {
                "title": "#17324d", "muted": "#527084", "accent": "#2385a4",
                "panel": "#eff6fa", "frame": "#cedee8", "rule": "#c7dce5",
                "map": "#f8fbfd", "text": "#283a47", "grid": "#7595a5",
            },
            "nature": {
                "title": "#493528", "muted": "#806b57", "accent": "#b17b42",
                "panel": "#f7f2e9", "frame": "#e3d6c3", "rule": "#ddcfbb",
                "map": "#fcfaf5", "text": "#43372d", "grid": "#a08e77",
            },
            "minimal": {
                "title": "#252525", "muted": "#666666", "accent": "#333333",
                "panel": "#ffffff", "frame": "#cccccc", "rule": "#d8d8d8",
                "map": "#ffffff", "text": "#303030", "grid": "#888888",
            },
            "metro": {
                "title": "#243247", "muted": "#61748a", "accent": "#dc6b45",
                "panel": "#f0f3f6", "frame": "#ccd5de", "rule": "#d5dde5",
                "map": "#fbfcfd", "text": "#293746", "grid": "#8292a3",
            },
            "ocean": {
                "title": "#123c46", "muted": "#4d7376", "accent": "#18a6a6",
                "panel": "#edf7f6", "frame": "#c5e0dc", "rule": "#c9e2de",
                "map": "#f8fcfb", "text": "#253e40", "grid": "#6d9693",
            },
            "sahel": {
                "title": "#593d24", "muted": "#816c50", "accent": "#c6872f",
                "panel": "#faf4e9", "frame": "#e6d6b8", "rule": "#e5d6bd",
                "map": "#fdfaf4", "text": "#453a2c", "grid": "#a58d69",
            },
            "light": {
                "title": "#303b4a", "muted": "#6b7787", "accent": "#5479a6",
                "panel": "#f4f6f9", "frame": "#d6dce5", "rule": "#dfe4eb",
                "map": "#ffffff", "text": "#303946", "grid": "#8a98aa",
            },
        }
        palette = palettes[self.design.currentData()].copy()
        if self.couleur_accent:
            palette["accent"] = self.couleur_accent
        return palette

    def _segment_echelle(self, map_item, crs_carte):
        """Choisit une longueur d'échelle lisible selon l'étendue et les unités choisies."""
        extent = map_item.extent()
        self._verifier_etendue(extent, "la carte utilisée pour l'échelle")
        distance = extent.width()
        if crs_carte.isGeographic():
            lat = (extent.yMinimum() + extent.yMaximum()) / 2
            distance *= 111_320 * max(0.1, abs(math.cos(math.radians(lat))))
        units = self.unites_echelle.currentData()
        if units == QgsUnitTypes.DistanceKilometers:
            value = distance / 1000 / 4
        elif units == QgsUnitTypes.DistanceMiles:
            value = distance / 1609.344 / 4
        elif units == QgsUnitTypes.DistanceFeet:
            value = distance * 3.28084 / 4
        else:
            value = distance / 4
        if not math.isfinite(value) or value <= 0:
            raise ValueError(
                "Impossible de calculer l'échelle : l'emprise produit une distance invalide. "
                "Vérifiez l'emprise et le système de coordonnées."
            )
        value = max(value, 0.001)
        magnitude = 10 ** int(math.floor(math.log10(value)))
        return max(magnitude, round(value / magnitude) * magnitude)

    def _libelle_unite_echelle(self):
        return {
            QgsUnitTypes.DistanceKilometers: "km",
            QgsUnitTypes.DistanceMeters: "m",
            QgsUnitTypes.DistanceMiles: "mi",
            QgsUnitTypes.DistanceFeet: "ft",
        }.get(self.unites_echelle.currentData(), "")

    @staticmethod
    def _ajouter_forme(layout, x, y, width, height, couleur, contour=None, epaisseur="0.2",
                       forme=QgsLayoutItemShape.Rectangle):
        item = QgsLayoutItemShape(layout)
        item.setShapeType(forme)
        item.setSymbol(QgsFillSymbol.createSimple({
            "color": couleur,
            "outline_color": contour or couleur,
            "outline_width": epaisseur,
            "joinstyle": "miter",
        }))
        layout.addLayoutItem(item)
        item.attemptMove(QgsLayoutPoint(x, y))
        item.attemptResize(QgsLayoutSize(width, height))
        return item

    def _ajouter_texte(self, layout, texte, x, y, width, height, taille=9, couleur="#28352e",
                       gras=False, alignement=Qt.AlignLeft):
        item = QgsLayoutItemLabel(layout)
        item.setText(texte)
        font = self.police.currentFont()
        font.setPointSize(taille)
        font.setBold(gras)
        item.setFont(font)
        item.setFontColor(QColor(couleur))
        item.setHAlign(alignement)
        item.setVAlign(Qt.AlignVCenter)
        item.setMargin(0)
        layout.addLayoutItem(item)
        item.attemptMove(QgsLayoutPoint(x, y))
        item.attemptResize(QgsLayoutSize(width, height))
        return item

    @staticmethod
    def _somme_champ(layer, field_name):
        total = 0.0
        for feature in layer.getFeatures():
            value = feature[field_name]
            if value is not None:
                total += float(value)
        return total
