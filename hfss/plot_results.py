"""Plot real HFSS CSV exports only. Does not generate example simulation data."""
import argparse
import csv
import json
import math
from pathlib import Path


def read_csv(path):
    with path.open(encoding='utf-8',newline='') as f:
        rows=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
    if not rows: raise ValueError('No solver data in '+str(path))
    if any(not math.isfinite(v) for r in rows for v in r.values()):
        raise ValueError('Nonfinite solver data')
    return sorted(rows,key=lambda r:r['frequency_GHz'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path,help='Directory containing Sweep100_220.csv')
    args=parser.parse_args()
    rows=read_csv(args.output/'Sweep100_220.csv')
    f=[r['frequency_GHz'] for r in rows]
    if abs(f[0]-100)>1e-6 or abs(f[-1]-220)>1e-6:
        raise ValueError('Sweep does not cover the intended 100-220 GHz range')
    report={'s11_min_GHz':min(rows,key=lambda r:r['S11_dB'])['frequency_GHz'],
            's11_min_dB':min(r['S11_dB'] for r in rows),
            'negative_real_Z_count':sum(r['Zin_real_ohm'] < -1 for r in rows),
            'S11_above_0_05dB_count':sum(r['S11_dB'] > 0.05 for r in rows),
            'note':'Numerical checks only; adaptive/boundary convergence must be reviewed separately.'}
    direct_path=args.output/'CheckDiscrete.csv'
    direct=read_csv(direct_path) if direct_path.exists() else []
    if direct:
        errors=[]
        for r in direct:
            near=min(rows,key=lambda t:abs(t['frequency_GHz']-r['frequency_GHz']))
            if abs(near['frequency_GHz']-r['frequency_GHz'])>1e-6:
                raise ValueError('Discrete validation frequency missing in interpolated grid')
            errors.append(abs(complex(r['S11_real'],r['S11_imag'])-
                              complex(near['S11_real'],near['S11_imag'])))
        report['max_complex_S11_discrete_difference']=max(errors)
        report['discrete_difference_below_0_02']=max(errors)<0.02
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,left=plt.subplots(figsize=(9,5))
    right=left.twinx()
    lines=left.plot(f,[r['Zin_real_ohm']/1000 for r in rows],color='#b92262',label='Re(Zin)')
    lines+=left.plot(f,[r['Zin_imag_ohm']/1000 for r in rows],color='#6cabe0',label='Im(Zin)')
    lines+=right.plot(f,[r['S11_dB'] for r in rows],color='black',label='S11, 1 kohm ref.')
    if direct:
        right.plot([r['frequency_GHz'] for r in direct],[r['S11_dB'] for r in direct],
                   'o',mfc='none',mec='black',ms=4,label='Discrete checks')
    left.axvline(130,color='gray',linestyle='--',linewidth=0.8)
    left.set_xlim(100,220);left.set_xlabel('Frequency (GHz)')
    left.set_ylabel('Zin (kohm)');right.set_ylabel('S11 (dB)')
    left.grid(alpha=0.2)
    left.set_title('HFSS approximate model — not the authors\' geometry')
    left.legend(lines,[line.get_label() for line in lines],loc='best')
    fig.tight_layout();fig.savefig(args.output/'fig2d_approx.png',dpi=220)
    fig.savefig(args.output/'fig2d_approx.pdf');plt.close(fig)
    (args.output/'numerical_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
