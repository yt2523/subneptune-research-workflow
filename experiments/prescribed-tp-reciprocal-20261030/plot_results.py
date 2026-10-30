"""Replot saved summary into a NEW directory; no model/API calls."""
from pathlib import Path
import argparse,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);args=p.parse_args()
root=Path(__file__).resolve().parent
summary=json.loads((root/'summary.json').read_text());r=summary['recovery'];records=summary['records']
contract={'truth':summary['truth']};run=root/'data'
figdir=Path(args.output_dir).resolve();figdir.mkdir(parents=True,exist_ok=False)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150,'savefig.dpi':180})
fig,axes=plt.subplots(1,2,figsize=(11,4.1),layout='constrained');search=[q for q in records if q['kind']=='search']
axes[0].scatter([q['gas_fraction']*100 for q in search],[q['target_relative_residual']*100 for q in search],color='#24649a',label='New B40 search fits',s=48)
cached=(json.loads((run/'frozen-inputs.json').read_text())['reused_evidence']['B-truth']['radius_cm']/contract['truth']['radius_cm']-1)*100
axes[0].scatter([1],[cached],marker='s',facecolors='none',edgecolors='#24649a',label='Cached B40 upper endpoint',s=60);axes[0].axhline(0,color='#b25e36',ls='--',label='A30 target at 1% gas');axes[0].scatter([r['inferred_fraction']*100],[r['nominal_radius_relative_residual']*100],marker='*',color='#27936a',s=140,zorder=4,label='Validated local candidate')
axes[0].set(xscale='log',xlabel='Gas mass / total mass [%]',ylabel='Signed radius mismatch [%]',title='Same curves, EOS and truth fraction');axes[0].set_xticks([.05,.1,r['inferred_fraction']*100,1],labels=['0.05','0.1','0.2436','1.0']);axes[0].legend(fontsize=7.5,loc='lower right');axes[0].grid(alpha=.2)
vals=[abs(r['nominal_radius_relative_residual'])]+[abs(q['target_relative_residual']) for q in r['confirmation']];axes[1].bar(['Nominal','Tighter controls','More knots'],vals,color=['#24649a','#27936a','#75ad9c']);axes[1].axhline(1e-5,color='#b25e36',ls='--',label='Confirmation radius limit');axes[1].axhline(5e-6,color='#687b8c',ls=':',label='Nominal radius limit')
for i,v in enumerate(vals):axes[1].text(i,v*1.25,f'{v:.3e}',ha='center',fontsize=9)
axes[1].set(yscale='log',ylim=(1e-9,3e-5),ylabel='Absolute relative radius mismatch',title='Both independent numerical checks pass');axes[1].legend(fontsize=8,loc='upper left');axes[1].grid(axis='y',alpha=.2)
for suffix in ['png','svg']:fig.savefig(figdir/('reciprocal-recovery.'+suffix))
plt.close(fig)
