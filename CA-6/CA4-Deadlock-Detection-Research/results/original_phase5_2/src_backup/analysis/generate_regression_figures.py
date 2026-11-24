"""
CA4 - Research Mini-Project R13: Deadlock Detection under Different Resource Patterns
Script: src/analysis/generate_regression_figures.py

Generates supplemental publication figures for multivariable regression diagnostics:
- Fig 7: Observed vs. Fitted log(Median Detection Time) across models and patterns.
- Fig 8: Multivariable regression coefficients with 95% Confidence Intervals for N and M.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SUMMARY_CSV = PROJECT_ROOT / "results" / "processed" / "matrix_experiment_summary.csv"
FIGURES_DIR = PROJECT_ROOT / "results" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams.update({
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "figure.titlesize": 14,
    "lines.linewidth": 1.8,
})

df = pd.read_csv(SUMMARY_CSV)


def plot_observed_vs_fitted():
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for idx, (rm, title, ax) in enumerate([
        ("single_instance", "Single-Instance (WFG): Observed vs Fitted", axes[0]),
        ("multi_instance", "Multi-Instance (Reduction): Observed vs Fitted", axes[1]),
    ]):
        sub = df[df["resource_model"] == rm].copy()
        colors = {"acyclic": "#1f77b4", "circular": "#d62728", "mixed": "#2ca02c", "random": "#9467bd"}

        for pat in ["acyclic", "circular", "mixed", "random"]:
            psub = sub[sub["pattern"] == pat]
            y = np.log(psub["median_us"].values)
            X = np.column_stack([np.ones(len(y)), np.log(psub["n"].values), np.log(psub["m"].values)])
            beta = np.linalg.pinv(X.T @ X) @ X.T @ y
            y_pred = X @ beta

            ax.scatter(y_pred, y, label=pat.capitalize(), color=colors[pat], alpha=0.6, s=32)

        # 1:1 line
        lims = [1.5, 7.5]
        ax.plot(lims, lims, "k--", alpha=0.7, label="1:1 Parity")
        ax.set_title(title, weight="bold")
        ax.set_xlabel("Fitted $\ln(\mathrm{Median\ Time\ [\mu s]})$")
        ax.set_ylabel("Observed $\ln(\mathrm{Median\ Time\ [\mu s]})$")
        ax.set_xlim(lims)
        ax.set_ylim(lims)
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend()

    plt.suptitle("Fig 7: Multivariable OLS Regression Diagnostics (Observed vs. Fitted)", weight="bold")
    plt.tight_layout()
    outpath = FIGURES_DIR / "fig7_observed_vs_fitted_regression.png"
    plt.savefig(outpath, dpi=300)
    plt.close()
    print(f"Saved: {outpath}")


def plot_regression_coefficients():
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    patterns = ["acyclic", "circular", "mixed", "random"]
    models = ["single_instance", "multi_instance"]

    for idx, (dim, dim_name, ax) in enumerate([
        ("log_N", "Process Count Scaling ($\hat{\\beta}_N$)", axes[0]),
        ("log_M", "Resource Type Scaling ($\hat{\\beta}_M$)", axes[1]),
    ]):
        y_pos = np.arange(len(patterns))
        width = 0.35

        for m_idx, (rm, label, color) in enumerate([
            ("single_instance", "Single-Instance (WFG)", "#3470a3"),
            ("multi_instance", "Multi-Instance (Reduction)", "#e27c38"),
        ]):
            sub = df[df["resource_model"] == rm]
            coefs = []
            errs = []

            for pat in patterns:
                psub = sub[sub["pattern"] == pat]
                y = np.log(psub["median_us"].values)
                X = np.column_stack([np.ones(len(y)), np.log(psub["n"].values), np.log(psub["m"].values)])
                N, p = X.shape
                beta = np.linalg.pinv(X.T @ X) @ X.T @ y
                residuals = y - X @ beta
                sigma2 = np.sum(residuals**2) / (N - p)
                se = np.sqrt(np.diag(sigma2 * np.linalg.pinv(X.T @ X)))

                var_idx = 1 if dim == "log_N" else 2
                coefs.append(beta[var_idx])
                errs.append(1.96 * se[var_idx])  # 95% CI margin

            offset = -width/2 if m_idx == 0 else width/2
            ax.bar(y_pos + offset, coefs, width, yerr=errs, capsize=4, label=label, color=color, alpha=0.85)

        ax.set_title(dim_name, weight="bold")
        ax.set_xticks(y_pos)
        ax.set_xticklabels([p.capitalize() for p in patterns])
        ax.set_ylabel("Estimated Scaling Exponent ($\hat{\\beta}$)")
        ax.grid(True, linestyle="--", alpha=0.6, axis="y")
        if dim == "log_N":
            ax.axhline(1.0, color="red", linestyle=":", label="Linear Threshold ($\hat{\\beta}=1.0$)")
        ax.legend()

    plt.suptitle("Fig 8: Multivariable Power-Law Exponents with 95% Confidence Intervals", weight="bold")
    plt.tight_layout()
    outpath = FIGURES_DIR / "fig8_multivariable_coefficients_ci.png"
    plt.savefig(outpath, dpi=300)
    plt.close()
    print(f"Saved: {outpath}")


if __name__ == "__main__":
    print("Generating supplementary regression diagnostic plots...")
    plot_observed_vs_fitted()
    plot_regression_coefficients()
    print("Figures 7 & 8 generated successfully.")
