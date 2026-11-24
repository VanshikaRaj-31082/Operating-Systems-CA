# Overleaf Submission & Compilation Guide for CA5
## Continuous Assessment 5 – Linux Systems Engineering Challenge

**Project:** `CA5-Linux-Systems-Engineering`  
**Candidate:** Vanshika Raj (USN: `25BTRCL278`)  
**Institution:** Jain (Deemed-to-be University), Faculty of Engineering and Technology  

---

### 1. Overview

The final CA5 research report is written in standard, professional academic LaTeX in:
```
CA5-Linux-Systems-Engineering/docs/final_report.tex
```
It is designed to compile cleanly using standard **pdfLaTeX** or **XeLaTeX** on [Overleaf](https://www.overleaf.com) or any local TeX Live / MiKTeX distribution.

---

### 2. Required Files for Overleaf Submission

To compile the report on Overleaf, create a new blank project and upload the following files:

```
Overleaf Project Root/
├── main.tex                                    <-- Rename docs/final_report.tex to main.tex
└── results/
    └── figures/
        ├── fig1_race_condition_accuracy.png    <-- Upload from CA5-Linux-Systems-Engineering/results/figures/
        ├── fig2_lock_contention_throughput.png <-- Upload from CA5-Linux-Systems-Engineering/results/figures/
        ├── fig3_context_switches_vs_threads.png<-- Upload from CA5-Linux-Systems-Engineering/results/figures/
        └── fig4_deadlock_recovery_latency.png  <-- Upload from CA5-Linux-Systems-Engineering/results/figures/
```

> **Note on Image Paths:** The LaTeX document references figures using the relative path `results/figures/<filename>.png`. If you place the figures directly in the Overleaf project root, you can either keep the `results/figures/` folder structure in Overleaf or change the `\includegraphics` paths to bare filenames.

---

### 3. Step-by-Step Overleaf Upload Instructions

1. **Log in to Overleaf:** Navigate to [https://www.overleaf.com](https://www.overleaf.com) and log in.
2. **Create New Project:**
   - Click **New Project** -> **Blank Project**.
   - Project Name: `CA5_Linux_Systems_Engineering_25BTRCL278`.
3. **Upload the LaTeX Source:**
   - Delete the default `main.tex` in the new Overleaf project.
   - Upload `CA5-Linux-Systems-Engineering/docs/final_report.tex` and rename it to `main.tex`.
4. **Create Folder & Upload Figures:**
   - Click the **New Folder** icon in Overleaf and name it `results`.
   - Inside `results`, create a subfolder named `figures`.
   - Upload the 4 PNG files from your local `CA5-Linux-Systems-Engineering/results/figures/` into `results/figures/`.
5. **Set Compiler Settings:**
   - Click the **Menu** button in the top-left corner of Overleaf.
   - Ensure **Compiler** is set to **pdfLaTeX** (or **XeLaTeX**).
   - Ensure **TeX Live Version** is set to **2023** or **2024**.
6. **Compile:**
   - Click the green **Recompile** button.
   - The document will compile with zero errors, producing the complete academic research PDF.

---

### 4. Local Compilation via Command Line (Optional)

If a local TeX Live or MiKTeX installation is available on Linux or Windows:

```bash
cd CA5-Linux-Systems-Engineering
pdflatex -interaction=nonstopmode -output-directory=docs docs/final_report.tex
pdflatex -interaction=nonstopmode -output-directory=docs docs/final_report.tex
```
*(Running twice resolves cross-references, table of contents, and list of figures).*
