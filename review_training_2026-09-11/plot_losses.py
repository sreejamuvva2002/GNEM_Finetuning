"""Plot logged loss windows. Requires matplotlib; does not read model weights."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
rows=json.loads((ROOT/'loss_history.json').read_text())
variants=['A_cpt','B_facts','C_answers','D_sql','BC_facts_answers','BD_facts_sql']
fig,axes=plt.subplots(2,3,figsize=(13,7),layout='constrained')
for ax,v in zip(axes.flat,variants):
 h=[r for r in rows if '/run_v2_20260812_170423/'in r['path']and r['variant']==v]
 ax.plot([r['epoch']for r in h],[r['loss']for r in h],color='#1769aa',linewidth=1.8,marker='o'if v=='A_cpt'else None)
 ax.set(title=v,xlabel='Epoch',ylabel='Logged training loss (log scale)',yscale='log');ax.grid(alpha=.2,which='both')
 ax.annotate(f"Last logged: {h[-1]['loss']:.5g}",(h[-1]['epoch'],h[-1]['loss']),xytext=(-6,10),textcoords='offset points',ha='right',fontsize=9)
 if v=='A_cpt':ax.text(.03,.04,'Only two loss windows recorded',transform=ax.transAxes,fontsize=9)
fig.suptitle('GNEM v2: recorded training-loss windows, original six-arm run\nNo validation losses; different supervision targets across arms',fontsize=14)
fig.savefig(ROOT/'loss_curves.png',dpi=180);fig.savefig(ROOT/'loss_curves.pdf');plt.close(fig)
fig,axes=plt.subplots(2,3,figsize=(13,7),layout='constrained')
for ax,v in zip(axes.flat,[x for x in variants if x!='BC_facts_answers']):
 for seed in ['13','29','47','61','79']:
  h=[r for r in rows if '/run_v2_'in r['path']and r['variant']==v and r['seed_label']==seed]
  ax.plot([r['epoch']for r in h],[r['loss']for r in h],label=seed,alpha=.8,linewidth=1.2)
 ax.set(title=v,xlabel='Epoch',ylabel='Logged training loss (log scale)',yscale='log');ax.grid(alpha=.2,which='both')
axes.flat[-1].axis('off');handles,labels=axes.flat[0].get_legend_handles_labels();axes.flat[-1].legend(handles,labels,title='Training seed',loc='center')
fig.suptitle('GNEM v2: five-seed training-loss histories\nTraining fit only; this plot does not establish generalization',fontsize=14)
fig.savefig(ROOT/'seed_loss_curves.png',dpi=180);fig.savefig(ROOT/'seed_loss_curves.pdf');plt.close(fig)
print('Created original-run and seed-sweep PNG/PDF loss curves.')
