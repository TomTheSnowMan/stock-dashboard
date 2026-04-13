from __future__ import annotations

import pandas as pd

def dataframe_to_csv(df: pd.DataFrame) -> bytes:
    """
    Convert a DataFrame to UTF-8 encoded CSV bytes
    for use with Streamlit download buttons.
    """
    return df.to_csv(index=False).encode("utf-8")