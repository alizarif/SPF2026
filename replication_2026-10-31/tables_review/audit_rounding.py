"""Read-only audit of displayed changes; blue requires demonstrated formatting equivalence."""
from pathlib import Path
from collections import Counter
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP
import hashlib,json,math,re,sys,os
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'tables_review'/'table_data_verified.json'
if not P.exists():P=ROOT/'tables_review'/'table_data.json'
SNAPSHOT=P.read_bytes()
D=json.loads(SNAPSHOT)
def displayed_pairs(table):
 return {(c.get('audit_row',r['label']),c.get('audit_column',str(i))):(c['original_display'],c['replicated_display']) for r in table['rows'] if r['type']=='data' for i,c in enumerate(r['cells']) if c.get('kind')=='numeric'}
verified_tables={}
verified_sources={'T11':ROOT/'table11_investigation/verified_table.json','TB14':ROOT/'tableB14_investigation/verified_table.json'}
for tid,source in verified_sources.items():
 if source.exists():
  table=json.loads(source.read_text())
  if displayed_pairs(D[tid])==displayed_pairs(table):verified_tables[tid]=table
# Read the minimal credential-free table objects, exported from the historical R workspace.
import pandas as pd
archive_info=json.loads((ROOT/'data_cache/archived_generic_objects.json').read_text())
a={name:pd.read_parquet(ROOT/info['path']) for name,info in archive_info['objects'].items()}
saved_tests=a['tests'];saved_tests_by_name=saved_tests.set_index('variable_longname')
t8cols=[x for x in saved_tests.columns if x!='variable_longname' and not x.startswith('empty')]
rows8=[r for r in D['T8']['rows'] if r['type']=='data' and r['label']!='Average']
t8map={};t8evidence=[]
for i,r in enumerate(rows8):
 for j,col in enumerate(t8cols):
  orig=r['cells'][j+1]['starsoriginal'];pos=str(saved_tests.iloc[i][col]);named=str(saved_tests_by_name.loc[r['label'],col]);posstars=int(re.search('star([0-3])',pos)[1]);namestars=int(re.search('star([0-3])',named)[1])
  q={'row':r['label'],'column':r['cells'][j+1]['audit_column'],'published_stars':orig,'archived_positional_row_name':str(saved_tests.iloc[i].variable_longname),'archived_positional_test':pos,'archived_own_variable_test':named,'positional_matches_published':orig==posstars,'own_variable_stars':namestars,'row_alignment_changes_stars':orig!=namestars}
  t8map[(r['label'],q['column'])]=q;t8evidence.append(q)

def interval(original,precision,stars,is_p):
 u=10**(-precision);lo=original-u/2;hi=original+u/2
 if is_p:
  lo=max(0,lo);hi=min(1,hi)
  # R randomization_test chooses stars on raw p before sprintf.
  bounds={0:(.1,1),1:(.05,.1),2:(.01,.05),3:(0,.01)}
  slo,shi=bounds[stars];lo=max(lo,slo);hi=min(hi,shi)
 return lo,hi

cells=[];matched=Counter();total=Counter();tie_candidates=[]
for tid,t in D.items():
 for ri,r in enumerate(t['rows']):
  if r['type']!='data':continue
  for ci,c in enumerate(r['cells']):
   if c.get('kind')!='numeric':continue
   total[tid]+=1
   original=float(c['original']);rep=float(c['replicated']);precision=c.get('precision',2)
   if not math.isfinite(rep):continue
   unit=10**(-precision);scaled=rep/unit;half=math.floor(scaled)+.5;distance=abs(rep-half*unit)
   floating_tol=max(1e-12,64*abs(float(np.spacing(rep))))
   is_tie=distance<=floating_tol
   tie_can_explain=is_tie and min(abs(original-math.floor(scaled)*unit),abs(original-math.ceil(scaled)*unit))<1e-10
   if is_tie:tie_candidates.append({'item':tid,'row':c.get('audit_row',r['label']),'column':c.get('audit_column',t['columns'][ci]),'replicated':rep,'nearest_half_unit':half*unit,'distance':distance,'mismatch':c['mismatch']})
   if not c['mismatch']:
    matched[tid]+=1;continue
   row=c.get('audit_row',r['label']);col=c.get('audit_column',t['columns'][ci]);is_p=col.endswith(' p') or col.lower().startswith('p-val')
   so=c.get('starsoriginal',0);sr=c.get('starsreplicated',0)
   lo,hi=interval(original,precision,so,is_p)
   gap=max(lo-rep,rep-hi,0)
   q={'cell_key':[tid,ri,ci],'item':tid,'row_index':ri,'cell_index':ci,'row':row,'column':col,'original_display':c['original_display'],'replicated_display':c['replicated_display'],'original_printed_number':original,'replicated_unrounded':rep,'precision':precision,'numeric_mismatch':c.get('numeric_mismatch',True),'stars_original':so,'stars_replicated':sr,'recommended_color':'red','blue_eligible':False,'original_compatible_rounding_interval':[lo,hi],'distance_outside_original_interval':gap,'computed_value_near_half_unit':is_tie,'half_unit_tie_candidate':tie_can_explain,'provisional':tid in ['T11','TB14']}
   if tid in verified_tables:
    q['provisional']=False
    q.update(classification='verified_recalculation_difference_not_rounding',reason='The final independently checked recalculation uses an explicitly declared estimator/data pipeline. The published original unrounded estimate is not established as identical; adjacent display values or exact-test half-cent boundaries are insufficient to demonstrate a rounding-only difference.')
   elif tid in ['T11','TB14']:
    q.update(classification='provisional_estimator_or_data_difference',reason='The underlying estimator/data pipeline is still being investigated. Even a small difference cannot be assigned to rounding before the same unrounded quantity is established.',correction_status='Qualified reconstruction, not a proven correction')
   elif tid=='T8':
    ev=t8map[(row,col)];q['archived_test_assignment']=ev
    if ev['row_alignment_changes_stars']:
     q.update(classification='verified_significance_row_assignment_difference',reason='Published stars equal a different variable’s archived test at the same row position; matching archived tests by variable changes these stars. This is an assignment error, not numeric formatting.')
    else:q.update(classification='significance_difference_not_rounding',reason='The ratio matches at printed precision, but significance differs. Source code selects stars before formatting p-values; no evidence identifies a rounding-only change.')
   elif is_p:
    pooled=(original+rep)/2;se=math.sqrt(max(0,2*pooled*(1-pooled)/10000))
    compatible=gap<=3*se
    q['monte_carlo_diagnostic']={'draws_assumed_each':10000,'approx_two_run_standard_error':se,'distance_to_original_interval':gap,'compatible_with_3SE_plus_original_rounding_interval':compatible,'warning':'Compatibility is not proof of a shared estimator or dataset and does not make the difference a formatting issue. T6 has variable valid-draw counts, so 10000 is approximate.'}
    if tid=='T5' and (row,col.split()[0]+' Share') in [('Unemployment Rate','h0 Share'),('Real Net Exports','h0 Share')]:
     q.update(classification='p_value_with_changed_observed_statistic',reason='The corresponding exact quarter share also differs. The p-value change is not a display rounding error.')
    elif compatible:q.update(classification='monte_carlo_compatible_not_rounding',reason='The raw simulated p-value differs; the printed change is statistically compatible with simulation variation. No same-value/different-formatter evidence exists. Stars are assigned before rounding.')
    else:q.update(classification='inferential_difference_exceeds_mc_diagnostic',reason='The raw p-value differs beyond a conservative two-run Monte Carlo diagnostic. Changed inputs, test construction, or source version require investigation; not rounding.')
   else:q.update(classification='deterministic_numeric_difference',reason='The recalculated unrounded value lies outside the interval that would print as the published number. It is not a half-unit tie, and no saved original intermediate proves a formatter-only difference.')
   if tie_can_explain and tid not in ['T11','TB14']:
    q['reason']+=' Half-unit proximity would require separate review of exact arithmetic and the source formatter; proximity alone does not justify blue.'
   cells.append(q)
header={'item':'TB13','kind':'header','original_display':'Horizon 2','replicated_display':'Horizon 4','recommended_color':'red','blue_eligible':False,'classification':'substantive_horizon_label_difference','reason':'The data horizon identifier differs; not a rounding operation.'}
criteria={
 'blue':'Only a demonstrated same underlying estimate with a display-only discrepancy: documented different rounding conventions at a mathematically established half-unit boundary, verified intermediate/double rounding, or harmless binary representation at that same boundary. A +/-0.01 change alone is insufficient.',
 'black':'Identical published and replicated displayed value and significance. Matching rounded values do not establish equal unrounded estimates.',
 'red':'Any unresolved change in estimated magnitude, sample, model, target, test, p-value realization, or significance assignment. Monte Carlo-compatible changes are explicitly labeled stochastic rather than described as substantive scientific disagreement.',
 'monte_carlo':'Different random draws produce different unrounded p-values. Even when they round to adjacent cent values or change a threshold star, they are not rounding-only. Require identical unrounded p to label formatting-only.',
 'stars':'The supplied randomization_test.R computes p<=.10/.05/.01 stars before sprintf("%.2f",p). Therefore a star change cannot be attributed solely to printing p to two decimals.',
 'pending':'T11 and TB14 classifications apply only to the present snapshot and must be refreshed after their estimator/data investigations; possible new half-cent cases are tracked separately.'}
summary={'numeric_cells':sum(total.values()),'printed_match_cells':sum(matched.values()),'current_mismatched_cells':len(cells),'blue_confirmed':sum(x['blue_eligible'] for x in cells),'red_recommended':len(cells),'header_red':1,'provisional_cells':sum(x['provisional'] for x in cells),'by_table':{k:{'total':total[k],'match':matched[k],'mismatch':total[k]-matched[k]} for k in D},'by_classification':dict(Counter(x['classification'] for x in cells)),'mismatched_half_unit_candidates':sum(x['half_unit_tie_candidate'] for x in cells)}
report={'audit_version':1,'scope':'All15-table current review snapshot; original builder and source data unchanged.','source_table_data':str(P.relative_to(ROOT)),'source_table_data_sha256':hashlib.sha256(SNAPSHOT).hexdigest(),'classification_valid_for_snapshot_only':True,'pending_refresh_tables':['T11','TB14'],'criteria':criteria,'summary':summary,'cells':cells,'header_cells':[header],'current_snapshot_half_unit_candidates_including_matches':tie_candidates,'T8_archival_evidence':{'source':archive_info['source'],'sha256':archive_info['original_sha256'],'portable_objects':archive_info['objects'],'object':'tests','total_star_cells':len(t8evidence),'published_matches_positional_saved_tests':sum(x['positional_matches_published'] for x in t8evidence),'published_matches_correctly_named_saved_tests':sum(not x['row_alignment_changes_stars'] for x in t8evidence),'mappings':t8evidence,'code_evidence':['functions/tab_forecast_accuracy_generic.R orders accuracy with variables and constructs tests without analogous reordering.','functions/add_stars.R assigns tests[ii,jj] by position and references global tests rather than formal test.']},'original_intermediate_search':{'generic_output_RData':'Decoded accuracy matrices retain full precision. No-data ratios agree with replicated values; saved tests are already formatted two-decimal strings plus star labels. No recoverable original unrounded p-values in these test objects.','RData_and_rand_test_moments_output_RData':'pyreadr listing fails due unsupported serialized features, consistent with initial inventory. Cannot claim these prove or disprove original unrounded values.','original_tex_tables':'Relevant latest draft/tables and processing/tables files contain two-decimal printed values, not hidden higher precision.','recomputation_audits':['core_tables_results.json','cell_comparison.json','tables_review/independent_core_expected.json','annotated_extended_table_data.json'],'no_demonstrated_rounding_only_cells_in_current_snapshot':True}}
# Keep the builder contract explicit. A cell is blue only if classification is
# exactly 'rounding_only'; all current cells retain their evidence-based class.
report['audit_version']=2
report['pending_refresh_tables']=[tid for tid in ['T11','TB14'] if tid not in verified_tables]
report['verified_recalculation_tables_in_snapshot']=list(verified_tables)
report['classifications']=[{k:q[k] for k in ['item','row','column','classification','original_display','replicated_display','recommended_color','blue_eligible','provisional','reason']} for q in cells]
new_b14=ROOT/'tableB14_investigation/verified_table.json'
if new_b14.exists():
 b14=json.loads(new_b14.read_text());new_cells=[]
 for r in b14['rows']:
  if r['type']!='data':continue
  for c in r['cells']:
   if c.get('kind')!='numeric' or not c.get('mismatch'):continue
   col=c['audit_column'];is_p=col.endswith(' p')
   q={k:c[k] for k in ['original_display','replicated_display']}
   q.update(item='TB14',row=c['audit_row'],column=col,replicated_unrounded=c['replicated'],blue_eligible=False,recommended_color='red',classification='exact_test_or_input_difference_not_rounding' if is_p else 'caption_estimator_or_data_difference_not_rounding')
   q['reason']='Caption-consistent recomputation changes the inputs/estimator and uses exact enumeration rather than the original simulated test. Printed adjacency or a half-unit boundary alone does not prove equality of the underlying original value.' if is_p else 'The caption-consistent estimator and current data differ from the historical source pipeline; no identical original unrounded estimate was established.'
   if q['row']=='Unemployment Rate' and col=='h0 AI':
    q['reason']='Current best-within-quarter MAE has exact decimal value 0.075 (binary calculation 0.07499999999999996). The historical best-person-over-time estimate underlying published 0.08 is approximately 0.0766667 over three available observations. These are different estimates/samples; final deterministic decimal half-even formatting should show 0.08 for the current value and remove this display mismatch.'
   new_cells.append(q)
 report['pending_caption_consistent_B14']={'source':str(new_b14.relative_to(ROOT)),'sha256':hashlib.sha256(new_b14.read_bytes()).hexdigest(),'scope':'Additional classifications for the new verified table; do not overlay unless the final canonical table uses exactly these original/replicated display pairs.','blue_confirmed':0,'mismatched_cells':len(new_cells),'classifications':new_cells,'historical_half_cent_provenance_only':{'explanation':'Historical CPROF h1 AI 333.605 and PCE h1 AI 0.805 are potential formatting boundaries, but the final caption-consistent estimates differ; neither supports a blue final-table override.','excluded_from_final_overrides':True}}
new_t11=ROOT/'table11_investigation/verified_table.json'
if new_t11.exists():
 t11=json.loads(new_t11.read_text());new_cells=[]
 for r in t11['rows']:
  if r['type']!='data':continue
  for c in r['cells']:
   if c.get('kind')!='numeric' or not c.get('mismatch'):continue
   new_cells.append(dict(item='T11',row=c['audit_row'],column=c['audit_column'],original_display=c['original_display'],replicated_display=c['replicated_display'],replicated_unrounded=c['replicated'],blue_eligible=False,recommended_color='red',classification='declared_model_recalculation_difference_not_rounding',reason='Verified regression uses the newly declared timing/sample/identity method. No mismatched estimate is a half-unit boundary, and no identical original unrounded value was recovered.'))
 report['pending_declared_method_T11']={'source':str(new_t11.relative_to(ROOT)),'sha256':hashlib.sha256(new_t11.read_bytes()).hexdigest(),'scope':'Additional classifications for the verified declared-method table; only apply to exactly matching final display pairs.','blue_confirmed':0,'mismatched_cells':len(new_cells),'classifications':new_cells}
(ROOT/'tables_review/rounding_audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False))
print(json.dumps(summary,indent=2))
