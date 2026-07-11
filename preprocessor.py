import pandas as pd


def get_passed(df : pd.DataFrame, passeed_only = False):
   # Create the columns
    df["pass"] = df["score"] >= 50

    # Highest score for passing rows
    passed = (
        df[df["pass"]]
        .sort_values("score", ascending=False)
        .drop_duplicates("name")
    )
   
    return passed


def calc_grades(df : pd.DataFrame, points_to_grades):
    df['acumlated_points'] = df['points'] * df['credit_hours']
    print(df.sort_values('level'))
    n_df = df.groupby('level')[['acumlated_points', 'credit_hours', 'score']].sum().copy()
    n_df['points'] = (n_df['acumlated_points'] / n_df['credit_hours']).round(2)
    n_df[['grade', 'desciptive_grade']] = n_df['points'].apply(lambda x : pd.Series(points_to_grades(x)))
    cols = ['acumlated_points', 'credit_hours', 'points', 'grade', 'desciptive_grade', 'score']
    return n_df[cols].to_numpy().flatten()


def handle_zero_credit(df : pd.DataFrame):
    return df[(df['credit_hours'] != 0 )]

def handle_zero_on_fail(df: pd.DataFrame) -> pd.DataFrame: 
    df.loc[df["score"] < 50, "score"] = 0
    return df