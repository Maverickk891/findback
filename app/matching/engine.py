import re
from datetime import datetime
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config import Config
from app.models import get_db_connection

# Domain-specific synonym dictionary to assist matching
SYNONYMS = {
    'wallet': ['purse', 'billfold', 'cardholder', 'pouch', 'money clip'],
    'phone': ['mobile', 'cellphone', 'smartphone', 'iphone', 'android', 'galaxy', 'oneplus'],
    'laptop': ['notebook', 'macbook', 'thinkpad', 'computer', 'chromebook', 'dell', 'hp', 'lenovo'],
    'bag': ['backpack', 'rucksack', 'handbag', 'tote', 'duffel', 'knapsack'],
    'earphones': ['earbuds', 'airpods', 'headphones', 'headset', 'buds', 'tws'],
    'id': ['identity', 'college id', 'student id', 'campus card', 'badge', 'card', 'license'],
    'keys': ['keychain', 'keyring', 'room key', 'bike key', 'car key'],
    'watch': ['smartwatch', 'apple watch', 'fitbit', 'timepiece', 'chronograph', 'band'],
    'glasses': ['spectacles', 'sunglasses', 'shades', 'frames', 'specs'],
    'bottle': ['flask', 'tumbler', 'thermos', 'sipper'],
    'charger': ['adapter', 'power bank', 'cable', 'cord', 'power brick']
}

def preprocess_text(text):
    if not text:
        return ""
    text = text.lower()
    # Normalize punctuation
    text = re.sub(r'[^\w\s]', ' ', text)
    tokens = text.split()
    
    # Expand synonyms
    expanded_tokens = list(tokens)
    for token in tokens:
        for canonical, syn_list in SYNONYMS.items():
            if token == canonical or token in syn_list:
                expanded_tokens.append(canonical)
                expanded_tokens.extend(syn_list[:2])
                
    return " ".join(expanded_tokens)

def calculate_text_similarity(text1, text2):
    p1 = preprocess_text(text1)
    p2 = preprocess_text(text2)
    
    if not p1 or not p2:
        return 0.0, []
        
    try:
        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform([p1, p2])
        score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        score = float(score) * 100.0
        
        # Identify common informative tokens
        feature_names = vectorizer.get_feature_names_out()
        v1 = tfidf_matrix[0].toarray()[0]
        v2 = tfidf_matrix[1].toarray()[0]
        shared = []
        for i, feat in enumerate(feature_names):
            if v1[i] > 0 and v2[i] > 0 and len(feat) > 2:
                shared.append(feat)
                
        return min(100.0, max(0.0, score)), shared[:5]
    except Exception:
        # Fallback if vocabulary only has stop words
        s1 = set(p1.split())
        s2 = set(p2.split())
        overlap = s1.intersection(s2)
        if not s1 or not s2:
            return 0.0, []
        jaccard = (len(overlap) / len(s1.union(s2))) * 100.0
        return min(100.0, jaccard), list(overlap)[:5]

def calculate_category_similarity(cat1, cat2):
    if not cat1 or not cat2:
        return 0.0
    c1 = cat1.strip().lower()
    c2 = cat2.strip().lower()
    if c1 == c2:
        return 100.0
    # Soft category groupings
    groupings = [
        {'electronics', 'gadgets', 'computers', 'mobile accessories'},
        {'wallets & bags', 'accessories', 'luggage', 'bags', 'wallets'},
        {'documents & ids', 'identity cards', 'cards', 'keys'},
        {'clothing', 'wearables', 'jewelry & watches'}
    ]
    for grp in groupings:
        if c1 in grp and c2 in grp:
            return 70.0
    return 0.0

def calculate_location_similarity(loc1, loc2):
    if not loc1 or not loc2:
        return 0.0
    l1 = loc1.lower().strip()
    l2 = loc2.lower().strip()
    
    if l1 == l2:
        return 100.0
        
    # Substring check
    if l1 in l2 or l2 in l1:
        return 90.0
        
    # Overlap on location tokens
    tokens1 = set(re.findall(r'\w+', l1))
    tokens2 = set(re.findall(r'\w+', l2))
    
    # Filter common insignificant words
    noise = {'near', 'at', 'in', 'the', 'block', 'room', 'area', 'beside', 'opposite'}
    t1 = tokens1 - noise
    t2 = tokens2 - noise
    
    if not t1 or not t2:
        t1, t2 = tokens1, tokens2
        
    overlap = t1.intersection(t2)
    if overlap:
        min_len = min(len(t1), len(t2))
        overlap_coeff = (len(overlap) / min_len) * 100.0 if min_len > 0 else 0
        jaccard = (len(overlap) / len(t1.union(t2))) * 100.0
        
        if overlap_coeff >= 70.0:
            return min(100.0, max(85.0, overlap_coeff))
        return min(100.0, max(50.0, 0.6 * overlap_coeff + 0.4 * jaccard))
        
    return 0.0

def calculate_date_similarity(date_str1, date_str2):
    try:
        # Handle string dates YYYY-MM-DD
        if isinstance(date_str1, str):
            d1 = datetime.strptime(date_str1.split()[0], '%Y-%m-%d').date()
        else:
            d1 = date_str1
            
        if isinstance(date_str2, str):
            d2 = datetime.strptime(date_str2.split()[0], '%Y-%m-%d').date()
        else:
            d2 = date_str2
            
        days_diff = abs((d1 - d2).days)
        
        if days_diff == 0:
            return 100.0
        elif days_diff == 1:
            return 90.0
        elif days_diff == 2:
            return 80.0
        elif days_diff <= 4:
            return 70.0
        elif days_diff <= 7:
            return 50.0
        elif days_diff <= 14:
            return 30.0
        else:
            return max(0.0, 30.0 - (days_diff - 14) * 2.0)
    except Exception:
        return 50.0

def match_items(lost_item, found_item):
    """
    Computes weighted score between a lost item and a found item.
    Weights from synopsis:
    - Description: 50%
    - Category: 20%
    - Location: 20%
    - Date closeness: 10%
    """
    if not isinstance(lost_item, dict):
        lost_item = dict(lost_item)
    if not isinstance(found_item, dict):
        found_item = dict(found_item)

    # Combine item name, brand, color and description for comprehensive NLP representation
    desc1 = f"{lost_item['item_name']} {lost_item['color']} {lost_item.get('brand') or ''} {lost_item['description']}"
    desc2 = f"{found_item['item_name']} {found_item['color']} {found_item.get('brand') or ''} {found_item['description']}"
    
    desc_score, shared_words = calculate_text_similarity(desc1, desc2)
    
    # Explicit attribute reinforcement (color & brand alignment)
    color1 = (lost_item.get('color') or '').strip().lower()
    color2 = (found_item.get('color') or '').strip().lower()
    brand1 = (lost_item.get('brand') or '').strip().lower()
    brand2 = (found_item.get('brand') or '').strip().lower()
    
    attr_boost = 0.0
    if color1 and color2 and (color1 in color2 or color2 in color1):
        attr_boost += 8.0
    if brand1 and brand2 and (brand1 in brand2 or brand2 in brand1):
        attr_boost += 12.0
    desc_score = min(100.0, desc_score + attr_boost)
    
    cat_score = calculate_category_similarity(lost_item['category'], found_item['category'])
    loc_score = calculate_location_similarity(lost_item['last_seen_location'], found_item['found_location'])
    date_score = calculate_date_similarity(lost_item['date_lost'], found_item['date_found'])
    
    total_score = (
        Config.MATCH_WEIGHT_DESCRIPTION * desc_score +
        Config.MATCH_WEIGHT_CATEGORY * cat_score +
        Config.MATCH_WEIGHT_LOCATION * loc_score +
        Config.MATCH_WEIGHT_DATE * date_score
    )
    total_score = round(min(100.0, max(0.0, total_score)), 1)
    
    # Generate human-readable matching explanation
    reasons = []
    if cat_score >= 100:
        reasons.append(f"Identical category: {lost_item['category']}")
    elif cat_score > 0:
        reasons.append(f"Related categories: {lost_item['category']} / {found_item['category']}")
        
    if shared_words:
        reasons.append(f"Key matching descriptors: {', '.join(shared_words)}")
    elif desc_score > 30:
        reasons.append(f"{desc_score:.0f}% linguistic description similarity")
        
    if loc_score >= 80:
        reasons.append("Reported in the same or adjacent location")
    elif loc_score > 0:
        reasons.append("Geographically correlated campus zone")
        
    if date_score >= 90:
        reasons.append("Reported on the same day or within 24 hours")
    elif date_score >= 70:
        reasons.append("Reported within 2 to 4 days apart")
        
    if not reasons:
        reasons.append("Baseline textual and contextual overlap detected")
        
    match_reasons_str = " • ".join(reasons)
    
    return {
        'lost_item_id': lost_item['id'],
        'found_item_id': found_item['id'],
        'description_score': round(desc_score, 1),
        'category_score': round(cat_score, 1),
        'location_score': round(loc_score, 1),
        'date_score': round(date_score, 1),
        'total_score': total_score,
        'match_reasons': match_reasons_str
    }

def run_matching_for_item(item_type, item_id):
    """
    Recalculates matches for a newly added or updated item against all open opposite items.
    """
    conn = get_db_connection()
    matches_found = []
    
    if item_type == 'lost':
        lost_item = conn.execute('SELECT * FROM lost_items WHERE id = ?', (item_id,)).fetchone()
        if not lost_item or lost_item['status'] == 'Returned':
            conn.close()
            return []
            
        found_candidates = conn.execute(
            "SELECT * FROM found_items WHERE status != 'Returned'"
        ).fetchall()
        
        for found_item in found_candidates:
            res = match_items(lost_item, found_item)
            if res['total_score'] >= Config.MATCH_THRESHOLD:
                # Upsert into matches table
                conn.execute('''
                    INSERT INTO matches (lost_item_id, found_item_id, description_score, category_score, location_score, date_score, total_score, match_reasons)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(lost_item_id, found_item_id) DO UPDATE SET
                        description_score=excluded.description_score,
                        category_score=excluded.category_score,
                        location_score=excluded.location_score,
                        date_score=excluded.date_score,
                        total_score=excluded.total_score,
                        match_reasons=excluded.match_reasons,
                        created_at=CURRENT_TIMESTAMP
                ''', (
                    res['lost_item_id'], res['found_item_id'],
                    res['description_score'], res['category_score'],
                    res['location_score'], res['date_score'],
                    res['total_score'], res['match_reasons']
                ))
                
                # Update status of both items to 'Matched' if still 'Reported'
                if lost_item['status'] == 'Reported':
                    conn.execute("UPDATE lost_items SET status = 'Matched', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (lost_item['id'],))
                if found_item['status'] == 'Reported':
                    conn.execute("UPDATE found_items SET status = 'Matched', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (found_item['id'],))
                    
                # Create notification for lost item owner
                conn.execute('''
                    INSERT INTO notifications (user_id, title, message, link)
                    VALUES (?, ?, ?, ?)
                ''', (
                    lost_item['user_id'],
                    f"Possible Match Found ({res['total_score']}%)",
                    f"A found item '{found_item['item_name']}' matches your lost '{lost_item['item_name']}'.",
                    f"/matches?lost_id={lost_item['id']}"
                ))
                
                # Create notification for finder
                conn.execute('''
                    INSERT INTO notifications (user_id, title, message, link)
                    VALUES (?, ?, ?, ?)
                ''', (
                    found_item['user_id'],
                    f"Potential Owner Identified ({res['total_score']}%)",
                    f"Someone reported a lost '{lost_item['item_name']}' that matches what you found.",
                    f"/matches?found_id={found_item['id']}"
                ))
                
                matches_found.append(res)
                
    elif item_type == 'found':
        found_item = conn.execute('SELECT * FROM found_items WHERE id = ?', (item_id,)).fetchone()
        if not found_item or found_item['status'] == 'Returned':
            conn.close()
            return []
            
        lost_candidates = conn.execute(
            "SELECT * FROM lost_items WHERE status != 'Returned'"
        ).fetchall()
        
        for lost_item in lost_candidates:
            res = match_items(lost_item, found_item)
            if res['total_score'] >= Config.MATCH_THRESHOLD:
                conn.execute('''
                    INSERT INTO matches (lost_item_id, found_item_id, description_score, category_score, location_score, date_score, total_score, match_reasons)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(lost_item_id, found_item_id) DO UPDATE SET
                        description_score=excluded.description_score,
                        category_score=excluded.category_score,
                        location_score=excluded.location_score,
                        date_score=excluded.date_score,
                        total_score=excluded.total_score,
                        match_reasons=excluded.match_reasons,
                        created_at=CURRENT_TIMESTAMP
                ''', (
                    res['lost_item_id'], res['found_item_id'],
                    res['description_score'], res['category_score'],
                    res['location_score'], res['date_score'],
                    res['total_score'], res['match_reasons']
                ))
                
                if lost_item['status'] == 'Reported':
                    conn.execute("UPDATE lost_items SET status = 'Matched', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (lost_item['id'],))
                if found_item['status'] == 'Reported':
                    conn.execute("UPDATE found_items SET status = 'Matched', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (found_item['id'],))
                    
                conn.execute('''
                    INSERT INTO notifications (user_id, title, message, link)
                    VALUES (?, ?, ?, ?)
                ''', (
                    lost_item['user_id'],
                    f"Possible Match Found ({res['total_score']}%)",
                    f"A found item '{found_item['item_name']}' matches your lost '{lost_item['item_name']}'.",
                    f"/matches?lost_id={lost_item['id']}"
                ))
                
                conn.execute('''
                    INSERT INTO notifications (user_id, title, message, link)
                    VALUES (?, ?, ?, ?)
                ''', (
                    found_item['user_id'],
                    f"Potential Owner Identified ({res['total_score']}%)",
                    f"Someone reported a lost '{lost_item['item_name']}' that matches what you found.",
                    f"/matches?found_id={found_item['id']}"
                ))
                
                matches_found.append(res)
                
    conn.commit()
    conn.close()
    return matches_found
