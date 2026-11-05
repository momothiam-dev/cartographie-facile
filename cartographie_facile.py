from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QAction, QMessageBox


class CartographieFacile:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.about_action = None
        self.dialog = None

    def initGui(self):
        self.action = QAction("Créer une carte…", self.iface.mainWindow())
        self.action.setToolTip("Composer et exporter une mise en page cartographique")
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("&Cartographie facile", self.action)
        self.iface.addToolBarIcon(self.action)

        self.about_action = QAction("À propos…", self.iface.mainWindow())
        self.about_action.triggered.connect(self.about)
        self.iface.addPluginToMenu("&Cartographie facile", self.about_action)

    def unload(self):
        if self.action is not None:
            self.iface.removePluginMenu("&Cartographie facile", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
        if self.about_action is not None:
            self.iface.removePluginMenu("&Cartographie facile", self.about_action)
            self.about_action = None
        if self.dialog is not None:
            self.dialog.close()
            self.dialog = None

    def about(self):
        QMessageBox.about(
            self.iface.mainWindow(),
            "À propos de Cartographie facile",
            "<h3>Cartographie facile</h3>"
            "<p><b>Objectif :</b> aider à composer rapidement une carte prête à "
            "relire et à exporter, sans remplacer le travail d'analyse SIG.</p>"
            "<p><b>Méthode :</b> l'extension utilise les couches déjà ouvertes dans "
            "QGIS, leurs styles et le SCR choisi pour créer une mise en page avec "
            "légende, échelle, flèche nord et grille facultatives, puis exporter "
            "en PDF ou en PNG.</p>"
            "<p><b>Avantages :</b> moins de tâches répétitives, plusieurs formats "
            "et designs, modèles d’exemple et modèles réutilisables, aperçu avant export, logo et options "
            "adaptées à différents projets, et mise en page "
            "modifiable ensuite dans QGIS.</p>"
            "<p><b>Protection :</b> aucune connexion Internet ni commande externe ; "
            "les données sources et le projet sont protégés contre l'écrasement par "
            "les exports. Une confirmation est demandée avant de remplacer un export.</p>"
            "<p>Créée par Mamadou Thiam.</p>",
        )

    def run(self):
        from .dialog import CartographieDialog

        if self.dialog is None:
            self.dialog = CartographieDialog(self.iface)
        self.dialog.setWindowState(
            self.dialog.windowState()
            & ~Qt.WindowState.WindowMaximized
            & ~Qt.WindowState.WindowFullScreen
        )
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
