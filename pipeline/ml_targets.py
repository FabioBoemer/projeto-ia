"""
Alvos de regressão a partir da camada Gold (apartment_kpis.parquet).

Ver docs/ML_DEFINICAO_ALVOS.md para as definições usadas no Sprint 4.
"""
from __future__ import annotations

import pandas as pd


def _cols_startswith(df: pd.DataFrame, prefix: str) -> list[str]:
    return [c for c in df.columns if c.startswith(prefix)]


def light_comfort(df: pd.DataFrame) -> pd.Series:
    """Média das colunas avg__sun_* por apartamento (uma linha = um apt)."""
    sun_cols = _cols_startswith(df, "avg__sun_")
    if not sun_cols:
        raise ValueError("Gold: nenhuma coluna avg__sun_* encontrada.")
    return df[sun_cols].mean(axis=1).rename("light_comfort")


def view_mean_row(df: pd.DataFrame) -> pd.Series:
    cols = _cols_startswith(df, "avg__view_")
    if not cols:
        return pd.Series(0.0, index=df.index, name="view_mean")
    return df[cols].mean(axis=1).rename("view_mean")


def noise_mean_row(df: pd.DataFrame) -> pd.Series:
    """Média de ruído em área (avg__noise_*), excluindo window_noise daqui."""
    cols = _cols_startswith(df, "avg__noise_")
    if not cols:
        return pd.Series(0.0, index=df.index, name="noise_mean")
    return df[cols].mean(axis=1).rename("noise_mean")


def _min_max_norm(s: pd.Series) -> pd.Series:
    lo, hi = float(s.min()), float(s.max())
    if hi - lo < 1e-12:
        return pd.Series(0.5, index=s.index)
    return (s - lo) / (hi - lo)


def env_quality_score(df: pd.DataFrame) -> pd.Series:
    """
    Índice em [0, 1]: combina luz (melhor = maior), vista (maior = melhor),
    ruído (menor = melhor) após normalização global por componente.
    """
    light = light_comfort(df)
    view_m = view_mean_row(df)
    noise_m = noise_mean_row(df)

    L = _min_max_norm(light)
    V = _min_max_norm(view_m)
    N_inv = 1.0 - _min_max_norm(noise_m)
    score = (L + V + N_inv) / 3.0
    return score.rename("env_quality_score")


def add_ml_targets(df: pd.DataFrame, copy: bool = True) -> pd.DataFrame:
    """
    Retorna cópia do DataFrame com colunas de alvo para regressão.

    - light_comfort / target_light_comfort
    - env_quality_score / target_env_quality
    """
    out = df.copy() if copy else df
    lc = light_comfort(out)
    out["light_comfort"] = lc
    out["target_light_comfort"] = lc

    eq = env_quality_score(out)
    out["env_quality_score"] = eq
    out["target_env_quality"] = eq
    return out


def feature_columns_for_light_comfort(df: pd.DataFrame) -> list[str]:
    """Colunas sugeridas para X ao prever target_light_comfort (sem vazamento)."""
    drop = {"apartment_id", "light_comfort", "target_light_comfort", "env_quality_score", "target_env_quality"}
    sun = set(_cols_startswith(df, "avg__sun_"))
    num = df.select_dtypes(include=["float64", "float32", "int64", "int32"]).columns
    return [c for c in num if c not in drop and c not in sun]


def feature_columns_for_env_quality(df: pd.DataFrame) -> list[str]:
    """Colunas sugeridas para X ao prever target_env_quality (sem vazamento grave)."""
    drop = {
        "apartment_id",
        "light_comfort",
        "target_light_comfort",
        "env_quality_score",
        "target_env_quality",
    }
    blocked_prefixes = ("avg__sun_", "avg__view_", "avg__noise_")
    num = df.select_dtypes(include=["float64", "float32", "int64", "int32"]).columns
    out: list[str] = []
    for c in num:
        if c in drop:
            continue
        if any(c.startswith(p) for p in blocked_prefixes):
            continue
        out.append(c)
    return out
