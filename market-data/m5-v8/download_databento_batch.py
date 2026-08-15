#!/usr/bin/env python3
"""Safely quote, submit, download and transcode the M5 V8 Databento batch.

The script never submits a paid job unless --execute is supplied AND the live
Databento quote is <= --max-cost-usd. Output DBN files are split by month and
transcoded to Parquet with mapped raw symbols.
"""
from __future__ import annotations
import argparse, json, os, time
from pathlib import Path

DATASET='XNAS.ITCH'; SCHEMA='ohlcv-1m'; START='2018-05-01'; END='2026-08-16'

def load_symbols(path:Path)->list[str]:
    vals=[x.strip() for x in path.read_text().splitlines() if x.strip() and not x.lstrip().startswith('#')]
    return list(dict.fromkeys(vals))

def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument('--symbols',type=Path,required=True)
    ap.add_argument('--outdir',type=Path,required=True)
    ap.add_argument('--start',default=START); ap.add_argument('--end',default=END)
    ap.add_argument('--max-cost-usd',type=float,default=20.0)
    ap.add_argument('--execute',action='store_true',help='Actually submit the batch after the cost gate passes')
    ap.add_argument('--poll-seconds',type=float,default=10.0)
    args=ap.parse_args()
    if not os.environ.get('DATABENTO_API_KEY'):
        raise SystemExit('DATABENTO_API_KEY is not set')
    import databento as db
    symbols=load_symbols(args.symbols); client=db.Historical()
    req=dict(dataset=DATASET,symbols=symbols,schema=SCHEMA,start=args.start,end=args.end,stype_in='raw_symbol')
    cost=float(client.metadata.get_cost(**req)); size=int(client.metadata.get_billable_size(**req)); count=int(client.metadata.get_record_count(**req))
    quote={'dataset':DATASET,'schema':SCHEMA,'symbols':len(symbols),'start':args.start,'end_exclusive':args.end,'cost_usd':cost,'billable_size_bytes':size,'record_count':count,'max_cost_usd':args.max_cost_usd}
    args.outdir.mkdir(parents=True,exist_ok=True)
    (args.outdir/'quote.json').write_text(json.dumps(quote,indent=2)+'\n')
    print(json.dumps(quote,indent=2))
    if cost>args.max_cost_usd:
        raise SystemExit(f'Cost gate blocked purchase: ${cost:.2f} > ${args.max_cost_usd:.2f}')
    if not args.execute:
        print('QUOTE_ONLY: cost gate passed; re-run with --execute to submit the batch.')
        return
    job=client.batch.submit_job(**req,encoding='dbn',compression='zstd',split_duration='month',delivery='download')
    job_id=job['id']; print('SUBMITTED',job_id)
    while job_id not in {j['id'] for j in client.batch.list_jobs('done')}:
        if job_id in {j['id'] for j in client.batch.list_jobs('expired')}:
            raise RuntimeError(f'Batch job expired: {job_id}')
        time.sleep(args.poll_seconds)
    raw_dir=args.outdir/'dbn'; pq_dir=args.outdir/'parquet'; raw_dir.mkdir(exist_ok=True); pq_dir.mkdir(exist_ok=True)
    files=client.batch.download(job_id=job_id,output_dir=raw_dir)
    parquet=[]
    for f in sorted(map(Path,files)):
        if f.name.endswith('.dbn.zst') or f.name.endswith('.dbn'):
            out=pq_dir/(f.name.replace('.dbn.zst','.parquet').replace('.dbn','.parquet'))
            db.DBNStore.from_file(f).to_parquet(out,pretty_ts=True,price_type='float',map_symbols=True)
            parquet.append(str(out))
    manifest={'job_id':job_id,'quote':quote,'downloaded_files':[str(x) for x in files],'parquet_files':parquet}
    (args.outdir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':
    main()
