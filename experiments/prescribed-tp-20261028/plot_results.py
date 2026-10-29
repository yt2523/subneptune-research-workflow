"""Replot archived summary into a NEW directory; no model calls or archive modification."""
from pathlib import Path
import argparse,json,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);args=p.parse_args()
root=Path(__file__).resolve().parent
s=json.loads((root/'summary.json').read_text());cases={q['name']:q for q in s['cases']}
figdir=Path(args.output_dir).resolve();figdir.mkdir(parents=True,exist_ok=False)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150,'savefig.dpi':180})
fig,axes=plt.subplots(1,2,figsize=(11,4.2),layout='constrained')
for name,slope,color in [('A-truth',30,'#2563a6'),('B-truth',40,'#bd5937')]:
 q=cases[name];p=np.geomspace(.1,q['gas_base_pressure_GPa']*1e4,300);t=300+slope*np.log(p/.1);axes[0].plot(t,p,color=color,label=f'{name[0]}: 300 + {slope} ln(P / 0.1 bar)');axes[0].scatter(t[-1],p[-1],color=color,s=30)
axes[0].set(yscale='log',xlabel='Temperature [K]',ylabel='Pressure [bar]',title='Same outer boundary and density EOS');axes[0].invert_yaxis();axes[0].legend(fontsize=8);axes[0].grid(alpha=.2)
selected=[cases[x] for x in ['A-recovery-low','A-truth','A-recovery-high']];xs=[q['gas_fraction']*100 for q in selected];ys=[q['radius_earth'] for q in selected]
axes[1].scatter(xs,ys,color='#2563a6',s=48,label='A: three computed samples',zorder=3);axes[1].axhline(cases['B-truth']['radius_earth'],color='#bd5937',ls='--',label='B target at 1% gas');axes[1].scatter([1],[cases['B-truth']['radius_earth']],color='#bd5937',marker='*',s=110,zorder=4)
for x,y in zip(xs,ys):axes[1].annotate(f'{y:.6f}',(x,y),xytext=((-5 if x>5 else 4),7),ha=('right' if x>5 else 'left'),textcoords='offset points',fontsize=8)
axes[1].set(xscale='log',xlabel='Gas mass / total mass [%]',ylabel='Total radius [Earth equatorial radii]',title='No bracket; no inferred composition');axes[1].set_xticks([.2,1,8],labels=['0.2','1','8']);axes[1].grid(alpha=.2);axes[1].legend(fontsize=8,loc='upper right',bbox_to_anchor=(1,.88))
for suffix in ['png','svg']:fig.savefig(figdir/('tp-and-recovery.'+suffix))
plt.close(fig)
fig,ax=plt.subplots(figsize=(8,3.8),layout='constrained');x=np.arange(3);rock=[q['rounded_boundary']['radius_earth'] for q in selected];envelope=[q['rounded_boundary']['gas_thickness_earth'] for q in selected]
ax.bar(x,rock,color='#3d668d',width=.55,label='Rock-base radius (rounded profile)');ax.bar(x,envelope,bottom=rock,color='#8dc9d4',width=.55,label='Gas thickness')
for i,q in enumerate(selected):ax.text(i,q['radius_earth']+.015,f"R={q['radius_earth']:.6f}\nbase gas rho={q['gas_base_density']:.3f} g/cm³",ha='center',fontsize=9)
ax.set(xticks=x,xticklabels=['0.2% gas','1% gas','8% gas'],ylabel='Radius [Earth equatorial radii]',ylim=(0,2.02),title='Coupled structure in the ideal-mu2 fixture');ax.legend(fontsize=8,loc='lower right');ax.grid(axis='y',alpha=.15)
for suffix in ['png','svg']:fig.savefig(figdir/('radius-components.'+suffix))
plt.close(fig)
