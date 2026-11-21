"""Search local two-layer routes with rounded copper distances and explicit endpoints."""
from dataclasses import dataclass
import heapq
import math

import numpy as np
import pcbnew as pcb

import route

SURFACES = (pcb.F_Cu,pcb.B_Cu)
STEP = .05


@dataclass(frozen=True)
class Terminal:
    point: tuple
    layers: tuple
    bounds: tuple|None = None

    @classmethod
    def pad(cls,item):
        return cls(route.pos(item),tuple(i for i,s in enumerate(SURFACES) if item.IsOnLayer(s)),
                   route.box(item))


class Grid:
    def __init__(self,board,limits):
        left, top, right, bottom=limits
        self.x=np.arange(left,right+STEP/2,STEP)
        self.y=np.arange(top,bottom+STEP/2,STEP)
        self.board=board
        self.parts=[]
        for footprint in board.GetFootprints():
            for pad in footprint.Pads():
                layers=tuple(i for i,s in enumerate(SURFACES) if pad.IsOnLayer(s))
                if layers:
                    self.parts.append((pad.GetNetname(),layers,"pad",route.box(pad),0))
        for area in board.Zones():
            if area.GetIsRuleArea() and area.GetDoNotAllowTracks():
                self.parts.append(("",(0,1),"keepout",route.box(area),0))
        for item in board.GetTracks():
            if isinstance(item,pcb.PCB_VIA):
                r=pcb.ToMM(item.GetWidth(pcb.F_Cu))/2
                self.parts.append((item.GetNetname(),(0,1),"via",route.pos(item),r))
            elif item.GetLayer() in SURFACES:
                coords=tuple((pcb.ToMM(a.x),pcb.ToMM(a.y)) for a in (item.GetStart(),item.GetEnd()))
                self.parts.append((item.GetNetname(),(SURFACES.index(item.GetLayer()),),"track",coords,
                                   pcb.ToMM(item.GetWidth())/2))

    def measure(self,kind,data,margin):
        if kind in ("pad","keepout"):
            a,b,c,d=data
        else:
            (a,b),(c,d)=(data,data) if kind=="via" else data
            a,c=min(a,c),max(a,c)
            b,d=min(b,d),max(b,d)
        i=max(0,int(math.ceil((a-margin-self.x[0])/STEP)))
        k=min(len(self.x),1+int(math.floor((c+margin-self.x[0])/STEP)))
        j=max(0,int(math.ceil((b-margin-self.y[0])/STEP)))
        l=min(len(self.y),1+int(math.floor((d+margin-self.y[0])/STEP)))
        if k<=i or l<=j:
            return None
        x,y=self.x[i:k][None,:],self.y[j:l][:,None]
        if kind in ("pad","keepout"):
            dx=np.maximum(np.maximum(a-x,x-c),0.)
            dy=np.maximum(np.maximum(b-y,y-d),0.)
            hit=dx*dx+dy*dy<margin**2
        else:
            (sx,sy),(tx,ty)=(data,data) if kind=="via" else data
            u,v=tx-sx,ty-sy
            if u or v:
                t=np.clip(((x-sx)*u+(y-sy)*v)/(u*u+v*v),0,1)
                dx=x-sx-t*u
                dy=y-sy-t*v
            else:
                dx,dy=x-sx,y-sy
            hit=dx*dx+dy*dy<margin**2
        return slice(j,l),slice(i,k),hit

    def masks(self,net,width):
        shape=(2,len(self.y),len(self.x))
        blocked=np.zeros(shape,dtype=np.bool_)
        vblocked=blocked.copy()
        for other,layers,kind,coords,radius in self.parts:
            if other==net:
                candidates=((vblocked,.44),) if kind in ("pad","via") else ()
            else:
                gap=max(route.gap(net),route.gap(other),.30 if kind=="keepout" else 0)
                candidates=((blocked,radius+width/2+gap+.009),(vblocked,radius+.30+gap+.018))
            for grid,margin in candidates:
                cover=self.measure(kind,coords,margin)
                if cover is not None:
                    y,x,hit=cover
                    for side in layers:
                        grid[side,y,x]|=hit
        for mask,margin in ((blocked,.3+width/2+.019),(vblocked,.62)):
            mask[:,:,self.x<50+margin]=True
            mask[:,:,self.x>180-margin]=True
            mask[:,self.y<50+margin,:]=True
            mask[:,self.y>130-margin,:]=True
        return blocked.tolist(),(vblocked[0]|vblocked[1]).tolist()

    def access(self,terminal,blocked):
        x,y=terminal.point
        lo,hi=x-.12,x+.12
        up,down=y-.12,y+.12
        if terminal.bounds:
            a,b,c,d=terminal.bounds
            lo,hi=max(a+.04,x-.55),min(c-.04,x+.55)
            up,down=max(b+.04,y-.55),min(d-.04,y+.55)
        xs=np.flatnonzero((self.x>=lo)&(self.x<=hi))
        ys=np.flatnonzero((self.y>=up)&(self.y<=down))
        return [(int(i),int(j),s) for i in xs for j in ys for s in terminal.layers if not blocked[s][j][i]]

    def trace(self,net,width,source,target,limit=700000,via_ok=True):
        occupancy,via_mask=self.masks(net,width)
        starts=self.access(source,occupancy)
        targets=set(self.access(target,occupancy))
        if not starts or not targets:
            return ()
        xlow=min(p[0] for p in targets)
        xhigh=max(p[0] for p in targets)
        ylow=min(p[1] for p in targets)
        yhigh=max(p[1] for p in targets)
        def estimate(node):
            x,y,_=node
            dx=max(xlow-x,x-xhigh,0)
            dy=max(ylow-y,y-yhigh,0)
            return 10*max(dx,dy)+4*min(dx,dy)
        costs={point:0 for point in starts}
        parent={}
        queue=[(estimate(node),0,node) for node in starts]
        heapq.heapify(queue)
        nx,ny=len(self.x),len(self.y)
        iterations=0
        while queue and iterations<limit:
            _,travel,current=heapq.heappop(queue)
            if costs[current]!=travel:
                continue
            if current in targets:
                path=[current]
                while path[-1] in parent:
                    path.append(parent[path[-1]])
                return self.compact(path[::-1],source,target)
            iterations+=1
            x,y,s=current
            def advance(nx_,ny_,ns,delta):
                if occupancy[ns][ny_][nx_]:
                    return
                nxt=(nx_,ny_,ns)
                if travel+delta>=costs.get(nxt,10**9):
                    return
                costs[nxt]=travel+delta
                parent[nxt]=current
                heapq.heappush(queue,(travel+delta+estimate(nxt),travel+delta,nxt))
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                a,b=x+dx,y+dy
                if 0<=a<nx and 0<=b<ny and not occupancy[s][y][a] and not occupancy[s][b][x]:
                    advance(a,b,s,14 if dx and dy else 10)
            if via_ok and not via_mask[y][x]:
                advance(x,y,1-s,210)
        return ()

    def compact(self,path,source,target):
        def delta(first,last):
            return tuple(b-a for a,b in zip(first,last))
        middle=[path[0]]
        for a,b,c in zip(path,path[1:],path[2:]):
            if delta(a,b)!=delta(b,c):
                middle.append(b)
        if path[-1]!=path[0]:
            middle.append(path[-1])
        out=[(float(round(self.x[x],5)),float(round(self.y[y],5)),s) for x,y,s in middle]
        return [(*source.point,out[0][2]),*out,(*target.point,out[-1][2])]
