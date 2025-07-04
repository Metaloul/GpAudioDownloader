#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de build pour créer l'exécutable GP Audio Downloader
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(command, description):
    """Exécuter une commande et afficher le résultat"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} terminé avec succès")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de {description}:")
        print(f"Code de retour: {e.returncode}")
        print(f"Sortie d'erreur: {e.stderr}")
        return False


def install_dependencies():
    """Installer les dépendances"""
    return run_command(
        "pip install -r requirements.txt",
        "Installation des dépendances"
    )


def create_executable():
    """Créer l'exécutable avec PyInstaller"""
    # Commande PyInstaller avec options optimisées
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",  # Un seul fichier exécutable
        "--windowed",  # Pas de console (interface graphique)
        "--name=GPAudioDownloader",  # Nom de l'exécutable
        "--icon=icon.ico",  # Icône (si disponible)
        "--add-data=*.py;.",  # Inclure tous les fichiers Python
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=yt_dlp",
        "--hidden-import=yt_dlp.extractor",
        "--collect-all=yt_dlp",
        "--noconfirm",  # Écraser sans demander
        "main.py"
    ]
    
    # Si pas d'icône, enlever l'option
    if not Path("icon.ico").exists():
        pyinstaller_cmd = [cmd for cmd in pyinstaller_cmd if not cmd.startswith("--icon")]
    
    command = " ".join(pyinstaller_cmd)
    return run_command(command, "Création de l'exécutable")


def create_icon():
    """Créer une icône simple en SVG et la convertir (optionnel)"""
    icon_svg = '''
<svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <rect width="64" height="64" rx="8" fill="#3498db"/>
  <text x="32" y="40" font-family="Arial, sans-serif" font-size="24" font-weight="bold" 
        text-anchor="middle" fill="white">GP</text>
  <circle cx="48" cy="16" r="6" fill="#e74c3c"/>
  <path d="M42 16 L54 16 M48 10 L48 22" stroke="white" stroke-width="2"/>
</svg>
'''
    
    try:
        with open("icon.svg", "w", encoding="utf-8") as f:
            f.write(icon_svg)
        print("✅ Icône SVG créée")
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la création de l'icône: {e}")
        return False


def clean_build_files():
    """Nettoyer les fichiers de build temporaires"""
    import shutil
    
    dirs_to_clean = ["build", "__pycache__"]
    files_to_clean = ["*.spec"]
    
    for dir_name in dirs_to_clean:
        if Path(dir_name).exists():
            try:
                shutil.rmtree(dir_name)
                print(f"✅ Dossier {dir_name} supprimé")
            except Exception as e:
                print(f"❌ Erreur lors de la suppression de {dir_name}: {e}")
    
    # Nettoyer les fichiers .spec
    for spec_file in Path(".").glob("*.spec"):
        try:
            spec_file.unlink()
            print(f"✅ Fichier {spec_file} supprimé")
        except Exception as e:
            print(f"❌ Erreur lors de la suppression de {spec_file}: {e}")


def main():
    """Fonction principale de build"""
    print("🚀 Build de GP Audio Downloader")
    print("=" * 50)
    
    # Vérifier que nous sommes dans le bon dossier
    if not Path("main.py").exists():
        print("❌ Erreur: main.py non trouvé. Assurez-vous d'être dans le bon dossier.")
        sys.exit(1)
    
    # Étapes de build
    steps = [
        ("Création de l'icône", create_icon),
        ("Installation des dépendances", install_dependencies),
        ("Création de l'exécutable", create_executable),
    ]
    
    success = True
    for step_name, step_func in steps:
        if not step_func():
            print(f"\n❌ Échec lors de l'étape: {step_name}")
            success = False
            break
    
    if success:
        print("\n🎉 Build terminé avec succès!")
        print("📁 L'exécutable se trouve dans le dossier 'dist/'")
        
        # Afficher la taille du fichier
        exe_path = Path("dist/GPAudioDownloader.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"📊 Taille de l'exécutable: {size_mb:.1f} MB")
    else:
        print("\n❌ Build échoué")
        sys.exit(1)
    
    # Proposer de nettoyer
    response = input("\n🧹 Voulez-vous nettoyer les fichiers temporaires? (o/N): ")
    if response.lower() in ['o', 'oui', 'y', 'yes']:
        clean_build_files()
        print("✅ Nettoyage terminé")


if __name__ == "__main__":
    main()