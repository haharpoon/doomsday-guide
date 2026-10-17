from PIL import Image, ImageDraw, ImageFont
G=(0x1A,0xFF,0x80);K=(0,0,0);W,H=480,284
F="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
fn=lambda s:ImageFont.truetype(F,s)
def spline(p,n=12):
    if len(p)<3: return p
    P=[p[0]]+p+[p[-1]];out=[]
    for i in range(1,len(P)-2):
        p0,p1,p2,p3=P[i-1],P[i],P[i+1],P[i+2]
        for k in range(n):
            t=k/n;t2=t*t;t3=t2*t
            out.append(tuple(0.5*((2*p1[j])+(-p0[j]+p2[j])*t+(2*p0[j]-5*p1[j]+4*p2[j]-p3[j])*t2+(-p0[j]+3*p1[j]-3*p2[j]+p3[j])*t3) for j in (0,1)))
    out.append(p[-1]);return out
ROPE=7;HALO=19
def _seg_layers(path):
    pts=[(p[0],p[1]) for p in path];L=[p[2] for p in path]
    n=12;sp=spline(pts,n);pieces=[]
    for i,q in enumerate(sp):
        lay=L[min(i//n,len(L)-1)]
        if pieces and pieces[-1][0]==lay: pieces[-1][1].append(q)
        else:
            prev=pieces[-1][1][-1] if pieces else q
            pieces.append((lay,[prev,q]))
    return pieces
def _arrow(d,a,b):
    import math
    ang=math.atan2(b[1]-a[1],b[0]-a[0]);s=14
    d.polygon([(b[0]+6*math.cos(ang),b[1]+6*math.sin(ang)),(b[0]-s*math.cos(ang-0.6),b[1]-s*math.sin(ang-0.6)),(b[0]-s*math.cos(ang+0.6),b[1]-s*math.sin(ang+0.6))],fill=G)
def knot(name,title,panels):
    im=Image.new("RGB",(W,H),K);d=ImageDraw.Draw(im)
    d.text((8,4),title,fill=G,font=fn(18))
    n=len(panels);pw=W/n
    for i,panel in enumerate(panels):
        label,strands=panel[0],panel[1];props=panel[2] if len(panel)>2 else []
        arrow=panel[3] if len(panel)>3 else False
        x0=i*pw;y0=40;ph=172
        if i: d.line([(x0,40),(x0,270)],fill=G,width=2)
        tf=lambda x,y:(x0+14+x*(pw-28),y0+8+y*(ph-16))
        items=[];k=0
        for si,s_ in enumerate(strands):
            path=[tuple(p) if len(p)>2 else (p[0],p[1],si) for p in s_]
            for lay,pp in _seg_layers(path):
                items.append((lay,k,"rope",[tf(*q) for q in pp]));k+=1
        for lay,kind,geo in props: items.append((lay,k,kind,geo));k+=1
        endpiece=[it for it in items if it[2]=="rope"][-1] if items else None
        items.sort(key=lambda t:(t[0],t[1]))
        for lay,_,kind,geo in items:
            if kind=="rope":
                d.line(geo,fill=K,width=HALO,joint="curve")
                d.line(geo,fill=G,width=ROPE,joint="curve")
            elif kind=="post":
                (ax,ay),(bx,by)=tf(*geo[0]),tf(*geo[1])
                d.rectangle([ax,ay,bx,by],fill=K,outline=G,width=3)
            elif kind=="peg":
                cx,cy=tf(*geo);d.ellipse([cx-11,cy-11,cx+11,cy+11],fill=K,outline=G,width=3)
        if arrow and endpiece:
            g=endpiece[3]; _arrow(d,g[max(0,len(g)-5)],g[-1])
        d.ellipse([x0+4,y0-4,x0+28,y0+20],fill=K,outline=G,width=2)
        d.text((x0+16,y0+8),str(i+1),fill=G,font=fn(15),anchor="mm")
        words=label.split();lines=[""]
        for w in words:
            if len(lines[-1]+" "+w)*7.4>pw-8: lines.append(w)
            else: lines[-1]=(lines[-1]+" "+w).strip()
        for j,l in enumerate(lines[:3]): d.text((x0+5,222+j*15),l,fill=G,font=fn(12))
    im.save(f"content/img/{name}.png")

# simple post / bar helpers
def bar(): return [(0.0,0.3),(1.0,0.3)]
def post(): return [(0.5,0.0),(0.5,1.0)]

knot("knot_square","SQUARE KNOT",[
 ("Right over left, tuck under",[[(0,0.2),(0.5,0.6),(1,0.2)],[(0,0.9),(0.3,0.55),(0.55,0.45),(0.9,0.9)]]),
 ("Left over right, tuck under",[[(0,1),(0.3,0.7),(0.5,0.4),(0.4,0.15),(0.25,0.1)],[(1,1),(0.7,0.7),(0.5,0.4),(0.6,0.15),(0.75,0.1)]]),
 ("Ends lie beside own standing part. Flat.",[[(0,0.3),(0.4,0.3),(0.5,0.5),(0.4,0.7),(0,0.7)],[(1,0.3),(0.6,0.3),(0.5,0.5),(0.6,0.7),(1,0.7)]]),
])
knot("knot_sheet_bend","SHEET BEND",[
 ("Fold thick rope into a U (bight)",[[(1,0.25),(0.3,0.25),(0.15,0.45),(0.3,0.65),(1,0.65)]]),
 ("Thin end up through the U",[[(1,0.25),(0.3,0.25),(0.15,0.45),(0.3,0.65),(1,0.65)],[(0.4,1),(0.4,0.1)]]),
 ("Round behind both legs of U",[[(1,0.25),(0.3,0.25),(0.15,0.45),(0.3,0.65),(1,0.65)],[(0.4,1),(0.4,0.1),(0.6,0.05),(0.75,0.45),(0.55,0.5)]]),
 ("Tuck under itself. Pull tight",[[(1,0.25),(0.3,0.25),(0.15,0.45),(0.3,0.65),(1,0.65)],[(0.4,1),(0.4,0.15),(0.65,0.1),(0.7,0.45),(0.3,0.45),(0.0,0.4)]]),
])
knot("knot_fig8_loop","FIGURE-EIGHT LOOP",[
 ("Fold a long bight",[[(0.35,0),(0.35,0.8),(0.5,0.95),(0.65,0.8),(0.65,0)]]),
 ("Bight round behind both lines",[[(0.35,0),(0.4,0.4),(0.7,0.55),(0.55,0.75),(0.3,0.6),(0.5,0.3),(0.65,0)]]),
 ("Through the first loop: an 8",[[(0.35,0),(0.4,0.35),(0.7,0.5),(0.5,0.65),(0.3,0.5),(0.5,0.35),(0.65,0)],[(0.5,0.55),(0.5,0.75),(0.35,0.95),(0.65,0.95),(0.5,0.75)]]),
 ("Dress: lines side by side. Pull all 4",[[(0.4,0),(0.45,0.3),(0.55,0.45),(0.45,0.6),(0.5,0.7),(0.3,0.95),(0.7,0.95),(0.5,0.7)],[(0.6,0),(0.55,0.3),(0.45,0.45),(0.55,0.6)]]),
])
knot("knot_round_turn","ROUND TURN + TWO HALF HITCHES",[
 ("Two full turns round the post",[post(),[(0,0.25),(0.5,0.3),(0.75,0.35),(0.5,0.4),(0.25,0.4),(0.5,0.45),(0.75,0.5),(0.4,0.6)]]),
 ("Half hitch round standing part",[post(),[(0,0.25),(0.5,0.3),(0.7,0.35)],[(0.7,0.45),(0.4,0.6),(0.2,0.35),(0.1,0.15),(0.25,0.15)]]),
 ("Second half hitch, same way",[post(),[(0,0.25),(0.5,0.3),(0.7,0.35)],[(0.7,0.45),(0.35,0.55),(0.15,0.3),(0.05,0.15),(0.2,0.12),(0.15,0.35),(0.3,0.45)]]),
])
knot("knot_truckers","TRUCKER'S HITCH",[
 ("Make a fixed loop in the line",[[(0,0.2),(0.5,0.2),(0.6,0.1),(0.7,0.2),(0.6,0.3),(0.5,0.2)],[(0.6,0.2),(1,0.2)]]),
 ("End round anchor, up through loop",[[(0,0.2),(0.55,0.2)],[(0.65,0.2),(0.6,0.35),(0.5,0.9)],[(0.4,0.95),(0.45,0.3),(0.62,0.22)]]),
 ("Pull down hard: 2 to 1 pull",[[(0,0.2),(0.55,0.2)],[(0.65,0.2),(0.55,0.9)],[(0.45,0.9),(0.6,0.2),(0.8,0.6)]]),
 ("Lock with two half hitches",[[(0,0.2),(0.55,0.2)],[(0.65,0.2),(0.55,0.9)],[(0.45,0.9),(0.6,0.2),(0.4,0.7),(0.55,0.75),(0.5,0.65)]]),
])
knot("knot_alpine_butterfly","ALPINE BUTTERFLY",[
 ("Wrap rope round your hand twice",[[(0,0.3),(0.5,0.2),(0.7,0.5),(0.3,0.6),(0.5,0.3),(0.75,0.4),(1,0.3)]]),
 ("Pick up the middle wrap",[[(0,0.3),(0.5,0.25),(0.7,0.5),(0.3,0.55),(1,0.35)],[(0.5,0.5),(0.5,0.1)]]),
 ("Fold it over and tuck under all",[[(0,0.3),(0.3,0.5),(0.5,0.6),(0.7,0.5),(1,0.3)],[(0.5,0.55),(0.4,0.9),(0.6,0.9),(0.5,0.55)]]),
])
knot("knot_rolling","ROLLING HITCH",[
 ("Wrap round the pole",[[(0.0,0.5),(1,0.5)],[(0.2,0),(0.4,0.5),(0.3,0.7),(0.2,0.45)]]),
 ("Second wrap crossing the first",[[(0.0,0.5),(1,0.5)],[(0.2,0),(0.4,0.5),(0.3,0.7),(0.45,0.45),(0.55,0.55),(0.5,0.7),(0.45,0.4)]]),
 ("Hitch on the far side. Pull toward wraps",[[(0.0,0.5),(1,0.5)],[(0.2,0),(0.4,0.5),(0.3,0.7),(0.5,0.4),(0.6,0.65),(0.75,0.4),(0.8,0.6),(0.9,0.8)]]),
])
knot("knot_timber","TIMBER HITCH",[
 ("Pass end round the log",[[(0,0.45),(1,0.45)],[(0,0.65),(1,0.65)],[(0.2,0.0),(0.5,0.4),(0.6,0.7),(0.4,0.8)]]),
 ("Round the standing part",[[(0,0.45),(1,0.45)],[(0,0.65),(1,0.65)],[(0.2,0.0),(0.5,0.4),(0.6,0.7),(0.35,0.75),(0.4,0.25)]]),
 ("Twist round itself 3+ times",[[(0,0.45),(1,0.45)],[(0,0.65),(1,0.65)],[(0.2,0.0),(0.5,0.4),(0.6,0.7),(0.4,0.75),(0.5,0.6),(0.42,0.55),(0.52,0.48),(0.44,0.42)]]),
])
knot("knot_double_fisherman","DOUBLE FISHERMAN'S",[
 ("Lay ends side by side, opposite ways",[[(0,0.4),(1,0.4)],[(1,0.6),(0,0.6)]]),
 ("Wrap end A twice round B",[[(0,0.4),(0.4,0.4),(0.45,0.7),(0.5,0.3),(0.55,0.7),(0.6,0.3),(0.55,0.5)],[(1,0.6),(0,0.6)]]),
 ("Tuck A back through wraps",[[(0,0.4),(0.4,0.4),(0.45,0.7),(0.5,0.3),(0.55,0.7),(0.6,0.3),(0.42,0.55),(0.7,0.5)],[(1,0.6),(0,0.6)]]),
 ("Same with B. Pull knots together",[[(0,0.4),(0.45,0.45),(0.48,0.6)],[(1,0.6),(0.55,0.55),(0.52,0.4)]]),
])
knot("knot_water","WATER KNOT (WEBBING)",[
 ("Loose overhand in one strap",[[(0,0.5),(0.5,0.5),(0.6,0.3),(0.7,0.5),(0.55,0.6),(0.45,0.4)]]),
 ("Other strap follows it backward",[[(0,0.5),(0.5,0.5),(0.6,0.3),(0.7,0.5),(0.55,0.6),(0.45,0.4)],[(1,0.55),(0.68,0.55),(0.58,0.35),(0.48,0.48)]]),
 ("Tails 8 cm. Pull all 4 ends",[[(0,0.5),(0.45,0.5),(0.55,0.4),(0.6,0.55),(0.7,0.3)],[(1,0.5),(0.55,0.5),(0.45,0.6),(0.4,0.45),(0.3,0.7)]]),
])
knot("knot_prusik","PRUSIK",[
 ("Cord loop behind the rope",[[(0.5,0),(0.5,1)],[(0.1,0.5),(0.5,0.45),(0.8,0.5)],[(0.1,0.55),(0.5,0.6),(0.8,0.55)]]),
 ("Wrap through own loop",[[(0.5,0),(0.5,1)],[(0.8,0.5),(0.3,0.4),(0.6,0.45),(0.3,0.55),(0.6,0.6),(0.8,0.55)]]),
 ("3 wraps. Neat. Pull loop",[[(0.5,0),(0.5,1)],[(0.35,0.35),(0.65,0.35)],[(0.35,0.45),(0.65,0.45)],[(0.35,0.55),(0.65,0.55)],[(0.5,0.6),(0.5,0.95)]]),
])
knot("knot_sheepshank","SHEEPSHANK",[
 ("Fold slack into an S (Z)",[[(0,0.3),(0.8,0.3),(0.9,0.4),(0.8,0.5),(0.2,0.5),(0.1,0.6),(0.2,0.7),(1,0.7)]]),
 ("Half hitch over each bend",[[(0,0.3),(0.8,0.3),(0.9,0.4),(0.8,0.5),(0.2,0.5),(0.1,0.6),(0.2,0.7),(1,0.7)],[(0.1,0.25),(0.05,0.4),(0.15,0.55)],[(0.95,0.75),(0.97,0.55),(0.85,0.4)]]),
 ("Keep it loaded or it falls apart",[[(0,0.3),(0.8,0.3)],[(0.2,0.5),(0.8,0.5)],[(0.2,0.7),(1,0.7)],[(0.15,0.25),(0.15,0.75)],[(0.85,0.25),(0.85,0.75)]]),
])
# lashings
def poles(*ps): return [list(p) for p in ps]
knot("lash_square","SQUARE LASHING",[
 ("Clove hitch on upright, below cross",[[(0.5,0),(0.5,1)],[(0,0.4),(1,0.4)],[(0.35,0.6),(0.65,0.6)]]),
 ("Wrap over-under-over 3-4 times",[[(0.5,0),(0.5,1)],[(0,0.4),(1,0.4)],[(0.4,0.25),(0.62,0.3),(0.62,0.5),(0.4,0.55),(0.38,0.3)]]),
 ("2-3 frapping turns between poles",[[(0.5,0),(0.5,1)],[(0,0.4),(1,0.4)],[(0.6,0.3),(0.7,0.4),(0.6,0.5),(0.4,0.5),(0.3,0.4),(0.4,0.3),(0.6,0.3)]]),
 ("Finish: clove hitch. Tight",[[(0.5,0),(0.5,1)],[(0,0.4),(1,0.4)],[(0.4,0.3),(0.6,0.5)],[(0.6,0.3),(0.4,0.5)],[(0.3,0.6),(0.5,0.65)]]),
])
knot("lash_diagonal","DIAGONAL LASHING",[
 ("Timber hitch round both poles",[[(0.1,0.1),(0.9,0.9)],[(0.9,0.1),(0.1,0.9)],[(0.35,0.5),(0.5,0.35),(0.65,0.5),(0.5,0.65),(0.4,0.55)]]),
 ("3-4 wraps one diagonal",[[(0.1,0.1),(0.9,0.9)],[(0.9,0.1),(0.1,0.9)],[(0.35,0.35),(0.65,0.65)],[(0.3,0.42),(0.58,0.7)],[(0.42,0.3),(0.7,0.58)]]),
 ("3-4 wraps other diagonal",[[(0.1,0.1),(0.9,0.9)],[(0.9,0.1),(0.1,0.9)],[(0.35,0.35),(0.65,0.65)],[(0.65,0.35),(0.35,0.65)],[(0.7,0.42),(0.42,0.7)]]),
 ("Frap between, clove hitch",[[(0.1,0.1),(0.9,0.9)],[(0.9,0.1),(0.1,0.9)],[(0.5,0.3),(0.7,0.5),(0.5,0.7),(0.3,0.5),(0.5,0.3)]]),
])
knot("lash_tripod","TRIPOD LASHING",[
 ("Lay 3 poles side by side. Clove hitch",[[(0.1,0.3),(0.9,0.3)],[(0.1,0.45),(0.9,0.45)],[(0.1,0.6),(0.9,0.6)],[(0.2,0.2),(0.2,0.7)]]),
 ("Loose wraps over-under, 5-6 times",[[(0.1,0.3),(0.9,0.3)],[(0.1,0.45),(0.9,0.45)],[(0.1,0.6),(0.9,0.6)],[(0.25,0.2),(0.3,0.7)],[(0.32,0.2),(0.37,0.7)],[(0.39,0.2),(0.44,0.7)]]),
 ("Frap between poles. Clove hitch",[[(0.1,0.3),(0.9,0.3)],[(0.1,0.45),(0.9,0.45)],[(0.1,0.6),(0.9,0.6)],[(0.25,0.25),(0.45,0.4),(0.25,0.5)],[(0.25,0.4),(0.45,0.55),(0.25,0.65)]]),
 ("Spread legs, cross middle pole",[[(0.5,0.1),(0.15,0.95)],[(0.5,0.1),(0.85,0.95)],[(0.45,0.1),(0.55,0.95)]]),
])


def _sc(path,sx=1.0,yf=None):
    out=[]
    for p in path:
        x=min(1.0,max(0.0,0.5+(p[0]-0.5)*sx));y=yf(p[1]) if yf else p[1]
        out.append((x,y)+tuple(p[2:]))
    return out
_bly=lambda y: y*1.45 if y<0.62 else 0.9+(y-0.62)*0.27
# --- Main knots, drawn with explicit over/under layers (higher layer = on top) ---
_BIG=[(0.5,0,0),(0.5,0.3,0),(0.5,0.46,1),(0.72,0.40,1),(0.64,0.22,1),(0.42,0.26,1),(0.32,0.5,1),(0.28,0.85,1),(0.5,0.98,1),(0.72,0.85,1),(0.64,0.62,1)]
knot("knot_bowline","BOWLINE",[
 ("Small loop: the down side on top",[_sc([(0.5,0,0),(0.5,0.3,0),(0.5,0.46,1),(0.72,0.40,1),(0.64,0.22,1),(0.42,0.26,1),(0.32,0.5,1),(0.3,0.9,1)],1.8,_bly)],[],False),
 ("End up through the loop from below",[_sc(_BIG+[(0.6,0.43,-1),(0.58,0.32,1),(0.58,0.22,1)],1.8,_bly)],[],True),
 ("Go round behind the standing part",[_sc(_BIG+[(0.6,0.43,-1),(0.58,0.32,1),(0.6,0.12,1),(0.5,0.06,-1),(0.38,0.1,-1),(0.36,0.17,1)],1.8,_bly)],[],True),
 ("Back down through the loop. Pull",[_sc(_BIG+[(0.6,0.43,-1),(0.58,0.32,1),(0.6,0.12,1),(0.5,0.06,-1),(0.38,0.1,-1),(0.38,0.2,2),(0.46,0.36,2),(0.5,0.44,-1),(0.52,0.58,1),(0.52,0.66,1)],1.8,_bly)],[],True),
])
_POST=[(1,"post",[(0.43,0.0),(0.57,1.0)])]
_C1=[(0,0.15,2),(0.4,0.24,2),(0.62,0.33,2),(0.7,0.38,0),(0.5,0.47,0),(0.36,0.52,2)]
_C2=_C1+[(0.33,0.58,2),(0.5,0.52,3),(0.62,0.42,3),(0.66,0.3,3),(0.7,0.26,0),(0.5,0.3,0),(0.32,0.4,0)]
knot("knot_clove","CLOVE HITCH",[
 ("Wrap once round the post",[_sc(_C1+[(0.22,0.62,2)],1.4)],_POST,True),
 ("Cross over the first wrap, round again",[_sc(_C2+[(0.26,0.46,2)],1.4)],_POST,True),
 ("Tuck the end under the cross. Pull",[_sc(_C2+[(0.36,0.44,2.5),(0.6,0.46,2.5),(0.8,0.47,2.5),(1.0,0.48,2.5)],1.4)],_POST,True),
])
_PEG=[(3,"peg",(0.5,0.93))]
_UP=[(0.38,0.0,1),(0.38,0.6,1),(0.36,0.82,1),(0.42,0.97,0),(0.6,0.97,0),(0.68,0.85,1),(0.74,0.6,1),(0.72,0.36,1)]
_W=_UP+[(0.6,0.30,2),(0.46,0.33,2),(0.3,0.38,0),(0.46,0.45,0),(0.6,0.42,2),(0.46,0.47,2),(0.3,0.52,0),(0.46,0.58,0)]
knot("knot_taut_line","TAUT-LINE HITCH",[
 ("Round the stake, end up beside the line",[_sc(_UP,1.5)],_PEG,True),
 ("Two turns round the line, inside the loop",[_sc(_W+[(0.56,0.62,1)],1.5)],_PEG,True),
 ("Cross up, one turn outside, tuck. Slide",[_sc(_W+[(0.56,0.6,3),(0.58,0.4,3),(0.54,0.2,3),(0.46,0.14,3),(0.3,0.16,0),(0.46,0.22,0),(0.56,0.17,2.5),(0.7,0.1,2.5),(0.85,0.06,2.5)],1.5)],_PEG,True),
])
