/** Build the comparison workbook from final replication JSON records.
 * Run with the bundled Node runtime after both input files are finalized.
 * Uses the public @oai/artifact-tool API. No original research files are edited.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';

const run = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const workspace = path.dirname(run);
// Optional workbook dependency: use a normal local installation, or an explicit runtime.
let artifactTool;
if (process.env.REPLICATION_NODE_MODULES) {
  const require = createRequire(path.join(path.resolve(process.env.REPLICATION_NODE_MODULES), '..', 'package.json'));
  artifactTool = await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
} else {
  artifactTool = await import('@oai/artifact-tool');
}
const {Workbook,SpreadsheetFile} = artifactTool;
const summaryData=JSON.parse(await fs.readFile(path.join(run,'replication_comparison.json'),'utf8'));
const cells=JSON.parse(await fs.readFile(path.join(run,'cell_comparison.json'),'utf8'));
if(!Array.isArray(summaryData)||!Array.isArray(cells))throw new Error('Both comparison inputs must be JSON lists.');
if(summaryData.length!==23)throw new Error(`Expected 23 unique paper items, found ${summaryData.length}.`);
if(new Set(summaryData.map(x=>x.id)).size!==summaryData.length)throw new Error('Duplicate summary item ids.');
const outputDir=path.join(workspace,'outputs','replication');
const support=path.join(run,'workbook_qa');
await fs.mkdir(outputDir,{recursive:true});await fs.mkdir(support,{recursive:true});
const wb=Workbook.create();
const summary=wb.worksheets.add('Summary');
const audit=wb.worksheets.add('Cell audit');
const COLORS={ink:'#173B52',light:'#EEF3F6',green:'#DCEEDC',orange:'#FFE7C2',neutral:'#EEF0F2',text:'#1D2730'};
const safe=v=>v==null?null:(typeof v==='string'&&v.startsWith('=')?"'"+v:v);
const numberOrBlank=v=>v==null?null:Number.isFinite(Number(v))?Number(v):safe(String(v));
const joined=v=>Array.isArray(v)?v.join('; '):v==null?'':String(v);
function base(sheet,endRow,endCol) {
  sheet.showGridLines=false;
  sheet.getRange(`A1:${endCol}${endRow}`).format.font={name:'Arial',size:10,color:COLORS.text};
  sheet.getRange(`A1:${endCol}${endRow}`).format.verticalAlignment='center';
  sheet.getRange(`A1:${endCol}${endRow}`).format.rowHeight=20;
  sheet.freezePanes.freezeRows(8);sheet.freezePanes.freezeColumns(2);
}
function header(sheet,range) {
  const h=sheet.getRange(range);h.format.fill=COLORS.ink;h.format.font={name:'Arial',size:10,bold:true,color:'#FFFFFF'};
  h.format.wrapText=true;h.format.horizontalAlignment='center';h.format.rowHeight=36;
  h.format.borders={preset:'inside',style:'thin',color:'#FFFFFF'};
}
function statusFill(item) {
  const status=String(item.status||'').toLowerCase();
  if(/documentary|illustrative|source image|source reproduced/.test(status))return COLORS.neutral;
  if(/partial|unresolved|mismatch|caveat|limitation|horizon|not reproduced|unavailable|approximate|differences|close reproduction/.test(status))return COLORS.orange;
  if(/exact|match|reproduced|verified|compatible/.test(status))return COLORS.green;
  return COLORS.neutral;
}
base(summary,Math.max(35,summaryData.length+10),'P');
summary.tabColor=COLORS.ink;
summary.getRange('A2').values=[['Replication comparison']];summary.getRange('A2').format.font={size:16,bold:true,color:COLORS.ink};summary.getRange('A2:P2').format.rowHeight=27;
summary.getRange('A3').values=[['Predictable Forecasters, June 2026 draft. Comparison run: 31 October 2026.']];
summary.getRange('A4').values=[['Original PDF: paper/predictable_forecasters.pdf']];
summary.getRange('A5').values=[['Monte Carlo tests: 10,000 draws, seed 20261031. Rounded agreement and Monte Carlo compatibility are reported separately.']];
summary.getRange('A6').values=[['Green: match. Orange: partial match or caveat. Gray: documentary or not numerically tested. Blank counts mean not applicable or not tested.']];
summary.getRange('A7').values=[['Evidence, limitations, and file paths are in columns M–P. The Cell audit tab includes every compared number.']];
summary.getRange('A3:P6').format.font={name:'Arial',size:10,color:'#45525E'};
summary.getRange('A7:P7').format.font={name:'Arial',size:10,color:'#45525E',italic:true};
const sh=['Item','Title','PDF pages','Result','Value matches','Values tested','p rounded matches','p MC compatible','p values tested','Stars matched','Stars tested','','Evidence','Limitations','Reproduced files','Source scripts'];
summary.getRange('A8:P8').values=[sh];header(summary,'A8:K8');header(summary,'M8:P8');
const rows=summaryData.map(x=>[x.id,x.title,joined(x.original_pages),x.status,numberOrBlank(x.point_match),numberOrBlank(x.point_total),numberOrBlank(x.p_rounded_match),numberOrBlank(x.p_mc_compatible),numberOrBlank(x.p_total),numberOrBlank(x.stars_match),numberOrBlank(x.stars_total),null,joined(x.evidence),joined(x.limitations),joined(x.reproduced_paths),joined(x.source_scripts)].map(safe));
summary.getRange(`A9:P${8+rows.length}`).values=rows;
const widths={A:10,B:44,C:12,D:31,E:13,F:13,G:15,H:16,I:14,J:13,K:13,L:3,M:98,N:98,O:78,P:78};
for(const [c,w]of Object.entries(widths))summary.getRange(`${c}1:${c}${rows.length+10}`).format.columnWidth=w;
summary.getRange(`E9:K${8+rows.length}`).setNumberFormat('#,##0');
summary.getRange(`E9:K${8+rows.length}`).format.horizontalAlignment='right';
summary.getRange(`B9:D${8+rows.length}`).format.wrapText=true;
summary.getRange(`M9:P${8+rows.length}`).format.wrapText=true;
for(let i=0;i<rows.length;i++) {
  const r=i+9;
  if(i%2===1){summary.getRange(`A${r}:K${r}`).format.fill=COLORS.light;summary.getRange(`M${r}:P${r}`).format.fill=COLORS.light;}
  summary.getRange(`D${r}`).format.fill=statusFill(summaryData[i]);
  const lines=Math.max(Math.ceil(String(rows[i][1]||'').length/42),Math.ceil(String(rows[i][3]||'').length/29),...rows[i].slice(12).map((v,j)=>String(v||'').split('\n').reduce((n,s)=>n+Math.max(1,Math.ceil(s.length/(j<2?96:74))),0)));
  summary.getRange(`A${r}:P${r}`).format.rowHeight=Math.max(32,lines*12.5+9);
}

base(audit,Math.max(12,cells.length+8),'J');
audit.getRange('A2').values=[['Numeric cell comparison']];audit.getRange('A2').format.font={size:16,bold:true,color:COLORS.ink};audit.getRange('A2:J2').format.rowHeight=27;
audit.getRange('A3').values=[['Original values are transcribed from the final PDF; replicated values are independently computed.']];
audit.getRange('A4').values=[['Absolute differences and tolerance checks calculate from the displayed input columns. Rounded match records the replication comparison.']];
audit.getRange('A5').values=[['Summary counts are a snapshot of the same replication run. Item-specific method caveats are on Summary.']];
audit.getRange('A6').values=[['A blank original, replicated value, or tolerance remains unassessed; it is not treated as zero.']];
audit.getRange('A3:J6').format.font={name:'Arial',size:10,color:'#45525E'};
const ah=['Item','Row','Column / measure','Original','Replicated','Absolute difference','Kind','Rounded match','Tolerance','Within tolerance'];
audit.getRange('A8:J8').values=[ah];header(audit,'A8:J8');
const ar=cells.map(x=>[safe(x.item),safe(x.row),safe(x.column),numberOrBlank(x.original),numberOrBlank(x.replicated),null,safe(x.kind),x.rounded_match==null?null:Boolean(x.rounded_match),numberOrBlank(x.tolerance),null]);
if(ar.length){
  audit.getRange(`A9:J${ar.length+8}`).values=ar;
  const auditTable=audit.tables.add(`A8:J${ar.length+8}`,true,'NumericAudit');
  auditTable.style='TableStyleLight1';auditTable.showFilterButton=true;
  audit.getRange(`F9:F${ar.length+8}`).formulas=ar.map((_,i)=>[`=IF(AND(ISNUMBER(D${i+9}),ISNUMBER(E${i+9})),ABS(E${i+9}-D${i+9}),"")`]);
  audit.getRange(`J9:J${ar.length+8}`).formulas=ar.map((_,i)=>[`=IF(AND(ISNUMBER(F${i+9}),ISNUMBER(I${i+9})),F${i+9}<=I${i+9},"")`]);
  audit.getRange(`D9:F${ar.length+8}`).setNumberFormat('0.########');audit.getRange(`I9:I${ar.length+8}`).setNumberFormat('0.########');
  audit.getRange(`D9:F${ar.length+8}`).format.horizontalAlignment='right';audit.getRange(`I9:I${ar.length+8}`).format.horizontalAlignment='right';
  audit.getRange(`H9:H${ar.length+8}`).format.horizontalAlignment='center';audit.getRange(`J9:J${ar.length+8}`).format.horizontalAlignment='center';
  audit.getRange(`B9:C${ar.length+8}`).format.wrapText=true;
  for(const c of ['H','J']) {
    audit.getRange(`${c}9:${c}${ar.length+8}`).conditionalFormats.add('cellIs',{operator:'equal',formula:'TRUE',format:{fill:COLORS.green}});
    audit.getRange(`${c}9:${c}${ar.length+8}`).conditionalFormats.add('cellIs',{operator:'equal',formula:'FALSE',format:{fill:COLORS.orange}});
  }
  for(let i=0;i<ar.length;i++) {
    const r=i+9;if(i%2===1)audit.getRange(`A${r}:J${r}`).format.fill=COLORS.light;
    const lines=Math.max(Math.ceil(String(ar[i][1]||'').length/33),Math.ceil(String(ar[i][2]||'').length/26));
    audit.getRange(`A${r}:J${r}`).format.rowHeight=Math.max(22,lines*12+6);
  }
}
const aw={A:11,B:35,C:28,D:18,E:18,F:21,G:20,H:18,I:18,J:20};
for(const[c,w]of Object.entries(aw))audit.getRange(`${c}1:${c}${cells.length+10}`).format.columnWidth=w;
wb.recalculate();
const inspection=await wb.inspect({kind:'region',sheetId:'Summary',range:'A8:K14',maxChars:4500,tableMaxRows:7,tableMaxCols:11});
await fs.writeFile(path.join(support,'summary_inspection.txt'),inspection.ndjson);
const errorScan=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},maxChars:5000});
await fs.writeFile(path.join(support,'formula_error_scan.txt'),errorScan.ndjson);
for(const spec of [
 {sheetName:'Summary',range:'A1:K16',name:'summary_counts.png'},
 {sheetName:'Summary',range:'M8:N16',name:'summary_notes.png'},
 {sheetName:'Summary',range:'M19:N22',name:'summary_method_notes.png'},
 {sheetName:'Summary',range:'M29:N31',name:'summary_oos_notes.png'},
 {sheetName:'Summary',range:`A${Math.max(9,rows.length)}:K${rows.length+8}`,name:'summary_last_rows.png'},
 {sheetName:'Cell audit',range:`A1:J${Math.min(20,cells.length+8)}`,name:'cell_audit.png'}
]) {
  const preview=await wb.render({sheetName:spec.sheetName,range:spec.range,scale:1,format:'png'});
  await fs.writeFile(path.join(support,spec.name),new Uint8Array(await preview.arrayBuffer()));
}
const output=await SpreadsheetFile.exportXlsx(wb);const outputPath=path.join(outputDir,'replication_comparison.xlsx');await output.save(outputPath);
await fs.writeFile(path.join(support,'workbook_manifest.json'),JSON.stringify({output:outputPath,summaryRows:summaryData.length,auditRows:cells.length,formulaCells:cells.length*2,inputFiles:['replication_comparison.json','cell_comparison.json']},null,2));
console.log(JSON.stringify({output:outputPath,summaryRows:summaryData.length,auditRows:cells.length}));
