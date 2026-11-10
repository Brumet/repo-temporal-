const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const p=await b.newPage({viewport:{width:1400,height:1400}});
for(const [q,out] of JSON.parse(process.argv[2])){await p.goto('http://localhost:8765/index.html?'+q);await p.waitForFunction(()=>document.title==='ok',null,{timeout:60000});await p.screenshot({path:out});}
await b.close();})();
