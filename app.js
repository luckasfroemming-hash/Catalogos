document.getElementById('yr').textContent=new Date().getFullYear();
function imgL(h){return'./images/'+h+'.jpg'}
function imgP(h){return'https://wsrv.nl/?url=photo.yupoo.com/ovosneaker/'+h+'/medium.jpg'}
var nav=document.getElementById('nav');
function mkB(l,fn,n){var b=document.createElement('button');b.className='nb';b.dataset.s=l.toLowerCase();b.innerHTML='<span>'+l+'</span>'+(n?'<span class="cnt">'+n+'</span>':'');b.onclick=fn;return b}
var hb=mkB('Inicio',function(){sa(hb);home()});hb.classList.add('active');nav.appendChild(hb);
C.forEach(function(c){var n=P.filter(function(p){return p.cat===c}).length;var b=mkB(c,function(){sa(b);showCat(c)},n);nav.appendChild(b)});
function sa(el){document.querySelectorAll('.nb').forEach(function(b){b.classList.remove('active')});el.classList.add('active')}
document.getElementById('si').addEventListener('input',function(){var q=this.value.toLowerCase();document.querySelectorAll('.nb').forEach(function(b){b.style.display=(!q||b.dataset.s.includes(q))?'':'none'})});
function home(){
  document.getElementById('ttl').textContent='CATALOGO';
  document.getElementById('tsub').textContent=P.length+' produtos';
  var h='<div class="hero"><h2>PRODUTOS<br><span>PREMIUM</span></h2><p>Selecione uma categoria no menu lateral.</p><div class="hero-n"><div><div class="n">'+P.length+'</div><div class="l">Produtos</div></div><div><div class="n">'+C.length+'</div><div class="l">Categorias</div></div></div></div><p class="sec">CATEGORIAS</p><div class="cg" id="cg"></div>';
  document.getElementById('pc').innerHTML=h;
  var cg=document.getElementById('cg');
  C.forEach(function(c){var n=P.filter(function(p){return p.cat===c}).length;var d=document.createElement('div');d.className='cc';d.innerHTML='<div class="nm">'+c+'</div><div class="inf">'+n+' modelos</div>';d.onclick=function(){showCat(c)};cg.appendChild(d)});
}
function showCat(name){
  var ps=P.filter(function(p){return p.cat===name});
  document.getElementById('ttl').textContent=name.toUpperCase();
  document.getElementById('tsub').textContent=ps.length+' modelos';
  if(!ps.length){document.getElementById('pc').innerHTML='<div style="text-align:center;padding:60px;color:var(--mut)">Sem produtos</div>';return}
  document.getElementById('pc').innerHTML='<div class="pg" id="pg"></div>';
  var pg=document.getElementById('pg');
  ps.forEach(function(p){
    var d=document.createElement('div');d.className='pd';
    var s=imgL(p.cover);
    d.innerHTML='<img src="'+s+'" alt="'+p.title+'" loading="lazy" onerror="this.src=\''+imgP(p.cover)+'\';this.onerror=null"><div class="pi"><div class="pt">'+p.title+'</div><div class="ps">'+p.cat+'</div></div>';
    d.onclick=(function(pr){return function(){openLB(pr)}})(p);pg.appendChild(d);
  });
}
var LB={ph:[],i:0,t:'',id:''};
function openLB(p){LB.ph=p.photos||[p.cover];LB.i=0;LB.t=p.title;LB.id=p.id;document.getElementById('lb').classList.add('open');document.body.style.overflow='hidden';drawLB();loadAlb(p.id)}
function loadAlb(id){fetch('https://api.allorigins.win/get?url='+encodeURIComponent('https://ovosneaker.x.yupoo.com/albums/'+id+'?uid=1')).then(function(r){return r.json()}).then(function(d){var h=d.contents||'',hs=[],s={};var re=/photo\.yupoo\.com\/[^\/]+\/([a-f0-9]{8})\/(?:medium|small)\.jpg/g,m;while((m=re.exec(h))!==null){if(!s[m[1]]){s[m[1]]=1;hs.push(m[1]);}}if(hs.length>1&&LB.id===id){LB.ph=hs;drawLB();}}).catch(function(){})}
function drawLB(){var i=document.getElementById('lbi'),h=LB.ph[LB.i];i.style.opacity='.3';i.src=imgL(h);i.onerror=function(){this.src=imgP(h);this.onerror=null};i.onload=function(){i.style.opacity='1'};document.getElementById('lbn').textContent=(LB.i+1)+' / '+LB.ph.length;document.getElementById('lbt').textContent=LB.t;document.getElementById('lbp').disabled=LB.i===0;document.getElementById('lbnx').disabled=LB.i===LB.ph.length-1;var s=document.getElementById('lbs');if(LB.ph.length>1){s.innerHTML=LB.ph.map(function(h,i){return'<img src="'+imgL(h)+'" class="'+(i===LB.i?'on':'')+'" onclick="gLB('+i+')" onerror="this.src=\''+imgP(h)+'\';this.onerror=null">'}).join('');s.style.display='flex'}else s.style.display='none'}
function gLB(i){LB.i=i;drawLB()}
function closeLB(){document.getElementById('lb').classList.remove('open');document.body.style.overflow=''}
document.getElementById('lbx').onclick=closeLB;
document.getElementById('lbp').onclick=function(){if(LB.i>0){LB.i--;drawLB()}};
document.getElementById('lbnx').onclick=function(){if(LB.i<LB.ph.length-1){LB.i++;drawLB()}};
document.getElementById('lb').addEventListener('click',function(e){if(e.target===this)closeLB()});
document.addEventListener('keydown',function(e){if(!document.getElementById('lb').classList.contains('open'))return;if(e.key==='Escape')closeLB();if(e.key==='ArrowLeft'&&LB.i>0){LB.i--;drawLB()}if(e.key==='ArrowRight'&&LB.i<LB.ph.length-1){LB.i++;drawLB()}});
var tx=0;document.getElementById('lb').addEventListener('touchstart',function(e){tx=e.touches[0].clientX},{passive:true});document.getElementById('lb').addEventListener('touchend',function(e){var d=e.changedTouches[0].clientX-tx;if(Math.abs(d)>50){if(d<0&&LB.i<LB.ph.length-1){LB.i++;drawLB()}else if(d>0&&LB.i>0){LB.i--;drawLB()}}},{passive:true});
document.getElementById('mob').onclick=function(){document.getElementById('sb').classList.toggle('open')};
document.querySelector('main').addEventListener('click',function(){document.getElementById('sb').classList.remove('open')});
home();
