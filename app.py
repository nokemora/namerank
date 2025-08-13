from flask import Flask, render_template, request, jsonify
import re
import whois
import socket
import concurrent.futures
import random

app = Flask(__name__)

# Scoring weights
TLD_WEIGHTS = {
    '.com': 100, '.net': 60, '.org': 50, '.io': 75,
    '.co': 40, '.ai': 85, '.xyz': 25, '.tech': 65, '.app': 70
}

DICTIONARY_WORDS = {
    'shop', 'tech', 'ai', 'crypto', 'nft', 'app', 'web', 'cloud',
    'data', 'host', 'game', 'blog', 'news', 'video', 'music',
    'store', 'buy', 'sell', 'trade', 'invest', 'startup',
    'car', 'hotel', 'fitness', 'law', 'design', 'photo', 'travel'
}

SUGGESTION_KEYWORDS = [
    'labs', 'genius', 'pulse', 'forge', 'vault', 'core', 'hive',
    'flow', 'orbit', 'spark', 'peak', 'aura', 'node', 'shift', 'mode',
    'logic', 'boost', 'drive', 'sphere', 'grid', 'loop', 'edge', 'flare',
    'nexus', 'zen', 'nova', 'echo', 'atom', 'byte', 'pixel', 'glow',
    'trend', 'alpha', 'omega', 'prime', 'elite', 'next', 'now', 'live'
]

TLDs = ['.com', '.net', '.org', '.io', '.ai', '.tech', '.app', '.co']

RECENT_SALES = [
    {"domain": "ai.com", "price": 1200000},
    {"domain": "crypto.com", "price": 12000000},
    {"domain": "nft.com", "price": 24000000},
    {"domain": "aitech.ai", "price": 12500},
    {"domain": "startup.io", "price": 8500}
]

def calculate_rating(domain):
    domain = domain.lower().strip()
    if not re.match(r'^[a-z0-9-]+\.[a-z]{2,}$', domain):
        return {"error": "Invalid domain"}
    
    name, tld = domain.rsplit('.', 1)
    tld = '.' + tld
    length = len(name)
    
    tld_score = TLD_WEIGHTS.get(tld, 10)
    length_score = 100 if length <= 6 else max(0, 100 - (length - 6) * 15)
    penalty = 15 if '-' in name else 0
    penalty += 10 if any(c.isdigit() for c in name) else 0
    is_dict = name in DICTIONARY_WORDS
    dict_score = 20 if is_dict else 0
    vowel_ratio = sum(1 for c in name if c in 'aeiou') / len(name)
    brandability = 50 + int(vowel_ratio * 100)
    
    total = (
        tld_score * 0.35 +
        length_score * 0.3 +
        (100 - penalty) * 0.05 +
        dict_score * 0.1 +
        brandability * 0.2
    )
    
    # Value estimation
    base_val = 500 + (total - 50) * 30 if total > 50 else 100 + total * 8
    tld_mult = 3.0 if tld == '.com' else 1.8 if tld in ['.ai', '.io'] else 1.0
    dict_mult = 2.5 if is_dict else 1.0
    length_mult = 3.0 if length <= 6 else 2.0 if length <= 8 else 1.0
    
    min_val = int(base_val * tld_mult * dict_mult * length_mult * 0.8)
    max_val = int(base_val * tld_mult * dict_mult * length_mult * 1.4)
    min_val = (min_val // 100) * 100
    max_val = (max_val // 100) * 100
    
    return {
        "rating": round(min(100, max(0, total)), 1),
        "breakdown": {
            "TLD (.com)": round(tld_score * 0.35, 1),
            "Length": round(length_score * 0.3, 1),
            "Clean": round((100 - penalty) * 0.05, 1),
            "Real Word": round(dict_score * 0.1, 1),
            "Brandability": round(brandability * 0.2, 1)
        },
        "value": {
            "min": min_val,
            "max": max_val,
            "formatted": f"${min_val:,.0f} - ${max_val:,.0f}",
            "recent_sales": RECENT_SALES[:3]
        },
        "details": {"domain": domain}
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/rate', methods=['POST'])
def rate():
    domain = request.json.get('domain', '').strip()
    if not domain:
        return jsonify({"error": "Domain required"}), 400
    return jsonify(calculate_rating(domain))

@app.route('/suggest', methods=['POST'])
def suggest():
    base = request.json.get('base', '').strip().lower()
    if not base or len(base) < 3:
        return jsonify({"error": "Use 3+ characters"}), 400

    def check_available(domain_name):
        if len(domain_name) > 22:
            return {"domain": domain_name, "available": False}
        
        available = True
        try:
            socket.setdefaulttimeout(1.0)
            whois.whois(domain_name)
            available = False
        except:
            available = True
        finally:
            socket.setdefaulttimeout(None)
        
        return {"domain": domain_name, "available": available}

    domains_to_check = [
        f"{base}{keyword}{tld}"
        for keyword in SUGGESTION_KEYWORDS
        for tld in TLDs
        if 6 <= len(f"{base}{keyword}{tld}") <= 22
    ]

    suggestions = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        future_to_domain = {
            executor.submit(check_available, domain): domain
            for domain in domains_to_check[:12]
        }
        for future in concurrent.futures.as_completed(future_to_domain):
            try:
                result = future.result()
                suggestions.append(result)
            except:
                pass

    suggestions.sort(key=lambda x: (not x['available'], len(x['domain'])))
    return jsonify({"base": base, "suggestions": suggestions})

# === AI NAME GENERATOR ===
@app.route('/generate', methods=['POST'])
def generate():
    count = request.json.get('count', 8)
    results = []
    
    # Name generation components
    PREFIXES = ['Nexa', 'Aura', 'Virtuo', 'Thinka', 'Luma', 'Kilo', 'Stellar', 'Apex', 'Pulse', 'Orbit']
    SUFFIXES = ['IQ', 'X', 'Labs', 'Hub', 'Gen', 'Core', 'Flow', 'Shift', 'Node', 'Vault']
    WORDS = ['Spark', 'Logic', 'Drive', 'Sphere', 'Grid', 'Boost', 'Echo', 'Atom', 'Zen', 'Nova']

    def make_name():
        return random.choice([
            random.choice(PREFIXES) + random.choice(['AI', 'IQ', 'X', 'Labs']),
            random.choice(['Get', 'Go', 'Try']) + random.choice(PREFIXES),
            random.choice(PREFIXES) + random.choice(SUFFIXES),
            random.choice(['Urban', 'Solar', 'Neuro', 'Meta']) + random.choice(WORDS),
            random.choice(['Aurora', 'Strive', 'Zenith', 'Cognito', 'Vanta', 'Echelon'])
        ])

    generated = set()
    while len(generated) < count:
        name = make_name()
        if name not in generated:
            generated.add(name)
    
    for name in generated:
        for tld in ['.com', '.ai', '.io']:
            domain = f"{name.lower()}{tld}"
            available = True
            try:
                socket.setdefaulttimeout(1.0)
                whois.whois(domain)
                available = False
            except:
                available = True
            finally:
                socket.setdefaulttimeout(None)
            
            results.append({
                "name": name,
                "domain": domain,
                "tld": tld,
                "available": available
            })
    
    return jsonify({"names": results})

if __name__ == '__main__':
    app.run(debug=False)