#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module pour parser les fichiers Guitar Pro et extraire les métadonnées
"""

import os
import struct
from pathlib import Path
from typing import Dict, List, Optional


class GuitarProParser:
    """Parser pour les fichiers Guitar Pro"""
    
    # Extensions de fichiers Guitar Pro supportées
    GP_EXTENSIONS = ['.gp3', '.gp4', '.gp5', '.gpx', '.gp']
    
    def __init__(self):
        pass
        
    def find_gp_files(self, folder_path: str) -> List[str]:
        """Trouver tous les fichiers Guitar Pro dans un dossier"""
        gp_files = []
        folder = Path(folder_path)
        
        if not folder.exists():
            return gp_files
            
        # Rechercher récursivement dans tous les sous-dossiers
        for file_path in folder.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.GP_EXTENSIONS:
                gp_files.append(str(file_path))
                
        return sorted(gp_files)
        
    def extract_metadata(self, file_path: str) -> Dict[str, str]:
        """Extraire les métadonnées d'un fichier Guitar Pro"""
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext in ['.gp3', '.gp4', '.gp5']:
                return self._parse_gp345(file_path)
            elif file_ext == '.gpx':
                return self._parse_gpx(file_path)
            else:
                # Fallback: utiliser le nom de fichier
                return self._fallback_metadata(file_path)
                
        except Exception as e:
            print(f"Erreur lors du parsing de {file_path}: {e}")
            return self._fallback_metadata(file_path)
            
    def _parse_gp345(self, file_path: str) -> Dict[str, str]:
        """Parser pour les fichiers GP3, GP4, GP5"""
        metadata = {
            'title': '',
            'artist': '',
            'album': '',
            'file_path': file_path
        }
        
        try:
            with open(file_path, 'rb') as f:
                # Lire l'en-tête
                header = f.read(30)
                
                # Vérifier la version
                if b'FICHIER GUITAR PRO' in header:
                    # Lire les métadonnées de base
                    metadata.update(self._read_gp_strings(f))
                    
        except Exception as e:
            print(f"Erreur lors du parsing GP3/4/5: {e}")
            
        # Si pas de titre trouvé, utiliser le nom de fichier
        if not metadata['title']:
            metadata['title'] = Path(file_path).stem
            
        return metadata
        
    def _parse_gpx(self, file_path: str) -> Dict[str, str]:
        """Parser pour les fichiers GPX (Guitar Pro 6+)"""
        metadata = {
            'title': '',
            'artist': '',
            'album': '',
            'file_path': file_path
        }
        
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            
            # Vérifier d'abord si c'est un fichier ZIP valide
            if not zipfile.is_zipfile(file_path):
                # Si ce n'est pas un ZIP, utiliser le fallback
                return self._fallback_metadata(file_path)
            
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # Lire le fichier score.gpif
                if 'score.gpif' in zip_file.namelist():
                    with zip_file.open('score.gpif') as gpif_file:
                        content = gpif_file.read().decode('utf-8')
                        root = ET.fromstring(content)
                        
                        # Extraire les métadonnées du XML
                        score_info = root.find('.//ScoreInfo')
                        if score_info is not None:
                            title_elem = score_info.find('Title')
                            if title_elem is not None:
                                metadata['title'] = title_elem.text or ''
                                
                            artist_elem = score_info.find('Artist')
                            if artist_elem is not None:
                                metadata['artist'] = artist_elem.text or ''
                                
                            album_elem = score_info.find('Album')
                            if album_elem is not None:
                                metadata['album'] = album_elem.text or ''
                                
        except zipfile.BadZipFile:
            # Fichier GPX corrompu ou non-ZIP, utiliser le fallback
            return self._fallback_metadata(file_path)
        except Exception as e:
            print(f"Erreur lors du parsing GPX: {e}")
            
        # Si pas de titre trouvé, utiliser le nom de fichier
        if not metadata['title']:
            metadata['title'] = Path(file_path).stem
            
        return metadata
        
    def _read_gp_strings(self, file_handle) -> Dict[str, str]:
        """Lire les chaînes de caractères des fichiers GP"""
        metadata = {
            'title': '',
            'artist': '',
            'album': ''
        }
        
        try:
            # Sauter l'en-tête
            file_handle.seek(30)
            
            # Lire le titre
            title_length = struct.unpack('<I', file_handle.read(4))[0]
            if title_length > 0 and title_length < 1000:  # Sanity check
                title_bytes = file_handle.read(title_length)
                metadata['title'] = title_bytes.decode('latin-1', errors='ignore').strip()
                
            # Lire le sous-titre (souvent l'artiste)
            subtitle_length = struct.unpack('<I', file_handle.read(4))[0]
            if subtitle_length > 0 and subtitle_length < 1000:
                subtitle_bytes = file_handle.read(subtitle_length)
                metadata['artist'] = subtitle_bytes.decode('latin-1', errors='ignore').strip()
                
            # Lire l'artiste
            artist_length = struct.unpack('<I', file_handle.read(4))[0]
            if artist_length > 0 and artist_length < 1000:
                artist_bytes = file_handle.read(artist_length)
                if not metadata['artist']:  # Si pas d'artiste dans le sous-titre
                    metadata['artist'] = artist_bytes.decode('latin-1', errors='ignore').strip()
                    
            # Lire l'album
            album_length = struct.unpack('<I', file_handle.read(4))[0]
            if album_length > 0 and album_length < 1000:
                album_bytes = file_handle.read(album_length)
                metadata['album'] = album_bytes.decode('latin-1', errors='ignore').strip()
                
        except Exception as e:
            print(f"Erreur lors de la lecture des chaînes GP: {e}")
            
        # Nettoyer les métadonnées
        for key in ['title', 'artist', 'album']:
            if metadata.get(key):
                metadata[key] = self._clean_string(metadata[key])
        
        return metadata
    
    def _clean_string(self, text: str) -> str:
        """Nettoyer une chaîne de caractères des caractères spéciaux"""
        if not text:
            return ''
        
        import string
        import re
        
        # Enlever les caractères de contrôle et non-printables
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        # Enlever les caractères spéciaux problématiques
        cleaned = re.sub(r'[☺♂♀◄►▲↔▬§♀♂Ò☼]', '', cleaned)
        
        # Enlever les placeholders comme %TITLE%, %ARTIST%, etc.
        cleaned = re.sub(r'%[A-Z]+%', '', cleaned)
        
        # Enlever les séquences de caractères corrompus
        cleaned = re.sub(r'dÿ', '', cleaned)
        cleaned = re.sub(r'Al♀', '', cleaned)
        cleaned = re.sub(r'rv', '', cleaned)
        
        # Garder seulement les caractères ASCII printables et quelques caractères étendus
        cleaned = ''.join(c for c in cleaned if ord(c) >= 32 and ord(c) <= 126 or c in 'àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞß')
        
        # Nettoyer les espaces multiples
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Si la chaîne est vide ou ne contient que des caractères spéciaux, retourner vide
        if not cleaned or len(cleaned.strip()) == 0:
            return ''
        
        # Si la chaîne contient encore des patterns suspects, la rejeter
        if re.search(r'[\x00-\x1f]|Words by|Music by|Copyright|International Copyright Secured', cleaned):
            return ''
        
        return cleaned
        
    def _fallback_metadata(self, file_path: str) -> Dict[str, str]:
        """Métadonnées de fallback basées sur le nom de fichier"""
        file_name = Path(file_path).stem
        
        # Nettoyer le nom de fichier des caractères spéciaux
        file_name = self._clean_string(file_name)
        
        # Essayer de parser le nom de fichier (format: Artiste - Titre)
        if ' - ' in file_name:
            parts = file_name.split(' - ', 1)
            artist = self._clean_string(parts[0].strip())
            title = self._clean_string(parts[1].strip())
        else:
            artist = ''
            title = self._clean_string(file_name)
            
        return {
            'title': title,
            'artist': artist,
            'album': '',
            'file_path': file_path
        }
        
    def get_search_query(self, metadata: Dict[str, str]) -> str:
        """Générer une requête de recherche pour le téléchargement audio"""
        query_parts = []
        
        if metadata.get('artist'):
            query_parts.append(metadata['artist'])
            
        if metadata.get('title'):
            query_parts.append(metadata['title'])
            
        if not query_parts:
            # Utiliser le nom de fichier comme fallback
            file_name = Path(metadata['file_path']).stem
            query_parts.append(file_name)
            
        return ' '.join(query_parts)