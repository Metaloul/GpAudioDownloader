#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module pour rechercher des vidéos YouTube sans API key
"""

import requests
import re
import json
from typing import List, Dict, Optional
from urllib.parse import quote, urlencode

class YouTubeSearcher:
    """Classe pour rechercher des vidéos YouTube"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Rechercher des vidéos YouTube"""
        try:
            # Méthode 1: Scraping de la page de recherche YouTube
            results = self._search_youtube_scraping(query, max_results)
            if results:
                return results
            
            # Méthode 2: Utiliser Invidious (instance publique)
            results = self._search_invidious(query, max_results)
            if results:
                return results
                
            return []
            
        except Exception as e:
            print(f"Erreur lors de la recherche: {e}")
            return []
    
    def _search_youtube_scraping(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Rechercher en scrapant la page YouTube"""
        try:
            search_url = f"https://www.youtube.com/results?search_query={quote(query)}"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code != 200:
                return []
            
            # Extraire les données JSON de la page
            pattern = r'var ytInitialData = ({.*?});'
            match = re.search(pattern, response.text)
            
            if not match:
                return []
            
            data = json.loads(match.group(1))
            
            # Naviguer dans la structure JSON pour trouver les vidéos
            results = []
            try:
                contents = data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']
                
                for section in contents:
                    if 'itemSectionRenderer' in section:
                        items = section['itemSectionRenderer']['contents']
                        
                        for item in items:
                            if 'videoRenderer' in item:
                                video = item['videoRenderer']
                                
                                video_id = video.get('videoId')
                                title = ''
                                
                                if 'title' in video and 'runs' in video['title']:
                                    title = ''.join([run['text'] for run in video['title']['runs']])
                                
                                if video_id and title:
                                    results.append({
                                        'id': video_id,
                                        'title': title,
                                        'url': f'https://www.youtube.com/watch?v={video_id}'
                                    })
                                    
                                    if len(results) >= max_results:
                                        break
                        
                        if len(results) >= max_results:
                            break
            
            except (KeyError, TypeError):
                pass
            
            return results
            
        except Exception as e:
            print(f"Erreur scraping YouTube: {e}")
            return []
    
    def _search_invidious(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Rechercher via une instance Invidious"""
        invidious_instances = [
            'https://invidious.io',
            'https://yewtu.be',
            'https://invidious.snopyta.org',
            'https://invidious.kavin.rocks'
        ]
        
        for instance in invidious_instances:
            try:
                api_url = f"{instance}/api/v1/search"
                params = {
                    'q': query,
                    'type': 'video',
                    'sort_by': 'relevance'
                }
                
                response = self.session.get(api_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    results = []
                    for item in data[:max_results]:
                        if item.get('type') == 'video':
                            results.append({
                                'id': item.get('videoId', ''),
                                'title': item.get('title', ''),
                                'url': f"https://www.youtube.com/watch?v={item.get('videoId', '')}"
                            })
                    
                    if results:
                        return results
                        
            except Exception as e:
                print(f"Erreur avec instance Invidious {instance}: {e}")
                continue
        
        return []
    
    def get_best_match(self, query: str, artist: str = '', title: str = '') -> Optional[str]:
        """Obtenir la meilleure correspondance pour une recherche"""
        results = self.search(query, max_results=15)
        
        if not results:
            return None
        
        # Scorer les résultats
        scored_results = []
        
        for result in results:
            score = 0
            result_title = result['title'].lower()
            
            # Bonus si l'artiste est dans le titre (exact match)
            if artist and artist.lower() in result_title:
                # Bonus supplémentaire si c'est au début du titre
                if result_title.startswith(artist.lower()):
                    score += 5
                else:
                    score += 3
            
            # Bonus si le titre est dans le titre
            if title and title.lower() in result_title:
                score += 4
            
            # Gros bonus pour les versions officielles
            official_keywords = ['official', 'music video', 'official video', 'official music video']
            if any(word in result_title for word in official_keywords):
                score += 4
            
            # Bonus pour les chaînes officielles (VEVO, etc.)
            if any(word in result_title for word in ['vevo', 'records']):
                score += 2
            
            # Bonus pour les vidéos avec paroles officielles
            if any(word in result_title for word in ['lyrics', 'lyric video']):
                score += 1
            
            # Gros malus pour les covers et versions alternatives
            cover_keywords = [
                'cover', 'covers', 'covered by', 'covering',
                'remix', 'remixed', 'remix by',
                'karaoke', 'instrumental', 'backing track',
                'acoustic version', 'acoustic cover',
                'piano version', 'guitar cover',
                'live version', 'live at', 'live from', 'concert',
                'tribute', 'tribute to',
                'reaction', 'reacts to',
                'tutorial', 'how to play',
                'cover version', 'version by'
            ]
            
            for keyword in cover_keywords:
                if keyword in result_title:
                    if keyword in ['live', 'concert']:
                        score -= 2  # Malus modéré pour les lives
                    elif keyword in ['cover', 'remix', 'karaoke']:
                        score -= 4  # Gros malus pour covers/remixes
                    else:
                        score -= 3
            
            # Malus pour les titres trop longs (souvent des compilations)
            if len(result_title) > 100:
                score -= 1
            
            # Malus pour les titres avec beaucoup de caractères spéciaux
            special_chars = result_title.count('|') + result_title.count('-') + result_title.count('(')
            if special_chars > 3:
                score -= 1
            
            # Bonus pour les titres courts et précis
            if len(result_title) < 50 and artist and title:
                if artist.lower() in result_title and title.lower() in result_title:
                    score += 2
            
            scored_results.append((score, result))
        
        # Trier par score décroissant
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # Debug: afficher les scores des 3 premiers résultats
        print(f"\nTop 3 résultats pour '{query}':")
        for i, (score, result) in enumerate(scored_results[:3]):
            print(f"{i+1}. Score: {score} - {result['title']}")
        
        # Retourner la meilleure URL si le score est positif
        if scored_results and scored_results[0][0] > 0:
            return scored_results[0][1]['url']
        
        # Si aucun résultat n'a un score positif, prendre le premier quand même
        if scored_results:
            return scored_results[0][1]['url']
        
        return None

# Test de la classe
if __name__ == "__main__":
    searcher = YouTubeSearcher()
    results = searcher.search("metallica nothing else matters")
    
    print(f"Résultats trouvés: {len(results)}")
    for i, result in enumerate(results[:3]):
        print(f"{i+1}. {result['title']}")
        print(f"   URL: {result['url']}")