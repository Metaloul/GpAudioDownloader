#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour diagnostiquer les problèmes avec yt-dlp
"""

import yt_dlp
import sys

def test_ytdlp():
    """Tester la fonctionnalité de yt-dlp"""
    print("=== Test de yt-dlp ===")
    
    try:
        # Test 1: Version de yt-dlp
        print(f"Version yt-dlp: {yt_dlp.version.__version__}")
        
        # Test 2: Recherche simple
        print("\nTest de recherche simple...")
        search_opts = {
            'quiet': False,
            'no_warnings': False,
            'extract_flat': True,
            'default_search': 'ytsearch3:',
        }
        
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            query = "metallica nothing else matters"
            print(f"Recherche: {query}")
            
            try:
                result = ydl.extract_info(query, download=False)
                
                if result and 'entries' in result:
                    print(f"Nombre de résultats: {len(result['entries'])}")
                    
                    for i, entry in enumerate(result['entries'][:3]):
                        if entry:
                            print(f"  {i+1}. {entry.get('title', 'Titre inconnu')}")
                            print(f"     ID: {entry.get('id', 'N/A')}")
                            print(f"     URL: {entry.get('url', 'N/A')}")
                else:
                    print("Aucun résultat trouvé")
                    
            except Exception as e:
                print(f"Erreur lors de la recherche: {e}")
                
        # Test 3: Test de connectivité
        print("\nTest de connectivité...")
        test_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(test_opts) as ydl:
            try:
                # Tester avec une URL YouTube directe
                test_url = "https://www.youtube.com/watch?v=tAGnKpE4NCI"  # Metallica - Nothing Else Matters
                info = ydl.extract_info(test_url, download=False)
                print(f"Test URL directe réussi: {info.get('title', 'Titre inconnu')}")
            except Exception as e:
                print(f"Erreur test URL directe: {e}")
                
    except Exception as e:
        print(f"Erreur générale: {e}")
        return False
        
    return True

if __name__ == "__main__":
    success = test_ytdlp()
    sys.exit(0 if success else 1)