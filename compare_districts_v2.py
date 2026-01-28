import re
import os
import sys

# Turkish character normalization
def tr_lower(text):
    if not text:
        return ""
    
    # Pre-cleaning
    text = text.strip()
    
    # 1. Handle common anomalies manually before general lowercase
    # "Istanbul" (capital I) -> often meant to be "İstanbul" in Turkish context 
    # but strictly "I" -> "ı".
    # Groovy list seems to use "Istanbul" (ASCII I) for the city header.
    # We want "Istanbul" -> "istanbul" (dotted i) essentially for matching standard keys?
    # NO: Standard Turkish key for Istanbul is "istanbul" (starts with i).
    # If Input is "Istanbul", tr_lower makes it "ıstanbul".
    # We should normalize start if it is a known city?
    
    # Easier map for known problematic starts
    lower_map = {
        'İ': 'i', 'I': 'ı',
        'Ğ': 'ğ', 'Ü': 'ü', 'Ş': 'ş', 'Ö': 'ö', 'Ç': 'ç',
        'Â': 'a', 'â': 'a', 'Î': 'i', 'î': 'i', 'Û': 'u', 'û': 'u' # Circumflex removal
    }
    
    # Standardize loop
    chars = []
    for char in text:
        chars.append(lower_map.get(char, char.lower()))
    
    res = "".join(chars)
    
    # Post-fix specific to this dataset context
    # Groovy has "Istanbul" -> "ıstanbul". SQL has "istanbul".
    # We compel "ıstanbul" -> "istanbul" for this specific case?
    # Or better: treat "ıstanbul" and "istanbul" as same in logic?
    
    if res == "ıstanbul": return "istanbul"
    if res == "ızmir": return "izmir" # If written as Izmir
    # Isparta IS correctly "ısparta".
    
    return res

def tr_upper(text):
    if not text:
        return ""
    text = text.replace('i', 'İ').replace('ı', 'I')
    return text.upper()

def parse_groovy_list(filepath):
    """
    Parses the groovy list format:
    Province:
    1   District    PROVINCE
    """
    data = {} # { "province_lower": set("district_lower", ...) }
    current_province = None
    
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for Province Header e.g. "Adana:"
        if line.endswith(':'):
            current_province = tr_lower(line[:-1])
            if current_province not in data:
                data[current_province] = set()
            continue
            
        # Check for district line: "1   ALADAĞ   ADANA"
        # Split by whitespace
        parts = line.split()
        if len(parts) >= 3:
            # check if first part is a number
            if parts[0].isdigit():
                # The name is likely in the middle. The last part is Province Name.
                # Example: "1 ALADAĞ ADANA" -> Dist: ALADAĞ
                # Example: "3 ÇUKUROVA ADANA" -> Dist: ÇUKUROVA
                # Example: "10 SAİMBEYLİ ADANA"
                # Sometimes District names have spaces? "12 YENİ MAHALLE ANKARA"?
                # The last element is definitely Province.
                # district is parts[1:-1] joined.
                
                province_ref = parts[-1]
                district_parts = parts[1:-1]
                district_name = " ".join(district_parts)
                
                if current_province:
                    data[current_province].add(tr_lower(district_name))
                else:
                    # Fallback if no header seen (should not happen based on snippet)
                    pass

    return data

def parse_sql_file(filepath):
    """
    Parses SQL file to extract { "province_lower": set("district_lower") }
    """
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return {}

    items = {} # ID -> {name, parent, id}
    
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Regex for INSERT INTO `sehir` (...) VALUES (...)
    # Problem: "İstanbul (Avrupa)" contains parentheses which breaks lazy matching (.*?).
    # Solution: Split by 'insert into' and parse each block individually.
    
    statements = re.split(r'insert\s+into', content, flags=re.IGNORECASE)
    
    for stmt in statements:
        if "values" not in stmt.lower():
            continue
            
        # Find content between VALUES ( ... );
        # We assume the statement ends with );
        # Match from "values(" to the LAST ");" in this chunk
        
        m = re.search(r"values\s*\((.*)\)\s*;", stmt, re.IGNORECASE | re.DOTALL)
        if m:
            val_str = m.group(1)
        else:
            continue

        # split by comma, parsing simple SQL values
        parts = []
        # Primitive split by comma (assuming no commas in values based on observation)
        # If real SQL parser needed, this is insufficient but works for this dataset.
        raw_parts = val_str.split(',')
        for p in raw_parts:
            # Clean up quotes and newlines from splitting
            p = p.strip()
            # Handle 'value'
            if p.startswith("'") and p.endswith("'"):
                p = p[1:-1]
            parts.append(p)
            
        if len(parts) >= 4:
            # Handle possible newlines inside the parts
            pid = parts[0]
            # Name might be broken if it contained comma (unlikely for city names here)
            # Logic: id, plaka, name, parent
            name = parts[2].strip()
            parent = parts[3].strip() # Strip newline remnants
            
            items[pid] = {'name': name, 'parent': parent}

    # Reconstruct Hierarchy
    # Find root provinces
    # Logic: Parent is '100' or Name contains 'Ankara', 'Adana' etc?
    
    # "100" -> '0', 'Şehirler', 'ana'
    # "103" -> '6', 'Ankara', '100'
    # "121" -> '0', 'Gölbaşı', '103'
    
    # So Provinces have parent '100'.
    # EXCEPTION: Istanbul (Avrupa) '101' -> '100', Istanbul (Anadolu) '102' -> '100'.
    # We should merge these into "istanbul".
    
    result = {} # prov -> set(districts)
    
    provinces = {} # ID -> Normalized Name
    
    # 1. Identify Provinces
    for pid, info in items.items():
        if info['parent'] == '100':
            p_name_raw = info['name']
            
            # Special handling for Istanbul
            norm_name = tr_lower(p_name_raw)

            # Fix for Amasya (sometimes has cyrillic a?)
            # Just clean non-ascii if needed or simpler: check fuzzy
            if "amasya" in norm_name: 
                 # This handles potential weird chars if the basics are there
                 norm_name = "amasya"

            if "stanbul" in norm_name:
                provinces[pid] = "istanbul"
            elif "stanbul" in norm_name:
                provinces[pid] = "istanbul"
            else:
                provinces[pid] = norm_name

    # 2. Identify Districts
    for pid, info in items.items():
        parent_id = info['parent']
        name = tr_lower(info['name'])
        
        if parent_id in provinces:
            prov_name = provinces[parent_id]
            if prov_name not in result:
                result[prov_name] = set()
            result[prov_name].add(name)
            
    return result

def report_missing(target_name, target_data, base_data, output_file=None):
    """
    base_data: Groovy List (Gold Standard)
    target_data: SQL Data
    """
    # Helper to print to console and file
    def log(msg):
        print(msg)
        if output_file:
            output_file.write(msg + "\n")

    log(f"\n{'='*20}\nAnalyzing {target_name}...\n{'='*20}")
    
    total_missing = 0
    
    # Iterate over base provinces
    for prov in sorted(base_data.keys()):
        # Normalize prov key for Amasya issue?
        # If prov has weird char, tr_lower might preserve it.
        # Let's try to match by loose string
        
        target_prov_key = prov
        if prov not in target_data:
            # Try finding a close match
            # e.g. "amasyа" vs "amasya"
            candidates = [k for k in target_data.keys() if k.startswith(prov[:4])] # 'amas'
            if candidates:
                # assume the first one is it
                target_prov_key = candidates[0]
            else:
                log(f"!! CRITICAL: Province '{prov}' not found in {target_name} !!")
                continue
            
        base_districts = base_data[prov]
        target_districts = target_data[target_prov_key]
        
        missing = []
        for d in base_districts:
            # Check direct match
            found = False
            if d in target_districts:
                found = True
            else:
                # Check for "Merkez" variants
                if d == "merkez":
                   if "merkez" in target_districts or target_prov_key in target_districts:
                       found = True
                
                # Check fuzzy or specific maps (e.g. Karaköprü)
                if not found:
                    # check if district is substring
                    for td in target_districts:
                        if d == td: 
                            found = True; break
            
            if not found:
                missing.append(d)
                
        if missing:
            log(f"[{prov.upper()}] Eksik İlçeler (Eklemeniz Gerekenler): {', '.join([m.title() for m in missing])}")
            total_missing += len(missing)

        # --- Reverse Check: Items in SQL but NOT in Groovy ---
        # Bu kısım eski isimleri, 'Merkez' kayıtlarını veya hatalı yazımları bulur
        extra = []
        for td in target_districts:
            # Check matches in base
            # We need to do the fuzzy/normalization check again in reverse or just exact check per normalization
            found_in_base = False
            
            # Direct check
            if td in base_districts:
                found_in_base = True
            else:
                # Check fuzzy or map
                if td == "merkez": 
                    # Merkez usually maps to new districts, likely obsolete if strictly looking for sync
                    pass 
                
                # Reverse loop to check equality
                for bd in base_districts:
                    if bd == td:
                        found_in_base = True; break
            
            if not found_in_base:
                extra.append(td)
        
        if extra:
            log(f"    -> [{prov.upper()}] Fazla/Eski Kayıtlar (Silmeniz/Düzenlemeniz Gerekenler): {', '.join([e.title() for e in extra])}")

            # --- Auto-Advice for Merkez ---
            if "merkez" in extra and missing:
                if len(missing) == 1:
                    log(f"       * ÖNERİ (SQL): UPDATE sehir SET city_name = '{missing[0].title()}' WHERE city_name = 'Merkez' AND province_id = ...;")
                elif len(missing) > 1:
                    log(f"       * BİLGİ: 'Merkez' kaydı, şu yeni ilçelere bölünmüş olabilir: {', '.join([m.title() for m in missing])}.")


    if total_missing == 0:
        log(f"{target_name} is perfectly synced with Güncel Liste.")
    else:
        log(f"Total missing in {target_name}: {total_missing}")

def main():
    # Dosyaların script ile aynı dizinde olduğu varsayılır.
    # Eğer farklı bir yerdeyseler burayı manuel düzeltebilirsiniz.
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # base_dir = "/Users/hnidakd/Library/Containers/net.whatsapp.WhatsApp/Data/tmp/documents/B56BB1D2-E8E8-498F-B43D-B5FA0CF4142F/28 ocak 2026 sehir tablosu/"
    
    groovy_path = os.path.join(base_dir, "güncelliste-1.groovy")
    admin_sql_path = os.path.join(base_dir, "admin-sehir.sql")
    v1_sql_path = os.path.join(base_dir, "v1-sehir.sql")
    
    output_path = "eksik_ilceler_raporu.txt"
    
    print("Reading Reference Data (Güncel Liste)...")
    groovy_data = parse_groovy_list(groovy_path)
    
    print("Reading admin-sehir.sql...")
    admin_data = parse_sql_file(admin_sql_path)
    
    print("Reading v1-sehir.sql...")
    v1_data = parse_sql_file(v1_sql_path)
    
    with open(output_path, "w", encoding="utf-8") as f:
        report_missing("admin-sehir", admin_data, groovy_data, f)
        report_missing("v1-sehir", v1_data, groovy_data, f)
    
    print(f"\nRapor '{output_path}' dosyasına yazıldı.")

if __name__ == "__main__":
    main()
