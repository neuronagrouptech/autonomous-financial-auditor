import re
import csv
from io import StringIO
import pandas as pd

# ----------- utilidades -----------

def _clean_md(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    # quita ** __ ` y espacios raros
    s = re.sub(r"[*_`]", "", s)
    s = s.replace("\u00a0", " ")
    return s.strip()

def _normalize_period(col: str) -> str:
    return re.sub(r"\s+", " ", col.strip().upper())

def _is_period(col: str) -> bool:
    return re.match(r"^Q\d+\s*\d{4}$", _normalize_period(col)) is not None

def _to_numeric(x):
    if x is None:
        return 0.0
    s = str(x).replace(",", "").strip()
    if s == "":
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0

def _normalize_account(s: str) -> str:
    return _clean_md(s).upper()

# ----------- parser Markdown -----------

def _markdown_table_to_dataframe(md_text: str) -> pd.DataFrame:
    rows = []
    for line in md_text.splitlines():
        if "|" not in line:
            continue
        raw = line.strip().strip("|")
        # descarta la fila separadora de la cabecera (---)
        if all(re.fullmatch(r":?-{3,}:?", c.strip() or "-") for c in raw.split("|")):
            continue
        cells = [c.strip() for c in raw.split("|")]
        rows.append(cells)

    if not rows:
        raise ValueError("No se detectó una tabla Markdown.")

    header = [_clean_md(c) for c in rows[0]]
    body = rows[1:]
    # homogeneiza longitudes
    width = len(header)
    norm_body = []
    for r in body:
        r = (r + [""] * width)[:width]
        norm_body.append(r)

    df = pd.DataFrame(norm_body, columns=[c.strip() for c in header])
    return df

# ----------- parser CSV “suelto” (tolerante a comas internas) -----------

def _loose_csv_to_dataframe(csv_text: str) -> pd.DataFrame:
    reader = csv.reader(StringIO(csv_text))
    all_rows = [row for row in reader if any(str(c).strip() for c in row)]
    if not all_rows:
        raise ValueError("CSV vacío.")

    header = [c.strip() for c in all_rows[0]]
    if len(header) < 3:
        raise ValueError("Se esperaban al menos 3 columnas (Account, Description, periodos...).")

    # asumimos las dos primeras columnas como metadatos
    period_cols = header[2:]
    out = []
    for row in all_rows[1:]:
        if not row:
            continue
        # toma los últimos K tokens como periodos; el resto se colapsa en Account/Description
        K = len(period_cols)
        tail = [c.strip() for c in row[-K:]] if len(row) >= K else []
        head = row[:len(row)-K] if len(row) >= K else row

        if len(head) == 0:
            account, description = "", ""
        elif len(head) == 1:
            account, description = head[0].strip(), ""
        else:
            # 1er token = Account, el resto (con comas) = Description
            account = head[0].strip()
            description = ",".join([c.strip() for c in head[1:]]).strip()

        rec = {
            "Account": _clean_md(account),
            "Description": _clean_md(description),
        }
        for i, p in enumerate(period_cols):
            rec[p] = tail[i].strip() if i < len(tail) else ""
        out.append(rec)

    df = pd.DataFrame(out)
    return df

# ----------- normalización común -> formato largo -----------

# ----------- API pública que necesitas -----------

def _wide_to_long_fin(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    if "Account" not in df.columns:
        raise ValueError("Columna 'Account' no encontrada.")
    if "Description" not in df.columns:
        df["Description"] = ""

    # Detecta columnas de periodo
    period_cols = [c for c in df.columns if _is_period(c)]
    if not period_cols:
        period_cols = [c for c in df.columns if re.search(r"Q\d+\s*\d{4}", c, re.I)]
    if not period_cols:
        raise ValueError("No se detectaron columnas de periodo.")

    # Asignar account principal y sub_account
    current_account = None
    accounts, sub_accounts = [], []

    for _, row in df.iterrows():
        acc_clean = _clean_md(row["Account"])
        desc_clean = _clean_md(row["Description"])

        # Si es sección (description vacío y cantidad vacía en todos los periodos)
        if desc_clean == "" and all(str(row[p]).strip() == "" for p in period_cols):
            current_account = acc_clean
            accounts.append(current_account)
            sub_accounts.append("")  # sección no tiene sub_account
        else:
            accounts.append(current_account or acc_clean)
            sub_accounts.append(acc_clean)

    df["account"] = accounts
    df["sub_account"] = sub_accounts

    # Derretir a formato largo
    id_cols = ["account", "sub_account", "Description"]
    long_df = df.melt(id_vars=id_cols, value_vars=period_cols,
                      var_name="period", value_name="amount")

    long_df["period"] = long_df["period"].apply(_normalize_period)
    long_df["amount"] = long_df["amount"].apply(_to_numeric)
    long_df["description"] = long_df["Description"].apply(_clean_md)

    # Marca totales
    sub_acc_norm = long_df["sub_account"].apply(_normalize_account)
    total_keys = [
        "TOTAL", "GROSS PROFIT", "OPERATING INCOME",
        "INCOME BEFORE TAX", "NET INCOME",
        "TOTAL ASSETS", "TOTAL LIABILITIES", "TOTAL EQUITY",
        "TOTAL LIABILITIES AND EQUITY"
    ]
    long_df["is_total"] = sub_acc_norm.apply(lambda s: any(k in s for k in total_keys))
    long_df = long_df[~((long_df["sub_account"] == "") & (long_df["amount"] == 0.0))]

    return long_df[["account", "sub_account", "description", "period", "amount", "is_total"]]

def parse_pnl_str(file_content: str, file_type: str) -> pd.DataFrame:
    """
    Convierte P&L (CSV o Markdown) a formato largo:
    columns = account, description, period, amount, is_total
    """
    if file_type.lower() == "md":
        df = _markdown_table_to_dataframe(file_content)
    elif file_type.lower() == "csv":
        df = _loose_csv_to_dataframe(file_content)
    else:
        raise ValueError("file_type debe ser 'csv' o 'md'.")

    return _wide_to_long_fin(df)



def parse_balance_sheet(text):
    """
    Convierte un Balance Sheet en formato Markdown o CSV a un DataFrame normalizado
    con columnas: section, account, sub_account, description, period, amount, is_total.
    """
    # --- 1. Detectar formato y cargar en DataFrame ancho ---
    if text.strip().startswith("|"):  
        # Es Markdown
        table_lines = []
        for line in text.splitlines():
            if line.strip().startswith("|") and "|" in line:
                table_lines.append(line)
        table_str = "\n".join(table_lines)
        df_wide = pd.read_csv(StringIO(table_str), sep="|", engine="python", skipinitialspace=True)
        df_wide = df_wide.dropna(axis=1, how="all")
        df_wide = df_wide.rename(columns=lambda x: x.strip())
        df_wide = df_wide.drop(index=0).reset_index(drop=True)  # quitar fila de separadores
    else:
        # Es CSV
        df_wide = pd.read_csv(StringIO(text))
        df_wide = df_wide.rename(columns=lambda x: x.strip())

    # --- 2. Variables de contexto ---
    section = None
    account_lvl2 = None
    rows = []

    # --- 3. Iterar filas ---
    for _, row in df_wide.iterrows():
        raw_account = str(row["Account"]).strip()
        description = str(row["Description"]).strip() if "Description" in row else ""

        # Detectar si es sección (nivel 1)
        if raw_account.startswith("**") and raw_account.endswith("**") and not re.search(r"Total", raw_account, re.IGNORECASE):
            section = re.sub(r"\*\*", "", raw_account).strip()
            account_lvl2 = None
            continue

        # Detectar si es subtotal / total
        is_total = False
        if raw_account.startswith("**") and raw_account.endswith("**"):
            is_total = True
            sub_account = re.sub(r"\*\*", "", raw_account).strip()
        else:
            sub_account = raw_account

        # Detectar nivel 2 (cuenta intermedia)
        if not is_total and description == "" and raw_account != "":
            account_lvl2 = raw_account
            continue

        # Si es total y no hay account_lvl2, usar section como account
        if is_total and not account_lvl2:
            account = section
        else:
            account = account_lvl2

        # --- 4. Convertir a formato largo ---
        for period in row.index[2:]:
            try:
                amount = float(str(row[period]).replace(",", "").strip()) if str(row[period]).strip() else 0.0
            except ValueError:
                amount = 0.0
            rows.append({
                "section": section,
                "account": account,
                "sub_account": sub_account,
                "description": description,
                "period": period.strip(),
                "amount": amount,
                "is_total": is_total
            })

    return pd.DataFrame(rows)



def parse_balance_str_2(file_content: str, file_type: str) -> pd.DataFrame:
    """
    Convierte Balance Sheet (CSV o Markdown) a formato largo con 3 niveles:
    section, account, sub_account, description, period, amount, is_total
    """
    # 1. Leer tabla
    if file_type.lower() == "md":
        df = _markdown_table_to_dataframe(file_content)
    elif file_type.lower() == "csv":
        df = _loose_csv_to_dataframe(file_content)
    else:
        raise ValueError("file_type debe ser 'csv' o 'md'.")

    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    if "Account" not in df.columns:
        raise ValueError("Columna 'Account' no encontrada.")
    if "Description" not in df.columns:
        df["Description"] = ""

    period_cols = [c for c in df.columns if _is_period(c)]
    if not period_cols:
        period_cols = [c for c in df.columns if re.search(r"Q\d+\s*\d{4}", c, re.I)]
    if not period_cols:
        raise ValueError("No se detectaron columnas de periodo (ej. 'Q1 2025').")

    # 2. Detectar jerarquías
    section = None
    account_lvl2 = None
    parsed_rows = []

    for _, row in df.iterrows():
        acc_raw = _normalize_account(row["Account"])
        desc_raw = _clean_md(row["Description"])

        # Nivel 1: sección
        if desc_raw == "" and acc_raw in {"ASSETS", "LIABILITIES", "EQUITY"}:
            section = acc_raw
            account_lvl2 = None
            continue  # no guardamos esta fila

        # Nivel 2: categoría dentro de sección
        if desc_raw == "" and acc_raw not in {"ASSETS", "LIABILITIES", "EQUITY"}:
            account_lvl2 = acc_raw
            continue  # no guardamos esta fila

        # Nivel 3: detalle
        sub_account = acc_raw
        is_total = any(k in acc_raw for k in [
            "TOTAL", "TOTAL ASSETS", "TOTAL LIABILITIES", "TOTAL EQUITY", 
            "TOTAL LIABILITIES AND EQUITY"
        ])

        for p in period_cols:
            parsed_rows.append({
                "section": section or "",
                "account": account_lvl2 or "",
                "sub_account": sub_account,
                "description": desc_raw,
                "period": _normalize_period(p),
                "amount": _to_numeric(row[p]),
                "is_total": is_total
            })

    return pd.DataFrame(parsed_rows)

# ----------- comparaciones -----------

def compare_net_income_vs_retained_earnings(pnl_long: pd.DataFrame,
                                            bs_long: pd.DataFrame,
                                            prev_period: str, curr_period: str) -> dict:
    pp = _normalize_period(prev_period)
    cp = _normalize_period(curr_period)

    ni = pnl_long[
        (pnl_long["period"] == cp) &
        (pnl_long["account"].str.upper().str.strip() == "NET INCOME")
    ]["amount"].sum()

    re_prev = bs_long[
        (bs_long["period"] == pp) &
        (bs_long["account"].str.upper().str.strip() == "RETAINED EARNINGS")
    ]["amount"].sum()

    re_curr = bs_long[
        (bs_long["period"] == cp) &
        (bs_long["account"].str.upper().str.strip() == "RETAINED EARNINGS")
    ]["amount"].sum()

    delta = re_curr - re_prev
    return {
        "net_income": float(ni),
        "retained_earnings_delta": float(delta),
        "difference": float(ni - delta),
        "ok": abs(ni - delta) < 1e-6
    }

def balance_equation_check(bs_long: pd.DataFrame) -> pd.DataFrame:
    """
    Verifica por periodo: TOTAL ASSETS == TOTAL LIABILITIES + TOTAL EQUITY
    Retorna un DataFrame con diff y ok.
    """
    def pick(label):
        lab = label.upper()
        t = bs_long[bs_long["account"].str.upper().str.strip() == lab][["period", "amount"]]
        return t.groupby("period", as_index=False)["amount"].sum()

    assets = pick("TOTAL ASSETS").rename(columns={"amount": "assets"})
    liab = pick("TOTAL LIABILITIES").rename(columns={"amount": "liabilities"})
    eqty = pick("TOTAL EQUITY").rename(columns={"amount": "equity"})

    out = assets.merge(liab, on="period", how="outer").merge(eqty, on="period", how="outer")
    out = out.fillna(0.0)
    out["liab_plus_equity"] = out["liabilities"] + out["equity"]
    out["diff"] = out["assets"] - out["liab_plus_equity"]
    out["ok"] = out["diff"].abs() < 1e-6
    return out.sort_values("period")
