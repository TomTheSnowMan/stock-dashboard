def dataframe_to_csv(df):
    return df.to_csv(index=False).encode("utf-8")