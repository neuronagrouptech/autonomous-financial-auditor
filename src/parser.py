from typing import Dict

def parse_finance_markdown(md_content: str) -> Dict[str, float]:
    result = {}
    for line in md_content.splitlines():
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3 and parts[1].replace(',', '').replace('.', '', 1).isdigit():
                key = parts[0]
                value = float(parts[1].replace(',', ''))
                result[key] = value
    return result
