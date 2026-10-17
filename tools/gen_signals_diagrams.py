"""Draw the Signals & Radio diagrams (480x284, #1AFF80 on black).

Run from the repo root: python3 tools/gen_signals_diagrams.py
Writes content/img/signals-*.png.
"""
import os
from PIL import Image, ImageDraw, ImageFont
G=(0x1A,0xFF,0x80);W,H=480,284
def F(s):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"]:
        try: return ImageFont.truetype(p,s)
        except: pass
    return ImageFont.load_default()
def new(t):
    im=Image.new("RGB",(W,H),(0,0,0));d=ImageDraw.Draw(im);d.text((W//2,16),t,fill=G,font=F(20),anchor="mm");return im,d
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","content","img")
def save(im,n): im.save(os.path.join(OUT,f"signals-{n}.png"))
# SOS
im,d=new("SOS = ... --- ...  (no gaps)")
y=110
x=(W-(36*6+76*3-16))//2
for s in "...---...":
    if s==".": d.ellipse((x,y-10,x+20,y+10),fill=G);x+=36
    else: d.rectangle((x,y-10,x+60,y+10),fill=G);x+=76
d.text((W//2,170),"short x3   long x3   short x3",fill=G,font=F(18),anchor="mm")
d.text((W//2,215),"Pause, then repeat. Whistle, torch, tap.",fill=G,font=F(16),anchor="mm")
d.text((W//2,250),"Rule of 3: any signal x3 = HELP",fill=G,font=F(16),anchor="mm");save(im,"sos")
# ground-air
im,d=new("Ground-to-air (big: 3m+, 6m better)")
fs=F(13);cells=[("V","Need","help"),("X","Need","medical"),("N","No",""),("Y","Yes",""),("->","Going","this way")]
for i,(s,l1,l2) in enumerate(cells):
    cx=50+i*95;cy=110
    if s=="V": d.line((cx-22,cy-30,cx,cy+30,cx+22,cy-30),fill=G,width=8)
    elif s=="X": d.line((cx-22,cy-30,cx+22,cy+30),fill=G,width=8);d.line((cx+22,cy-30,cx-22,cy+30),fill=G,width=8)
    elif s=="N": d.line((cx-20,cy+30,cx-20,cy-30,cx+20,cy+30,cx+20,cy-30),fill=G,width=8)
    elif s=="Y": d.line((cx-22,cy-30,cx,cy),fill=G,width=8);d.line((cx+22,cy-30,cx,cy),fill=G,width=8);d.line((cx,cy,cx,cy+30),fill=G,width=8)
    else: d.line((cx-30,cy,cx+14,cy),fill=G,width=8);d.polygon([(cx+32,cy),(cx+12,cy-16),(cx+12,cy+16)],fill=G)
    d.text((cx,cy+55),l1,fill=G,font=fs,anchor="mm")
    if l2: d.text((cx,cy+72),l2,fill=G,font=fs,anchor="mm")
d.text((W//2,240),"High contrast, open ground, straight lines",fill=G,font=F(16),anchor="mm");save(im,"ground-air")
# mirror
im,d=new("Signal mirror: aim with V of fingers")
d.ellipse((20,60,80,120),outline=G,width=4);d.text((50,90),"SUN",fill=G,font=F(14),anchor="mm")
d.rectangle((150,140,190,190),outline=G,width=4);d.text((170,210),"mirror",fill=G,font=F(14),anchor="mm")
d.line((80,100,165,150),fill=G,width=3)
d.line((300,140,320,100),fill=G,width=6);d.line((340,140,320,100),fill=G,width=6)
d.text((320,160),"V fingers",fill=G,font=F(14),anchor="mm")
d.line((190,150,440,80),fill=G,width=3);d.polygon([(450,76),(430,74),(436,92)],fill=G)
d.text((430,60),"target",fill=G,font=F(14),anchor="mm")
d.text((W//2,250),"Flash spot onto fingers, then on target",fill=G,font=F(16),anchor="mm");save(im,"mirror")
# morse table
im,d=new("Morse code   . short   - long")
M=dict(A=".-",B="-...",C="-.-.",D="-..",E=".",F="..-.",G="--.",H="....",I="..",J=".---",K="-.-",L=".-..",M="--",N="-.",O="---",P=".--.",Q="--.-",R=".-.",S="...",T="-",U="..-",V="...-",W=".--",X="-..-",Y="-.--",Z="--..")
M.update({"1":".----","2":"..---","3":"...--","4":"....-","5":".....","6":"-....","7":"--...","8":"---..","9":"----.","0":"-----"})
fm=F(15);ks=list(M)
for i,k in enumerate(ks):
    c=i//9;r=i%9;d.text((10+c*120,40+r*26),f"{k} {M[k]}",fill=G,font=fm)
save(im,"morse")
# fire triangle
im,d=new("3 fires in a triangle = distress")
pts=[(240,70),(130,220),(350,220)]
d.polygon(pts,outline=G,width=3)
for x,y in pts:
    d.polygon([(x,y-28),(x-16,y+10),(x+16,y+10)],fill=G)
d.text((W//2,258),"About 25m apart. Day: smoke. Night: flame.",fill=G,font=F(16),anchor="mm");save(im,"fire")
# whistle/torch
im,d=new("Whistle / torch code")
rows=[("Help (SOS)","short x3, long x3, short x3"),("Mountain distress","6 blasts/flashes in a minute, wait 1 min"),("Reply","3 in a minute"),("Rule of three","any 3 = distress")]
for i,(a,b) in enumerate(rows):
    d.text((20,60+i*50),a,fill=G,font=F(18));d.text((20,84+i*50),b,fill=G,font=F(15))
save(im,"whistle")
# phonetic + mayday
im,d=new("MAYDAY call (VHF Ch16)")
L=["MAYDAY MAYDAY MAYDAY","This is <name> x3","MAYDAY <name>, position","Nature of distress","Help needed, persons aboard","Other info.  OVER"]
for i,l in enumerate(L): d.text((20,48+i*36),f"{i+1}. {l}",fill=G,font=F(18))
save(im,"mayday")
