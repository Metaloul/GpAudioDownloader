#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GP Audio Downloader
Application pour télécharger des fichiers audio basés sur des fichiers Guitar Pro
"""

import sys
import os
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QWidget, QPushButton, QLabel, QLineEdit, QFileDialog,
    QProgressBar, QTextEdit, QGroupBox, QMessageBox, QMenuBar
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon, QAction

from downloader import AudioDownloader
from gp_parser import GuitarProParser


class DownloadWorker(QThread):
    """Thread worker pour le téléchargement en arrière-plan"""
    progress_updated = Signal(int)
    status_updated = Signal(str)
    download_completed = Signal()
    error_occurred = Signal(str)
    
    def __init__(self, folder_path, output_path, exceptions=None):
        super().__init__()
        self.folder_path = folder_path
        self.output_path = output_path
        self.exceptions = exceptions or []
        self.downloader = AudioDownloader(output_path)
        self.parser = GuitarProParser()
        self._stop_requested = False
        self._pause_requested = False
        
    def stop(self):
        """Arrêter le téléchargement"""
        self._stop_requested = True
        
    def pause(self):
        """Mettre en pause le téléchargement"""
        self._pause_requested = True
        
    def resume(self):
        """Reprendre le téléchargement"""
        self._pause_requested = False
        
    def run(self):
        try:
            # Rechercher les fichiers Guitar Pro
            gp_files = self.parser.find_gp_files(self.folder_path)
            if not gp_files:
                self.error_occurred.emit("Aucun fichier Guitar Pro trouvé dans le dossier sélectionné.")
                return
                
            # Charger le cache des fichiers déjà traités
            cache_file = os.path.join(self.output_path, ".gp_downloader_cache.txt")
            processed_files = self._load_cache(cache_file)
            
            # Filtrer les fichiers selon les exceptions et le cache
            filtered_files = []
            for gp_file in gp_files:
                metadata = self.parser.extract_metadata(gp_file)
                
                # Vérifier si le fichier est dans le cache
                if gp_file in processed_files:
                    self.status_updated.emit(f"Ignoré (déjà traité): {metadata['title']}")
                    continue
                    
                # Vérifier les exceptions
                if self._should_exclude(metadata):
                    self.status_updated.emit(f"Ignoré (exception): {metadata['title']}")
                    continue
                    
                filtered_files.append(gp_file)
                
            if not filtered_files:
                self.status_updated.emit("Aucun nouveau fichier à traiter.")
                self.download_completed.emit()
                return
                
            total_files = len(filtered_files)
            self.status_updated.emit(f"Trouvé {total_files} nouveau(x) fichier(s) à traiter")
            
            for i, gp_file in enumerate(filtered_files):
                if self._stop_requested:
                    self.status_updated.emit("⏹️ Téléchargement arrêté par l'utilisateur")
                    return
                    
                # Gérer la pause
                while self._pause_requested and not self._stop_requested:
                    self.status_updated.emit("⏸️ Téléchargement en pause...")
                    self.msleep(500)  # Attendre 500ms avant de vérifier à nouveau
                    
                if self._stop_requested:
                    self.status_updated.emit("⏹️ Téléchargement arrêté par l'utilisateur")
                    return
                    
                # Extraire les métadonnées du fichier GP
                metadata = self.parser.extract_metadata(gp_file)
                
                # Vérifier si un fichier audio correspondant existe déjà
                if self._audio_file_exists(metadata):
                    self.status_updated.emit(f"Ignoré (audio existant): {metadata['title']}")
                    # Ajouter au cache même si on n'a pas téléchargé
                    processed_files.add(gp_file)
                    self._save_cache(cache_file, processed_files)
                else:
                    # Télécharger le fichier audio
                    self.status_updated.emit(f"Téléchargement: {metadata['title']}")
                    success = self.downloader.download_audio(metadata)
                    
                    if success:
                        self.status_updated.emit(f"Téléchargé: {metadata['title']}")
                        # Ajouter au cache
                        processed_files.add(gp_file)
                        self._save_cache(cache_file, processed_files)
                    else:
                        self.status_updated.emit(f"Échec: {metadata['title']}")
                    
                # Mettre à jour la progression
                progress = int((i + 1) / total_files * 100)
                self.progress_updated.emit(progress)
                
            self.download_completed.emit()
            
        except Exception as e:
            self.error_occurred.emit(f"Erreur lors du téléchargement: {str(e)}")
            
    def _should_exclude(self, metadata):
        """Vérifier si un fichier doit être exclu selon les exceptions"""
        if not self.exceptions:
            return False
            
        # Créer une chaîne de recherche avec toutes les métadonnées
        search_text = ' '.join([
            metadata.get('title', ''),
            metadata.get('artist', ''),
            metadata.get('album', ''),
            os.path.basename(metadata.get('file_path', ''))
        ]).lower()
        
        # Vérifier si un mot-clé d'exception est présent
        for exception in self.exceptions:
            if exception.strip().lower() in search_text:
                return True
                
        return False
        
    def _load_cache(self, cache_file):
        """Charger la liste des fichiers déjà traités"""
        processed_files = set()
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        processed_files.add(line.strip())
        except Exception as e:
            print(f"Erreur lors du chargement du cache: {e}")
        return processed_files
        
    def _save_cache(self, cache_file, processed_files):
        """Sauvegarder la liste des fichiers traités"""
        try:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                for file_path in sorted(processed_files):
                    f.write(f"{file_path}\n")
        except Exception as e:
            print(f"Erreur lors de la sauvegarde du cache: {e}")
    
    def _audio_file_exists(self, metadata):
        """Vérifier si un fichier audio correspondant existe déjà"""
        try:
            # Générer le nom de fichier attendu (même logique que dans downloader.py)
            filename_parts = []
            
            if metadata.get('artist') and metadata['artist'].strip():
                filename_parts.append(metadata['artist'].strip())
                
            if metadata.get('title') and metadata['title'].strip():
                title = metadata['title'].strip()
                # Nettoyer le titre
                import re
                title = re.sub(r'\.(gp[3-5x]?|tab)$', '', title, flags=re.IGNORECASE)
                filename_parts.append(title)
                
            if not filename_parts:
                # Fallback: utiliser le nom de fichier original
                file_path = metadata.get('file_path', 'unknown')
                filename_parts.append(Path(file_path).stem)
                
            filename = ' - '.join(filename_parts)
            
            # Nettoyer le nom de fichier (enlever les caractères non autorisés)
            filename = re.sub(r'[<>:"/\\|?*]', '', filename)
            filename = re.sub(r'[\s]+', ' ', filename).strip()
            
            # Limiter la longueur
            if len(filename) > 200:
                filename = filename[:200]
                
            if not filename:
                filename = 'unknown'
            
            # Extensions audio à vérifier
            audio_extensions = ['.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma']
            
            # Vérifier si un fichier avec ce nom existe dans le dossier de sortie
            for ext in audio_extensions:
                audio_file_path = os.path.join(self.output_path, f"{filename}{ext}")
                if os.path.exists(audio_file_path):
                    return True
                    
            return False
            
        except Exception as e:
            print(f"Erreur lors de la vérification du fichier audio: {e}")
            return False


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application"""
    
    def __init__(self):
        super().__init__()
        self.config_file = os.path.join(os.path.expanduser("~"), ".gp_downloader_config.json")
        self.download_worker = None
        self.is_paused = False
        self.init_ui()
        self.load_settings()
        self.setup_icon()
        
    def setup_icon(self):
        """Configurer l'icône de l'application"""
        try:
            # Essayer d'abord le fichier .ico
            icon_path = os.path.join(os.path.dirname(__file__), "app_logo.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
            else:
                # Fallback sur le fichier .png
                icon_path = os.path.join(os.path.dirname(__file__), "app_logo.png")
                if os.path.exists(icon_path):
                    self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
             print(f"Erreur lors du chargement de l'icône: {e}")
     
    def create_menu(self):
        """Créer le menu de l'application"""
        menubar = self.menuBar()
        
        # Menu Outils
        tools_menu = menubar.addMenu('Outils')
        
        # Action pour vider le cache
        clear_cache_action = QAction('Vider le cache', self)
        clear_cache_action.setStatusTip('Vider le cache des fichiers traités')
        clear_cache_action.triggered.connect(self.clear_cache)
        tools_menu.addAction(clear_cache_action)
        
        # Menu Aide
        help_menu = menubar.addMenu('Aide')
        
        # Action À propos
        about_action = QAction('À propos', self)
        about_action.setStatusTip('À propos de GP Audio Downloader')
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def init_ui(self):
        """Initialiser l'interface utilisateur"""
        self.setWindowTitle("GP Audio Downloader")
        self.setGeometry(100, 100, 800, 600)
        
        # Créer le menu
        self.create_menu()
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Titre
        title_label = QLabel("GP Audio Downloader")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        main_layout.addWidget(title_label)
        
        # Section sélection du dossier
        folder_group = QGroupBox("Dossier contenant les fichiers Guitar Pro")
        folder_layout = QHBoxLayout(folder_group)
        
        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setPlaceholderText("Sélectionnez un dossier...")
        self.folder_path_edit.setReadOnly(True)
        
        self.browse_button = QPushButton("Parcourir")
        self.browse_button.clicked.connect(self.browse_folder)
        
        folder_layout.addWidget(self.folder_path_edit)
        folder_layout.addWidget(self.browse_button)
        main_layout.addWidget(folder_group)
        
        # Section dossier de sortie
        output_group = QGroupBox("Dossier de téléchargement")
        output_layout = QHBoxLayout(output_group)
        
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Dossier de téléchargement...")
        self.output_path_edit.setReadOnly(True)
        
        self.output_browse_button = QPushButton("Parcourir")
        self.output_browse_button.clicked.connect(self.browse_output_folder)
        
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(self.output_browse_button)
        main_layout.addWidget(output_group)
        
        # Section exceptions
        exceptions_group = QGroupBox("Exceptions (mots-clés à exclure)")
        exceptions_layout = QVBoxLayout(exceptions_group)
        
        self.exceptions_edit = QTextEdit()
        self.exceptions_edit.setPlaceholderText("Entrez les mots-clés à exclure, un par ligne...\nExemple:\nintro\noutro\nlesson\ntutorial")
        self.exceptions_edit.setMaximumHeight(100)
        self.exceptions_edit.textChanged.connect(self.save_settings)  # Sauvegarder automatiquement
        exceptions_layout.addWidget(self.exceptions_edit)
        
        main_layout.addWidget(exceptions_group)
        
        # Boutons d'action
        buttons_layout = QHBoxLayout()
        
        self.download_button = QPushButton("Commencer le téléchargement")
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.start_download)
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        
        self.pause_button = QPushButton("⏸️ Pause")
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        
        self.stop_button = QPushButton("⏹️ Arrêter")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_download)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        
        buttons_layout.addWidget(self.download_button)
        buttons_layout.addWidget(self.pause_button)
        buttons_layout.addWidget(self.stop_button)
        main_layout.addLayout(buttons_layout)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Zone de statut
        status_group = QGroupBox("Statut")
        status_layout = QVBoxLayout(status_group)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(200)
        status_layout.addWidget(self.status_text)
        
        main_layout.addWidget(status_group)
        
        # Appliquer le style
        self.apply_styles()
        
    def apply_styles(self):
        """Appliquer les styles CSS"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ecf0f1;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: #ecf0f1;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d5dbdb;
            }
            QTextEdit {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
        """)
        
    def browse_folder(self):
        """Ouvrir le dialogue de sélection de dossier"""
        # Utiliser le dernier dossier utilisé comme point de départ
        start_dir = self.folder_path_edit.text() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(
            self, "Sélectionner le dossier contenant les fichiers Guitar Pro", start_dir
        )
        if folder:
            self.folder_path_edit.setText(folder)
            self.save_settings()
            self.check_ready_to_download()
            
    def browse_output_folder(self):
        """Ouvrir le dialogue de sélection du dossier de sortie"""
        # Utiliser le dernier dossier utilisé comme point de départ
        start_dir = self.output_path_edit.text() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(
            self, "Sélectionner le dossier de téléchargement", start_dir
        )
        if folder:
            self.output_path_edit.setText(folder)
            self.save_settings()
            self.check_ready_to_download()
            
    def check_ready_to_download(self):
        """Vérifier si on peut commencer le téléchargement"""
        folder_selected = bool(self.folder_path_edit.text())
        output_selected = bool(self.output_path_edit.text())
        self.download_button.setEnabled(folder_selected and output_selected)
        
    def start_download(self):
        """Commencer le téléchargement"""
        folder_path = self.folder_path_edit.text()
        output_path = self.output_path_edit.text()
        
        if not os.path.exists(folder_path):
            QMessageBox.warning(self, "Erreur", "Le dossier sélectionné n'existe pas.")
            return
            
        if not os.path.exists(output_path):
            QMessageBox.warning(self, "Erreur", "Le dossier de téléchargement n'existe pas.")
            return
            
        # Récupérer les exceptions
        exceptions_text = self.exceptions_edit.toPlainText()
        exceptions = [line.strip() for line in exceptions_text.split('\n') if line.strip()]
        
        # Gérer l'état des boutons
        self.download_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.is_paused = False
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_text.clear()
        
        # Afficher les exceptions actives
        if exceptions:
            self.status_text.append(f"Exceptions actives: {', '.join(exceptions)}")
        
        # Créer et démarrer le worker
        self.download_worker = DownloadWorker(folder_path, output_path, exceptions)
        self.download_worker.progress_updated.connect(self.update_progress)
        self.download_worker.status_updated.connect(self.update_status)
        self.download_worker.download_completed.connect(self.download_finished)
        self.download_worker.error_occurred.connect(self.download_error)
        self.download_worker.start()
        
    def update_progress(self, value):
        """Mettre à jour la barre de progression"""
        self.progress_bar.setValue(value)
        
    def update_status(self, message):
        """Mettre à jour le statut"""
        self.status_text.append(message)
        
    def download_finished(self):
        """Téléchargement terminé"""
        self.progress_bar.setValue(100)
        self.status_text.append("\n✅ Téléchargement terminé avec succès!")
        self.download_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.pause_button.setText("⏸️ Pause")
        self.is_paused = False
        QMessageBox.information(self, "Succès", "Tous les téléchargements sont terminés!")
        
    def download_error(self, error_message):
        """Erreur lors du téléchargement"""
        self.status_text.append(f"\n❌ Erreur: {error_message}")
        self.download_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Erreur", error_message)
        
    def toggle_pause(self):
        """Basculer entre pause et reprise"""
        if self.download_worker and self.download_worker.isRunning():
            if self.is_paused:
                self.download_worker.resume()
                self.pause_button.setText("⏸️ Pause")
                self.is_paused = False
                self.status_text.append("▶️ Téléchargement repris")
            else:
                self.download_worker.pause()
                self.pause_button.setText("▶️ Reprendre")
                self.is_paused = True
                self.status_text.append("⏸️ Téléchargement mis en pause")
                
    def stop_download(self):
        """Arrêter le téléchargement"""
        if self.download_worker and self.download_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirmation",
                "Êtes-vous sûr de vouloir arrêter le téléchargement ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.download_worker.stop()
                self.download_worker.wait(3000)
                self.download_button.setEnabled(True)
                self.pause_button.setEnabled(False)
                self.stop_button.setEnabled(False)
                self.pause_button.setText("⏸️ Pause")
                self.is_paused = False
                self.progress_bar.setVisible(False)
                self.status_text.append("🛑 Téléchargement arrêté par l'utilisateur")
                
    def show_about(self):
        """Afficher les informations sur l'application"""
        QMessageBox.about(
            self,
            "À propos",
            "<h3>GP Audio Downloader</h3>"
            "<p>Version 1.0</p>"
            "<p>Application pour télécharger automatiquement les fichiers audio correspondant aux tablatures Guitar Pro.</p>"
            "<p>Développé avec Python et PySide6</p>"
        )
        
    def clear_cache(self):
        """Vider le cache des fichiers traités"""
        output_path = self.output_path_edit.text()
        
        if not output_path:
            QMessageBox.warning(self, "Attention", "Veuillez d'abord sélectionner un dossier de téléchargement.")
            return
            
        cache_file = os.path.join(output_path, ".gp_downloader_cache.txt")
        
        if not os.path.exists(cache_file):
            QMessageBox.information(self, "Information", "Aucun cache trouvé.")
            return
            
        reply = QMessageBox.question(
            self, 
            "Confirmation", 
            "Êtes-vous sûr de vouloir vider le cache ?\n\nCela forcera le retraitement de tous les fichiers lors du prochain téléchargement.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(cache_file)
                QMessageBox.information(self, "Succès", "Cache vidé avec succès.")
                self.status_text.append("🗑️ Cache vidé - tous les fichiers seront retraités")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible de vider le cache: {str(e)}")
                self.status_text.append(f"❌ Erreur lors du vidage du cache: {str(e)}")
    
    def load_settings(self):
        """Charger les paramètres sauvegardés"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # Charger les chemins de dossiers
                if 'folder_path' in config and os.path.exists(config['folder_path']):
                    self.folder_path_edit.setText(config['folder_path'])
                    
                if 'output_path' in config and os.path.exists(config['output_path']):
                    self.output_path_edit.setText(config['output_path'])
                    
                # Charger les exceptions
                if 'exceptions' in config:
                    self.exceptions_edit.setPlainText('\n'.join(config['exceptions']))
                    
                self.check_ready_to_download()
        except Exception as e:
            print(f"Erreur lors du chargement des paramètres: {e}")
    
    def save_settings(self):
        """Sauvegarder les paramètres actuels"""
        try:
            config = {
                'folder_path': self.folder_path_edit.text(),
                'output_path': self.output_path_edit.text(),
                'exceptions': [line.strip() for line in self.exceptions_edit.toPlainText().split('\n') if line.strip()]
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des paramètres: {e}")
                
    def closeEvent(self, event):
        """Gérer la fermeture de l'application"""
        if self.download_worker and self.download_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirmation",
                "Un téléchargement est en cours. Voulez-vous vraiment quitter ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.download_worker.stop()
                self.download_worker.wait(3000)  # Attendre 3 secondes max
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """Point d'entrée principal"""
    app = QApplication(sys.argv)
    app.setApplicationName("GP Audio Downloader")
    app.setApplicationVersion("1.0")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()