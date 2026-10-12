"""Explosionszeichnung der Baugruppe mit Teilenamen.

Aufruf: python explosion.py bild.png gieren neigen   (z. B. -30 -22 = von links vorn, 150 -22 = von rechts)
Teile und Lage aus baugruppe.py (mp5_umbau/ muss erzeugt sein), Platine per kicad-cli.
"""
import os, sys, tempfile
import numpy as np
import trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import baugruppe as B  # noqa: E402

d = {}
for name, src, mat, _ in B.parts():
    if name.startswith("Steg vorn"):
        m = B.steg_vorn()
    elif name.startswith("Steg hinten"):
        m = B.bar(B.P.STEG_L, B.X_REAR_BAR, B.P.STOP[3])
    else:
        m = B.load(src if os.path.isabs(src) else os.path.join(B.SRC, src + ".stl"))
        m.apply_transform(mat)
    d[name] = (m.vertices, m.faces)
with tempfile.TemporaryDirectory() as tmp:
    bs, g = B.board(tmp)
    pcb = []
    for node in bs.graph.nodes_geometry:
        t, gn = bs.graph[node]
        geo = bs.geometry[gn].copy(); geo.apply_transform(g @ t); pcb.append(geo)
    pb = trimesh.util.concatenate(pcb); d["Platine"] = (pb.vertices, pb.faces)
th=np.radians(12.0); ag=np.array([-np.cos(th),np.sin(th),0])   # Magazinachse (oben)
# Versatz im Gun-Rahmen (X unten, Y hinten, Z links)
OFF={
 'Gehäuse links':(0,0,100),'Gehäuse rechts':(0,0,-75),'Platine':(0,0,-38),
 'Abzug':(75,0,45),'Zwischenring':(0,-40,0),'Steg vorn (Rundstab 96 mm)':(-55,-30,0),
 'Handschutz hinten':(0,-70,0),'Handschutz vorn mit Schalldämpfer links':(25,-150,60),
 'Handschutz vorn mit Schalldämpfer rechts':(-30,-150,-60),
 'Spannhebel Stift':(-25,-100,75),'Spannhebel Knauf':(-25,-100,100),
 'Korn':(-50,-150,0),'TSOP-Einsatz':(-65,-195,0),'Linsenhülse':(0,-225,0),'Frontkappe':(0,-255,0),
 'Schaft links':(0,80,45),'Schaft rechts':(0,80,-50),'OLED-Rahmen':(-35,100,0),
 'Steg hinten (Rundstab 77 mm)':(-60,40,0),
 'Magazin':tuple(-ag*90),'Magazin Unterteil':tuple(-ag*150),
}
COL={'Gehäuse':(0.58,0.6,0.63),'Platine':(0.15,0.55,0.25),'Steg':(0.78,0.78,0.8),'Stift':(0.78,0.78,0.8),
     'Magazin Unterteil':(0.25,0.45,0.6),'Abzug':(0.75,0.2,0.2),'Linsenhülse':(0.85,0.62,0.2),'OLED':(0.2,0.3,0.55),'TSOP':(0.55,0.2,0.6)}
def color(n):
    for k,c in COL.items():
        if k in n: return c
    return (0.3,0.31,0.33)
yaw,pitch=np.radians(float(sys.argv[2])),np.radians(float(sys.argv[3]))
def xf(v):
    u=v[...,1]; w=-v[...,0]; dd=v[...,2]
    u,dd=u*np.cos(yaw)+dd*np.sin(yaw),-u*np.sin(yaw)+dd*np.cos(yaw)
    w,dd=w*np.cos(pitch)+dd*np.sin(pitch),-w*np.sin(pitch)+dd*np.cos(pitch)
    return np.stack([u,w,dd],-1)
items=[]
for n,(v,f) in d.items():
    t=v[f]+np.array(OFF.get(n,(0,0,0)))
    items.append((n,xf(t),color(n)))
allp=np.concatenate([t.reshape(-1,3) for _,t,_ in items])
res=0.3; pad=60
u0,w0=allp[:,0].min()-pad,allp[:,1].min()-pad; u1,w1=allp[:,0].max()+pad,allp[:,1].max()+pad
nx,ny=int((u1-u0)/res)+2,int((w1-w0)/res)+2
Z=np.full((ny,nx),-1e9); C=np.ones((ny,nx,3)); Lt=np.array([-0.4,0.6,0.7]); Lt/=np.linalg.norm(Lt)
for n,T,c in items:
    nn=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]); nn/=np.linalg.norm(nn,axis=1,keepdims=True)+1e-12
    k=np.clip(0.35+0.65*np.abs(nn@Lt),0,1)
    for tr,kk in zip(T,k):
        A,B,Cc=tr
        x0=max(int((min(A[0],B[0],Cc[0])-u0)/res),0); x1=min(int((max(A[0],B[0],Cc[0])-u0)/res)+1,nx-1)
        y0=max(int((min(A[1],B[1],Cc[1])-w0)/res),0); y1=min(int((max(A[1],B[1],Cc[1])-w0)/res)+1,ny-1)
        if x1<x0 or y1<y0: continue
        xs=u0+np.arange(x0,x1+1)*res; ys=w0+np.arange(y0,y1+1)*res; X,Y=np.meshgrid(xs,ys)
        den=(B[1]-Cc[1])*(A[0]-Cc[0])+(Cc[0]-B[0])*(A[1]-Cc[1])
        if abs(den)<1e-12: continue
        l1=((B[1]-Cc[1])*(X-Cc[0])+(Cc[0]-B[0])*(Y-Cc[1]))/den; l2=((Cc[1]-A[1])*(X-Cc[0])+(A[0]-Cc[0])*(Y-Cc[1]))/den; l3=1-l1-l2
        mm=(l1>=-1e-6)&(l2>=-1e-6)&(l3>=-1e-6)
        if not mm.any(): continue
        D=l1*A[2]+l2*B[2]+l3*Cc[2]; zb=Z[y0:y1+1,x0:x1+1]; up=mm&(D>zb); zb[up]=D[up]; C[y0:y1+1,x0:x1+1][up]=np.array(c)*kk
fig=plt.figure(figsize=(nx/100,ny/100),dpi=100); ax=plt.axes([0,0,1,1]); ax.imshow(C,origin='lower',extent=[u0,u1,w0,w1]); ax.axis('off')
# Beschriftung: Anker = sichtbarer Schwerpunkt, Text nach außen versetzt
cen=np.array([(u0+u1)/2,(w0+w1)/2])
placed=[]
for n,T,c in items:
    p=T.reshape(-1,3)[:,:2].mean(0)
    dirv=p-cen; dirv=dirv/ (np.linalg.norm(dirv)+1e-9)
    q=p+dirv*35
    for _ in range(30):
        if all(np.hypot(*(q-r))>22 for r in placed): break
        q=q+np.array([0,-9])
    placed.append(q)
    ax.annotate(n,xy=p,xytext=q,fontsize=15,ha='center',va='center',
                arrowprops=dict(arrowstyle='-',color='0.25',lw=0.9),bbox=dict(boxstyle='round,pad=0.25',fc='white',ec='0.6',lw=0.6))
ax.set_xlim(u0,u1); ax.set_ylim(w0,w1)
plt.savefig(sys.argv[1],dpi=100)
