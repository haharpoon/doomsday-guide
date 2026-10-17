from PIL import Image, ImageDraw, ImageFont
G=(0x1A,0xFF,0x80); W,H=480,284
F="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def new(title):
    im=Image.new("RGB",(W,H),(0,0,0)); d=ImageDraw.Draw(im)
    d.text((8,4),title,fill=G,font=ImageFont.truetype(F,18)); return im,d
def t(d,xy,s,sz=13): d.text(xy,s,fill=G,font=ImageFont.truetype(F,sz))
def L(d,pts,w=4): d.line(pts,fill=G,width=w,joint="curve")
def C(d,c,r,w=4): d.ellipse([c[0]-r,c[1]-r,c[0]+r,c[1]+r],outline=G,width=w)
def arrow(d,a,b,w=3):
    L(d,[a,b],w); import math
    ang=math.atan2(b[1]-a[1],b[0]-a[0])
    for s in (2.6,-2.6): L(d,[b,(b[0]+12*math.cos(ang+s),b[1]+12*math.sin(ang+s))],w)

# CPR hands
im,d=new("CPR: HAND POSITION")
C(d,(70,140),28); L(d,[(98,140),(400,140)]); L(d,[(98,190),(400,190)])  # body side view
L(d,[(98,140),(98,190)])
d.rectangle([180,138,260,150],outline=G,width=3); t(d,(190,152),"breastbone",11)
arrow(d,(220,60),(220,132)); t(d,(232,64),"push straight down")
t(d,(232,82),"5-6 cm adult")
t(d,(232,100),"100-120 per min")
t(d,(10,215),"1 Heel of hand on centre of chest")
t(d,(10,233),"2 Other hand on top, fingers locked")
t(d,(10,251),"3 Arms straight, shoulders over hands")
im.save("content/img/cpr_hands.png")

# Recovery position
im,d=new("RECOVERY POSITION")
C(d,(80,120),22)  # head
L(d,[(100,130),(260,130)]) # back/body
L(d,[(100,150),(240,150)])
L(d,[(260,130),(380,140)]); L(d,[(240,150),(320,150),(330,200)])  # legs: top leg bent
L(d,[(380,140),(380,155)])
L(d,[(110,150),(90,175),(70,160)]) # top hand under cheek
t(d,(30,170),"hand under",11); t(d,(30,183),"cheek",11)
L(d,[(140,150),(170,190)]); t(d,(150,195),"arm out",11)
t(d,(300,205),"top knee bent",11)
arrow(d,(40,120),(20,95),2); t(d,(10,60),"tilt head back",11)
t(d,(10,225),"1 Near arm out at right angle  2 Far hand to cheek")
t(d,(10,243),"3 Bend far knee, pull to roll onto side")
t(d,(10,261),"4 Head tilted, airway open; check breathing")
im.save("content/img/recovery_position.png")

# Tourniquet
im,d=new("TOURNIQUET PLACEMENT")
L(d,[(60,90),(400,90)]); L(d,[(60,150),(400,150)])  # limb
L(d,[(400,90),(430,120),(400,150)])
t(d,(20,108),"body",12)
d.rectangle([180,82,215,158],outline=G,width=4); t(d,(160,58),"TOURNIQUET")
C(d,(320,120),12); t(d,(290,160),"WOUND")
arrow(d,(300,190),(230,190)); t(d,(240,198),"5-8 cm",12)
L(d,[(197,82),(197,40)],3); L(d,[(170,40),(225,40)],5); t(d,(232,32),"windlass: twist",12)
t(d,(10,220),"1 Place ABOVE wound (body side), not on a joint")
t(d,(10,238),"2 Tighten until bleeding STOPS")
t(d,(10,256),"3 Write TIME on skin. Do not loosen.")
im.save("content/img/tourniquet.png")

# Arm sling
im,d=new("ARM SLING (TRIANGLE BANDAGE)")
C(d,(150,60),22)
L(d,[(110,95),(190,95)]); L(d,[(110,95),(110,230)]); L(d,[(190,95),(190,230)])
L(d,[(190,110),(225,170),(130,165)])  # injured arm across chest
d.polygon([(118,145),(240,145),(130,205)],outline=G,width=4)  # sling
L(d,[(118,145),(160,85)],3); L(d,[(130,205),(140,85)],3)
t(d,(150,82),"knot",11)
t(d,(250,60),"1 Support arm across")
t(d,(250,78),"   chest, hand higher")
t(d,(250,96),"   than elbow")
t(d,(250,120),"2 Slide cloth under")
t(d,(250,138),"   arm, point to elbow")
t(d,(250,162),"3 Tie ends at neck,")
t(d,(250,180),"   hollow above collarbone")
t(d,(250,204),"4 Pin elbow point;")
t(d,(250,222),"   check fingers warm")
im.save("content/img/arm_sling.png")

# Leg splint
im,d=new("SPLINTING A LOWER LEG")
L(d,[(40,130),(420,130)],6); L(d,[(40,160),(420,160)],6)  # leg
t(d,(50,140),"knee",11); t(d,(380,140),"ankle",11)
L(d,[(200,128),(215,162)],3); t(d,(195,95),"break",12)
d.rectangle([30,110,440,120],outline=G,width=3); d.rectangle([30,170,440,180],outline=G,width=3)
t(d,(445,104),"rigid",10); t(d,(445,168),"rigid",10)
for x in (70,150,280,380): L(d,[(x,104),(x,186)],5)
t(d,(10,200),"1 Splints reach past the joint ABOVE and BELOW")
t(d,(10,218),"2 Pad gaps with cloth. Tie, knots on splint side")
t(d,(10,236),"3 No ties over the break. Firm, not tight")
t(d,(10,254),"4 Check toes: warm, pink, can feel = OK")
im.save("content/img/leg_splint.png")

# Cordage reverse wrap
im,d=new("CORDAGE: REVERSE WRAP")
for i in range(6):
    x=60+i*55
    L(d,[(x,90),(x+40,140)],5); L(d,[(x+40,140),(x+55,90)] ,3) if False else None
for i in range(6):
    x=60+i*55
    L(d,[(x+10,140),(x+50,90)],5)
L(d,[(30,115),(60,115)],3); t(d,(10,70),"loop",12)
t(d,(10,165),"1 Fold fibre bundle off-centre, pinch at bend")
t(d,(10,183),"2 Twist the FAR strand away from you")
t(d,(10,201),"3 Wrap it TOWARD you over the other strand")
t(d,(10,219),"4 Repeat: twist away, wrap toward")
t(d,(10,237),"5 Splice new fibre in before a strand ends")
t(d,(10,255),"Strands lock together and will not unravel")
im.save("content/img/cordage.png")

# Knapping
im,d=new("KNAPPING: PERCUSSION FLAKING")
d.polygon([(60,170),(200,110),(260,150),(120,210)],outline=G,width=4)
t(d,(90,215),"core (flint)",12)
L(d,[(200,110),(200,95)],3); t(d,(150,72),"edge / platform",12)
C(d,(270,60),22); t(d,(300,50),"hammerstone",12)
arrow(d,(255,75),(208,108)); 
t(d,(285,95),"strike near edge,",12); t(d,(285,111),"angle under 90 deg",12)
d.polygon([(215,135),(250,150),(225,175)],outline=G,width=3); t(d,(260,160),"flake comes off",12)
t(d,(10,238),"1 Eye protection + leather pad on leg")
t(d,(10,256),"2 Glancing blow, follow through. Sharp!")
im.save("content/img/knapping.png")

# Fish trap funnel
im,d=new("FUNNEL FISH TRAP")
d.ellipse([60,90,120,200],outline=G,width=4)
L(d,[(90,90),(360,110)]); L(d,[(90,200),(360,180)])
d.ellipse([340,110,380,180],outline=G,width=4)
L(d,[(90,90),(170,135)],3); L(d,[(90,200),(170,155)],3)
t(d,(140,140),"narrow",11)
for x in (160,230,300): L(d,[(x,98),(x,192)],2)
arrow(d,(20,145),(80,145)); t(d,(5,110),"fish in",12)
t(d,(390,135),"closed",12); t(d,(390,150),"end",12)
t(d,(10,218),"1 Weave sticks into a tube, close one end")
t(d,(10,236),"2 Inward funnel at mouth: easy in, hard out")
t(d,(10,254),"3 Bait inside, mouth faces downstream")
im.save("content/img/fish_trap.png")

# Gill net
im,d=new("GILL NET SET")
L(d,[(30,80),(450,80)],2); t(d,(10,50),"water surface",12)
L(d,[(60,60),(60,250)],5); L(d,[(420,60),(420,250)],5)
L(d,[(60,95),(420,95)],4); L(d,[(60,215),(420,215)],4)
for x in range(60,421,30): L(d,[(x,95),(x,215)],2)
for y in range(95,216,30): L(d,[(60,y),(420,y)],2)
for x in range(90,420,90): C(d,(x,95),7,3)
t(d,(150,100),"",11)
t(d,(430,90),"float",11); t(d,(430,205),"weight",11)
t(d,(90,225),"stake",11)
t(d,(70,255),"Set across slow water at an angle. Check often.",12)
im.save("content/img/gill_net.png")

# Knife sharpening
im,d=new("SHARPENING A KNIFE")
d.rectangle([60,180,420,210],outline=G,width=4); t(d,(200,213),"wet stone",12)
L(d,[(120,178),(330,140)],5); L(d,[(330,140),(400,120)],9)
t(d,(405,95),"handle",11)
L(d,[(120,178),(200,178)],2); t(d,(150,155),"~20 deg",12)
arrow(d,(250,120),(140,120)); t(d,(150,90),"push edge-first",12)
t(d,(10,235),"1 Same angle every stroke. 10 strokes per side")
t(d,(10,253),"2 Coarse side, then fine. Strop on leather/wood")
im.save("content/img/sharpening.png")
