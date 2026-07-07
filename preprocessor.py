import pandas as pd
import numpy as np


def handle_duplicates(df : pd.DataFrame):
   # Create the columns
    df["pass"] = df["score"] >= 50

    # Highest score for passing rows
    passed = (
        df[df["pass"]]
        .sort_values("score", ascending=False)
        .drop_duplicates("name")
    )

    # First occurrence for failing rows (only names with no passing rows)
    failed = (
        df[~df["pass"]]
        .groupby("name", as_index=False)
        .first()
    )


    # Combine
    result = pd.concat([passed, failed], ignore_index=True)
    return result


def calc_grades(df : pd.DataFrame, points_to_grades):
    df['acumlated_points'] = df['points'] * df['credit_hours']
    no_honor = (df['honor'] == False).any()
    
    n_df = df.groupby('level')[['acumlated_points', 'credit_hours', 'score']].sum().copy()
    n_df['points'] = (n_df['acumlated_points'] / n_df['credit_hours']).round(2)
    n_df[['grade', 'desciptive_grade']] = n_df['points'].apply(lambda x : pd.Series(points_to_grades(x)))
    cols = ['acumlated_points', 'credit_hours', 'points', 'grade', 'desciptive_grade', 'score']
    return np.append(n_df[cols].to_numpy().flatten(), ~no_honor)


def handle_zero_credit(df : pd.DataFrame):
    return df[(df['credit_hours'] != 0 )]

def handle_zero_on_fail(df: pd.DataFrame) -> pd.DataFrame: 
    df.loc[df["score"] < 50, "score"] = 0
    return df