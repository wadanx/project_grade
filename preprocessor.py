import pandas as pd

LEVELS = [1, 2, 3, 4]

def calc_grades(df : pd.DataFrame, points_to_grades):
    df['acumlated_points'] = df['points'] * df['credit_hours']
    no_honor = (df['honor'] == False).any()

    # Reindex to the full fixed set of levels (rather than only the levels this
    # student happens to have) so every row is the same length and a given
    # column position always means the same level, regardless of student.
    n_df = df.groupby('level')[['acumlated_points', 'credit_hours', 'score']].sum().copy()
    n_df = n_df.reindex(LEVELS)
    n_df['points'] = (n_df['acumlated_points'] / n_df['credit_hours']).round(2)

    def to_grade(points):
        if pd.isna(points):
            return pd.Series([None, None])
        return pd.Series(points_to_grades(points))

    n_df[['grade', 'desciptive_grade']] = n_df['points'].apply(to_grade)
    cols = ['acumlated_points', 'credit_hours', 'points', 'grade', 'desciptive_grade', 'score']
    per_level = n_df[cols].to_numpy().flatten().tolist()

    total_acumlated_points = df['acumlated_points'].sum()
    total_credit_hours = df['credit_hours'].sum()
    total_score = df['score'].sum()
    overall_points = round(total_acumlated_points / total_credit_hours, 2) if total_credit_hours else 0.0
    overall_grade, overall_desciptive_grade = points_to_grades(overall_points)

    overall = [
        total_acumlated_points,
        total_credit_hours,
        overall_points,
        total_score,
        overall_grade,
        overall_desciptive_grade,
    ]

    return per_level + overall + [~no_honor]


def process(df: pd.DataFrame) -> pd.DataFrame:
    df = df[(df['credit_hours'] != 0 )] # Remove Records with zero score 
    df["pass"] = df["score"] >= 50
    passed = (
        df[df["pass"]]
        .sort_values("score", ascending=False)
        .drop_duplicates("name")
    )
    failed = (
        df[~df["pass"]]
        .groupby("name", as_index=False)
        .first()
    )
    df = pd.concat([passed, failed], ignore_index=True)
    df.loc[df["score"] < 50, "score"] = 0
    df['honor'] = df['score'] >= 75
    return df