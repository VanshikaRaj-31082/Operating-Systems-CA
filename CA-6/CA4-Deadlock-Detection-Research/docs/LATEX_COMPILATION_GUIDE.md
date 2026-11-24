# Overleaf and LaTeX Compilation Instructions

**Document:** `CA4-Deadlock-Detection-Research/docs/final_report.tex`  
**Target:** Continuous Assessment 4 (CA4) Research Mini-Project Topic R13 Final Report

---

## 1. Local Compilation via TeX Live / MiKTeX / MacTeX
If you have a local LaTeX distribution installed:

```bash
# Navigate to the docs directory
cd CA4-Deadlock-Detection-Research/docs

# Copy or symlink the figures from ../results/figures/ into the current directory
# On Windows PowerShell:
Copy-Item ..\results\figures\*.png .

# Compile using pdflatex (run twice for cross-references):
pdflatex final_report.tex
pdflatex final_report.tex
```

---

## 2. Compilation on Overleaf (Recommended)
To compile seamlessly on [Overleaf](https://www.overleaf.com):

1. **Create a New Project:**  
   Click `New Project` -> `Blank Project`.
2. **Upload Files:**
   - Upload `final_report.tex`.
   - Upload all 8 PNG figures from `CA4-Deadlock-Detection-Research/results/figures/`:
     - `fig1_detection_time_vs_processes.png`
     - `fig2_detection_time_vs_resources.png`
     - `fig3_mean_vs_median_comparison.png`
     - `fig4_separate_scaling_breakdown.png`
     - `fig5_random_detector_positive_rate.png`
     - `fig6_correctness_verification_summary.png`
     - `fig7_observed_vs_fitted_regression.png`
     - `fig8_multivariable_coefficients_ci.png`
3. **Compile:**  
   Ensure compiler is set to `pdfLaTeX` (Overleaf default). Click **Recompile**.
