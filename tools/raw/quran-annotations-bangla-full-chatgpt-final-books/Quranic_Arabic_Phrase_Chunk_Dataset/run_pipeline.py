#!/usr/bin/env python3
"""Run extraction, validation and CSV-based report generation from the project root."""
from pathlib import Path
import shutil, subprocess, sys

ROOT = Path(__file__).resolve().parent
PY = sys.executable

def run(args):
    print('\n$ ' + ' '.join(map(str, args)), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)

run([PY, str(ROOT/'scripts/build_phrase_chunk_dataset.py'),
     '--data-dir', str(ROOT/'data_sources'), '--out-dir', str(ROOT/'output/csv')])
run([PY, str(ROOT/'scripts/validate_outputs.py'),
     '--data-dir', str(ROOT/'data_sources'), '--csv-dir', str(ROOT/'output/csv')])
run([PY, str(ROOT/'scripts/build_curriculum_audit_report.py'),
     '--csv-dir', str(ROOT/'output/csv'),
     '--output', str(ROOT/'output/reports/curriculum_alignment_and_chunk_dataset.docx')])

soffice = shutil.which('soffice')
if soffice:
    reports = ROOT/'output/reports'
    run([soffice, '--headless', '--convert-to', 'pdf', '--outdir', str(reports),
         str(reports/'curriculum_alignment_and_chunk_dataset.docx')])
    print('\nPDF report exported using LibreOffice.')
else:
    print('\nLibreOffice not found: DOCX report was generated; install LibreOffice to export PDF.')
print('\nPipeline complete. CSVs: output/csv | Reports: output/reports')
