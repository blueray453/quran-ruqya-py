#!/usr/bin/env python3
"""Recreate the Quranic Arabic frequency CSVs and reports from bundled sources.

Default workflow:
  1. Extract data_sources.zip and reference_tables.zip into build_workspace/.
  2. Rebuild CSVs from raw sources.
  3. Build the quantitative Ism and compatibility/status CSVs.
  4. Validate expected snapshot counts.
  5. Build DOCX reports exclusively from the generated CSVs.
  6. Convert reports to PDF when LibreOffice is available.
"""
from __future__ import annotations
import argparse, csv, hashlib, shutil, subprocess, sys, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def run(cmd):
    print('\n$ '+' '.join(str(x) for x in cmd),flush=True)
    subprocess.run([str(x) for x in cmd],check=True,cwd=ROOT)


def safe_extract(zip_path: Path, destination: Path):
    destination.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        root=destination.resolve()
        for member in z.infolist():
            target=(destination/member.filename).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f'Unsafe path in {zip_path.name}: {member.filename}')
        z.extractall(destination)


def verify_source_manifest(source_root: Path):
    manifest=source_root/'SOURCE_FILE_MANIFEST.csv'
    if not manifest.exists():
        raise FileNotFoundError(f'Source hash manifest missing: {manifest}')
    checked=0
    with manifest.open('r',encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            path=(source_root/row['relative_path']).resolve()
            if source_root.resolve() not in path.parents:
                raise ValueError(f'Unsafe path in source manifest: {row["relative_path"]}')
            if not path.is_file(): raise FileNotFoundError(f'Manifest source file missing: {path}')
            raw=path.read_bytes()
            digest=hashlib.sha256(raw).hexdigest()
            if len(raw)!=int(row['size_bytes']) or digest!=row['sha256']:
                raise ValueError(f'Source file hash/size mismatch: {row["relative_path"]}')
            checked += 1
    print(f'Verified {checked} bundled source files by size and SHA-256.')


def main():
    ap=argparse.ArgumentParser(description='Recreate Quranic Arabic analysis outputs.')
    ap.add_argument('--source-zip',default=str(ROOT/'data_sources.zip'))
    ap.add_argument('--reference-zip',default=str(ROOT/'reference_tables.zip'))
    ap.add_argument('--workspace',default=str(ROOT/'build_workspace'))
    ap.add_argument('--output-dir',default=str(ROOT/'output'))
    ap.add_argument('--skip-validation',action='store_true',help='Skip snapshot-specific expected-count checks after regeneration.')
    ap.add_argument('--skip-pdf',action='store_true',help='Do not create PDF reports; DOCX reports will still be built.')
    args=ap.parse_args()
    srczip=Path(args.source_zip).resolve(); refzip=Path(args.reference_zip).resolve(); work=Path(args.workspace).resolve(); out=Path(args.output_dir).resolve()
    if not srczip.is_file(): raise FileNotFoundError(f'Source archive not found: {srczip}')
    if not refzip.is_file(): raise FileNotFoundError(f'Reference archive not found: {refzip}')
    if work.exists(): shutil.rmtree(work)
    work.mkdir(parents=True)
    source_root=work/'source_data'; reference_root=work/'reference_tables'
    safe_extract(srczip,source_root); safe_extract(refzip,reference_root)
    verify_source_manifest(source_root)
    csv_dir=out/'csv'; report_dir=out/'reports'
    if csv_dir.exists(): shutil.rmtree(csv_dir)
    if report_dir.exists(): shutil.rmtree(report_dir)
    csv_dir.mkdir(parents=True); report_dir.mkdir(parents=True)
    scripts=ROOT/'scripts'
    run([sys.executable,scripts/'build_frequency_csvs.py','--data-dir',source_root,'--output-dir',csv_dir,'--reference-dir',reference_root])
    run([sys.executable,scripts/'build_ism_csvs.py','--grammar-dir',source_root/'grammar','--output-dir',csv_dir])
    run([sys.executable,scripts/'build_compatibility_csvs.py','--csv-dir',csv_dir,'--data-dir',source_root])
    if not args.skip_validation:
        run([sys.executable,scripts/'validate_outputs.py','--csv-dir',csv_dir])
    run([sys.executable,scripts/'build_reports_from_csvs.py','--csv-dir',csv_dir,'--output-dir',report_dir])
    soffice=shutil.which('soffice')
    if not args.skip_pdf and soffice:
        for docx in [report_dir/'complete_analysis_report.docx',report_dir/'quantitative_ism_report.docx']:
            run([soffice,'--headless','--convert-to','pdf','--outdir',report_dir,docx])
    elif not args.skip_pdf:
        print('LibreOffice (soffice) not found; DOCX reports created, PDF conversion skipped.')
    print('\nPipeline completed.')
    print(f'CSV outputs: {csv_dir}')
    print(f'Reports:     {report_dir}')

if __name__=='__main__': main()
