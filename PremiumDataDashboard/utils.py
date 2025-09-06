import pandas as pd

def load_data(path):
    """Load CSV or Excel into pandas DataFrame."""
    if str(path).lower().endswith(('.xls', '.xlsx')):
        return pd.read_excel(path)
    else:
        return pd.read_csv(path)

def get_numeric_columns(df):
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

def get_all_columns(df):
    return list(df.columns)

def summary_stats(df, column):
    s = df[column].describe()
    return {
        'count': int(s['count']),
        'mean': float(s['mean']) if not pd.isna(s['mean']) else None,
        'std': float(s['std']) if not pd.isna(s['std']) else None,
        'min': float(s['min']) if not pd.isna(s['min']) else None,
        'max': float(s['max']) if not pd.isna(s['max']) else None,
        'sum': float(df[column].sum())
    }