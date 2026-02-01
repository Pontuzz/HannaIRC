#!/usr/bin/env python3
"""
Query Shoko Server for anime metadata and inject into knowledge base.
Shoko provides enriched anime data with AniDB integration.
"""

import xml.etree.ElementTree as ET
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import requests

# Shoko Server configuration
SHOKO_HOST = "your-shoko-server.local"  # e.g., "192.168.1.21"
SHOKO_PORT = 8112
SHOKO_BASE_URL = f"http://{SHOKO_HOST}:{SHOKO_PORT}/api/v3"

# Fallback to XML if Shoko is unavailable
XML_FILE = Path(__file__).parent.parent / "anime-titles.xml"
WEBHOOK_URL = "http://your-n8n-instance/webhook/teachhanna"  # Your n8n TeachHanna webhook

def check_shoko_health() -> bool:
    """Check if Shoko Server is available."""
    try:
        response = requests.get(f"{SHOKO_BASE_URL}/series", timeout=3)
        return response.status_code == 200
    except:
        return False

def search_shoko(query: str) -> Optional[Dict]:
    """
    Query Shoko Server for anime.
    Returns enriched anime data with AniDB links.
    """
    if not check_shoko_health():
        return None
    
    try:
        # Search Shoko for anime matching query
        response = requests.get(
            f"{SHOKO_BASE_URL}/search",
            params={"query": query, "limit": 1},
            timeout=5
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        if not data or not isinstance(data, list) or len(data) == 0:
            return None
        
        anime = data[0]
        
        # Extract relevant fields
        result = {
            "id": anime.get("id"),
            "name": anime.get("name", query),
            "description": anime.get("description", ""),
            "type": anime.get("type", "Unknown"),
            "year": anime.get("year"),
            "episodes": anime.get("episodeCount"),
            "anidb_id": anime.get("anidbId"),
            "anidb_url": f"https://anidb.net/?aid={anime.get('anidbId')}" if anime.get('anidbId') else None,
            "shoko_url": f"http://{SHOKO_HOST}:{SHOKO_PORT}/#/anime/{anime.get('id')}" if anime.get('id') else None
        }
        
        return result
    except Exception as e:
        print(f"⚠️  Shoko search error: {e}")
        return None

def parse_anime_titles(xml_path: Path) -> Dict:
    """
    Parse anime-titles.xml and build a lookup dictionary.
    
    Returns dict: {
        'abbreviations': {'jjk': 6594, 'op': 21, ...},
        'titles': {'Jujutsu Kaisen': 6594, ...},
        'anime_data': {6594: {'titles': [...], 'aid': 6594}, ...}
    }
    """
    if not xml_path.exists():
        print(f"❌ File not found: {xml_path}")
        return {}
    
    print(f"📖 Parsing {xml_path}...")
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    lookup = {
        'abbreviations': {},
        'titles': {},
        'anime_data': {}
    }
    
    for anime_elem in root.findall('anime'):
        aid = anime_elem.get('aid')
        if not aid:
            continue
        
        aid = int(aid)
        titles_list = []
        main_title = None
        
        for title_elem in anime_elem.findall('title'):
            title_text = title_elem.text
            title_type = title_elem.get('type', 'unknown')
            lang = title_elem.get('{http://www.w3.org/XML/1998/namespace}lang', 'unknown')
            
            if not title_text:
                continue
            
            titles_list.append({
                'text': title_text,
                'type': title_type,
                'lang': lang
            })
            
            # Store main title (usually the first one or type='main')
            if title_type == 'main' or main_title is None:
                main_title = title_text
            
            # Add to lookup: full title
            lookup['titles'][title_text.lower()] = aid
            
            # Add to lookup: abbreviations (type='short')
            if title_type == 'short':
                lookup['abbreviations'][title_text.lower()] = aid
        
        # Store anime data
        lookup['anime_data'][aid] = {
            'aid': aid,
            'main_title': main_title,
            'titles': titles_list,
            'anidb_url': f"https://anidb.net/?aid={aid}"
        }
    
    print(f"✅ Loaded {len(lookup['anime_data'])} anime")
    print(f"   - {len(lookup['abbreviations'])} abbreviations")
    print(f"   - {len(lookup['titles'])} total titles")
    
    return lookup

def search_anime(lookup: Dict, query: str) -> List[Tuple[int, str, str]]:
    """
    Search for anime by abbreviation or title.
    Returns list of (aid, main_title, anidb_url) tuples.
    """
    query_lower = query.lower()
    results = []
    
    # Exact abbreviation match (highest priority)
    if query_lower in lookup['abbreviations']:
        aid = lookup['abbreviations'][query_lower]
        anime = lookup['anime_data'][aid]
        return [(aid, anime['main_title'], anime['anidb_url'])]
    
    # Exact title match
    if query_lower in lookup['titles']:
        aid = lookup['titles'][query_lower]
        anime = lookup['anime_data'][aid]
        return [(aid, anime['main_title'], anime['anidb_url'])]
    
    # Partial match in abbreviations
    for abbr, aid in lookup['abbreviations'].items():
        if query_lower in abbr or abbr in query_lower:
            anime = lookup['anime_data'][aid]
            results.append((aid, anime['main_title'], anime['anidb_url']))
    
    # Partial match in titles
    for title, aid in lookup['titles'].items():
        if query_lower in title and (aid, title, lookup['anime_data'][aid]['anidb_url']) not in results:
            anime = lookup['anime_data'][aid]
            results.append((aid, anime['main_title'], anime['anidb_url']))
    
    return results[:10]  # Return top 10 matches

def inject_to_knowledge_base(lookup: Dict) -> None:
    """
    Inject anime metadata into TeachHanna webhook for Qdrant storage.
    """
    print(f"📤 Injecting anime metadata to knowledge base...")
    
    success_count = 0
    error_count = 0
    total = len(lookup['anime_data'])
    
    for idx, (aid, anime_data) in enumerate(lookup['anime_data'].items(), 1):
        if idx % 500 == 0:
            print(f"   [{idx}/{total}] {success_count} success, {error_count} errors...")
        titles_str = ", ".join([t['text'] for t in anime_data['titles']])
        
        payload = {
            "id": str(uuid.uuid4()),
            "text": f"{anime_data['main_title']} - {titles_str}",
            "url": anime_data['anidb_url'],
            "title": anime_data['main_title'],
            "source_type": "anidb_metadata",
            "confidence": 0.95,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sourceUser": None,
            "tags": ["anime", "anidb", "metadata"],
            "related_entities": [t['text'] for t in anime_data['titles'][:5]]
        }
        
        try:
            response = requests.post(WEBHOOK_URL, json=payload, timeout=5)
            if response.status_code in [200, 201]:
                success_count += 1
            else:
                error_count += 1
                print(f"⚠️  HTTP {response.status_code} for {anime_data['main_title']}")
        except Exception as e:
            error_count += 1
            print(f"❌ Error for {anime_data['main_title']}: {e}")
    
    print(f"✅ Injection complete: {success_count} success, {error_count} errors")

def main():
    import sys
    
    # Load lookup
    lookup = parse_anime_titles(XML_FILE)
    if not lookup:
        return
    
    # Command-line interface
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"\n🔍 Searching for: '{query}'")
        results = search_anime(lookup, query)
        
        if results:
            for aid, title, url in results:
                print(f"  ✓ {title} (AID: {aid})")
                print(f"    {url}")
        else:
            print("  ❌ No results found")
    else:
        # Interactive mode
        print("\n" + "="*60)
        print("Anime Lookup Database Ready")
        print("="*60)
        print("Commands:")
        print("  search <query>  - Search for anime")
        print("  inject          - Inject metadata to knowledge base")
        print("  quit            - Exit")
        print("="*60 + "\n")
        
        while True:
            try:
                user_input = input(">>> ").strip()
                
                if user_input.lower() == 'quit':
                    break
                elif user_input.lower() == 'inject':
                    inject_to_knowledge_base(lookup)
                elif user_input.lower().startswith('search '):
                    query = user_input[7:].strip()
                    results = search_anime(lookup, query)
                    if results:
                        for aid, title, url in results:
                            print(f"✓ {title} (AID: {aid}) - {url}")
                    else:
                        print("❌ No results found")
                else:
                    # Default: treat as search query
                    results = search_anime(lookup, user_input)
                    if results:
                        for aid, title, url in results:
                            print(f"✓ {title} (AID: {aid})")
                    else:
                        print("❌ No results found")
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
