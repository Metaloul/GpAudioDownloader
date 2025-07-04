#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module pour télécharger des fichiers audio basés sur les métadonnées Guitar Pro
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Optional
import yt_dlp
from urllib.parse import quote
from youtube_search import YouTubeSearcher


class AudioDownloader:
    """Classe pour télécharger des fichiers audio"""
    
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.searcher = YouTubeSearcher()
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'extractaudio': True,
            'audioformat': 'mp3',
            'audioquality': '320',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }
        
    def download_audio(self, metadata: Dict[str, str]) -> bool:
        """Télécharger un fichier audio basé sur les métadonnées"""
        try:
            # Générer la requête de recherche
            search_query = self._generate_search_query(metadata)
            
            if not search_query:
                print(f"Impossible de générer une requête pour {metadata.get('file_path', 'fichier inconnu')}")
                return False
                
            # Rechercher sur YouTube
            video_url = self._search_youtube(search_query, metadata)
            
            if not video_url:
                print(f"Aucun résultat trouvé pour: {search_query}")
                return False
                
            # Télécharger le fichier audio
            return self._download_from_url(video_url, metadata)
            
        except Exception as e:
            print(f"Erreur lors du téléchargement: {e}")
            return False
            
    def _generate_search_query(self, metadata: Dict[str, str]) -> str:
        """Générer une requête de recherche optimisée"""
        query_parts = []
        
        # Ajouter l'artiste s'il existe
        if metadata.get('artist') and metadata['artist'].strip():
            artist = self._clean_search_term(metadata['artist'].strip())
            if artist:
                query_parts.append(artist)
            
        # Ajouter le titre s'il existe
        if metadata.get('title') and metadata['title'].strip():
            title = self._clean_search_term(metadata['title'].strip())
            if title:
                query_parts.append(title)
            
        if not query_parts:
            # Fallback: utiliser le nom de fichier
            file_path = metadata.get('file_path', '')
            if file_path:
                file_name = Path(file_path).stem
                file_name = self._clean_search_term(file_name)
                if file_name:
                    query_parts.append(file_name)
                
        # Créer la requête de recherche
        search_query = ' '.join(query_parts)
            
        return search_query
    
    def _clean_search_term(self, term: str) -> str:
        """Nettoyer un terme de recherche"""
        if not term:
            return ''
        
        # Enlever les extensions de fichiers
        term = re.sub(r'\.(gp[3-5x]?|tab)$', '', term, flags=re.IGNORECASE)
        
        # Enlever les caractères spéciaux et parenthèses
        term = re.sub(r'[\[\](){}]', '', term)
        
        # Enlever les informations de version (ver 2, ver 3, etc.)
        term = re.sub(r'\s+ver\s+\d+', '', term, flags=re.IGNORECASE)
        
        # Enlever les informations d'auteur (by xxx)
        term = re.sub(r'\s+by\s+\w+', '', term, flags=re.IGNORECASE)
        
        # Enlever les caractères de contrôle et non-printables
        term = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', term)
        
        # Nettoyer les espaces multiples
        term = re.sub(r'\s+', ' ', term).strip()
        
        return term
        
    def _search_youtube(self, query: str, metadata: Dict[str, str] = None) -> Optional[str]:
        """Rechercher une vidéo sur YouTube avec plusieurs stratégies"""
        if metadata is None:
            metadata = {}
            
        # Extraire artiste et titre des métadonnées
        artist = metadata.get('artist', '').strip()
        title = metadata.get('title', '').strip()
        
        # Essayer plusieurs variantes de la requête
        search_queries = [
            query,
            query.replace(' guitar', ''),  # Sans le mot guitar
            query + ' official',  # Version officielle
            query.replace(' - ', ' '),  # Sans tirets
        ]
        
        for search_query in search_queries:
            try:
                # Utiliser get_best_match pour un meilleur filtrage
                best_url = self.searcher.get_best_match(search_query, artist, title)
                if best_url:
                    return best_url
                            
            except Exception as e:
                print(f"Erreur lors de la recherche YouTube pour '{search_query}': {e}")
                continue
                
        return None
        
    def _download_from_url(self, url: str, metadata: Dict[str, str]) -> bool:
        """Télécharger un fichier audio depuis une URL"""
        try:
            # Créer le dossier de sortie s'il n'existe pas
            os.makedirs(self.output_path, exist_ok=True)
            
            # Générer un nom de fichier sûr
            safe_filename = self._generate_safe_filename(metadata)
            output_template = os.path.join(self.output_path, f'{safe_filename}.%(ext)s')
            
            # Vérifier que le nom de fichier n'est pas vide
            if not safe_filename or safe_filename == 'unknown':
                print(f"Nom de fichier invalide généré pour {url}")
                return False
            
            # Options de téléchargement avec contournement des restrictions YouTube
            download_opts = {
                'format': '(bestaudio[acodec^=opus]/bestaudio)/best',
                'outtmpl': output_template,
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'writeinfojson': False,
                'writethumbnail': False,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'prefer_ffmpeg': True,
                'retries': 3,
                'ignoreerrors': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                },
                'extractor_args': {
                    'youtube': {
                        'skip': ['hls', 'dash'],
                        'player_client': ['android', 'web']
                    }
                }
            }
            
            # Essayer d'abord sans post-processeur
            try:
                with yt_dlp.YoutubeDL(download_opts) as ydl:
                    ydl.download([url])
                    
                # Vérifier que le fichier a été créé et n'est pas vide
                expected_files = [
                    os.path.join(self.output_path, f'{safe_filename}.mp3'),
                    os.path.join(self.output_path, f'{safe_filename}.m4a'),
                    os.path.join(self.output_path, f'{safe_filename}.webm'),
                ]
                
                for file_path in expected_files:
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        print(f"Fichier téléchargé avec succès: {file_path}")
                        return True
                        
                print(f"Aucun fichier valide trouvé après téléchargement de {url}")
                return False
                
            except Exception as inner_e:
                 print(f"Erreur lors du téléchargement: {inner_e}")
                 # Essayer avec une configuration de fallback très simple
                 simple_opts = {
                     'format': 'worst[ext=mp4]/worst',
                     'outtmpl': output_template,
                     'noplaylist': True,
                     'quiet': True,
                     'retries': 2,
                     'ignoreerrors': True,
                     'http_headers': {
                         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                     },
                     'extractor_args': {
                         'youtube': {
                             'player_client': ['android']
                         }
                     }
                 }
                 
                 try:
                     with yt_dlp.YoutubeDL(simple_opts) as ydl:
                         ydl.download([url])
                         
                     # Vérifier que le fichier a été créé
                     for ext in ['.m4a', '.mp4', '.webm']:
                         file_path = os.path.join(self.output_path, f'{safe_filename}{ext}')
                         if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                             print(f"Fichier téléchargé avec succès (fallback): {file_path}")
                             return True
                             
                     return False
                 except Exception as simple_e:
                     print(f"Échec même avec configuration simple: {simple_e}")
                     return False
                
        except Exception as e:
            print(f"Erreur générale lors du téléchargement depuis {url}: {e}")
            return False
            
    def _generate_safe_filename(self, metadata: Dict[str, str]) -> str:
        """Générer un nom de fichier sûr"""
        # Construire le nom de fichier
        filename_parts = []
        
        if metadata.get('artist') and metadata['artist'].strip():
            filename_parts.append(metadata['artist'].strip())
            
        if metadata.get('title') and metadata['title'].strip():
            title = metadata['title'].strip()
            # Nettoyer le titre
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
            
        return filename or 'unknown'
        
    def test_connection(self) -> bool:
        """Tester la connexion et la disponibilité de yt-dlp"""
        try:
            test_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'default_search': 'ytsearch1:',
            }
            
            with yt_dlp.YoutubeDL(test_opts) as ydl:
                # Test simple avec une recherche basique
                ydl.extract_info('test', download=False)
                
            return True
            
        except Exception as e:
            print(f"Erreur de connexion: {e}")
            return False
            
    def get_video_info(self, url: str) -> Optional[Dict]:
        """Obtenir les informations d'une vidéo"""
        try:
            info_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', ''),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', ''),
                    'view_count': info.get('view_count', 0),
                }
                
        except Exception as e:
            print(f"Erreur lors de l'extraction des infos: {e}")
            return None