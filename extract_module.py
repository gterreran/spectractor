import numpy as np
from scipy.optimize import curve_fit
from numpy.polynomial import legendre
from scipy.interpolate import LSQUnivariateSpline

import io
import base64
import matplotlib.pyplot as plt
plt.switch_backend('Agg')

def gauss(x, a,x0,sigma):
#    if a<0:
#        a=-a
    return a*np.exp(-((x-x0)**2)/(2*sigma**2))

def spline(x,_xdata,_ydata,nodes):
    return LSQUnivariateSpline(_xdata, _ydata, nodes, k=1)(x)

def open_trace(_file):
    with open(_file) as inp:
        for line in inp:
            d=line.strip('\n').split(',')
            trace.append([float(el) for el in d])
    return trace
    

def find_trace(_sections,_data,auto=0):
    _data=np.array(_data)
    trace=[]
    
    for sec in _sections:
        xx,yy=sec
        
        cen=yy[0]
        for i in range(len(xx)):
            if not auto:
                cen=yy[i]
            col=np.array(_data[:,xx[i]])
            pix= np.arange(len(col))
            
            for iter in [0,1]:
                success=0
                bg=np.where(((pix>cen-25)&(pix<cen-15))|((pix>cen+15)&(pix<cen+25)))
                
                tr=np.where((pix>cen-15)&(pix<cen+15))
                p=np.polyfit(pix[bg],col[bg],1)
                res=col[tr]-np.polyval(p,pix[tr])
                std=np.std(col[bg])

            
                try:
                    popt,pcov=curve_fit(gauss,pix[tr],res,p0=[100,cen,5])
                    
                    if popt[0]>0 and np.fabs(cen-popt[1])<5 and np.fabs(popt[2])<8 and np.fabs(popt[2])>1:# and popt[0]>3*std:
                        cen=popt[1]
                        success=1
                except:
                    pass
            
            if success:
                trace.append([xx[i],popt[1],np.fabs(popt[2])])
           
    trace=sorted(trace)
    x,c,s=zip(*trace)

    return list(x),list(c),list(s)



#By default the uses pickle to cache, which is not able to handle lambda object.
#For this reason I inserted 'import dill as pickle' in
#/anaconda3/lib/python3.7/site-packages/flask_caching/backends/filesystemcache.py
#/anaconda3/lib/python3.7/site-packages/flask_caching/backends/simplecache.py
#/anaconda3/lib/python3.7/site-packages/flask_caching/backends/memcache.py
#/anaconda3/lib/python3.7/site-packages/flask_caching/backends/rediscache.py
#/anaconda3/lib/python3.7/site-packages/flask_caching/contrib/uwsgicache.py
#/anaconda3/lib/python3.7/site-packages/dash_extensions/enrich.py
class func_base():
    def __init__(self,_fitter,_eval,_ord):
        self.fitter=lambda x,y: _fitter(x,y,int(_ord))
        self.eval=lambda x,opt: _eval(x,opt)
        
def func(_lab,_ord):
    if _lab=='Che':
        return func_base(legendre.legfit,legendre.legval,_ord)
    if _lab=='Leg':
        return func_base(legendre.legfit,legendre.legval,_ord)
    if _lab=='Sp1':
        return func_base(legendre.legfit,legendre.legval,_ord)
    if _lab=='Sp3':
        return func_base(legendre.legfit,legendre.legval,_ord)
    
class xcs:
    def __init__(self,x,c,s):
        self.x=x
        self.c=c
        self.s=s

class dTrace:
    def __init__(self):
        self.trace={}
        self.all=xcs([],[],[])
        self.good=xcs([],[],[])
        self.bad=xcs([],[],[])
        self.func=xcs(None,None,None)
        self.opt=xcs(None,None,None)
        self.visible=True
        self.status=self.get_status()
        self.spectrum=[]
    
    def get_status(self):
        if len(self.all.x)==0:
            return 'drawn'
        elif len(self.good.x)==0:
            return 'identified'
        elif len(self.spectrum)==0:
            return 'fitted'
        else:
            return 'extracted'

    
def fit_trace(_positions,_func_cen_lab,_order_cen,_func_sig_lab,_order_sig):
        

    good_x,good_c,good_s=_positions

    bad_x=[]
    bad_c=[]
    bad_s=[]

    func_cen=func(_func_cen_lab,_order_cen)
    func_sig=func(_func_sig_lab,_order_sig)

    fit_leg_c=func_cen.fitter(good_x,good_c)
    res_fit_leg_c=[]
    for j in range(len(good_x)):
        res_fit_leg_c.append((func_cen.eval(good_x[j],fit_leg_c)-good_c[j])**2)

    fit_leg_std_c=np.sqrt(np.sum(res_fit_leg_c)/len(res_fit_leg_c))


    fit_leg_s=func_sig.fitter(good_x,good_s)
    res_fit_leg_s=[]
    for j in range(len(good_x)):
        res_fit_leg_s.append((func_sig.eval(good_x[j],fit_leg_s)-good_s[j])**2)

    #fit_leg_s=np.polyfit(good_x,good_s,2)
    #res_fit_leg_s=[]
    #for j in range(len(good_x)):
    #    res_fit_leg_s.append((np.polyval(fit_leg_s,good_x[j])-good_s[j])**2)

    fit_leg_std_s=np.sqrt(np.sum(res_fit_leg_s)/len(res_fit_leg_s))


    #iter=0


    while 1:
        #ax1.cla()
        #ax2.cla()
        interaction=0
        for i in range(len(good_x))[::-1]:
            if np.fabs(good_c[i]-func_cen.eval(good_x[i],fit_leg_c))>fit_leg_std_c*3:
                interaction=1
                bad_x.append(good_x.pop(i))
                bad_c.append(good_c.pop(i))
                bad_s.append(good_s.pop(i))
                continue
        for i in range(len(good_x))[::-1]:
            if np.fabs(good_s[i]-func_sig.eval(good_x[i],fit_leg_s))>fit_leg_std_s*3:
            #if np.fabs(good_s[i]-np.polyval(fit_leg_s,good_x[i]))>fit_leg_std_s*3:
                interaction=1
                bad_x.append(good_x.pop(i))
                bad_c.append(good_c.pop(i))
                bad_s.append(good_s.pop(i))
                continue
        if interaction:
            fit_leg_c=func_cen.fitter(good_x,good_c)
            res_fit_leg_c=[]
            for j in range(len(good_x)):
                res_fit_leg_c.append((func_cen.eval(good_x[j],fit_leg_c)-good_c[j])**2)

            fit_leg_std_c=np.sqrt(np.sum(res_fit_leg_c)/len(good_x))

            fit_leg_s=func_sig.fitter(good_x,good_s)
            res_fit_leg_s=[]
            for j in range(len(good_x)):
                res_fit_leg_s.append((func_sig.eval(good_x[j],fit_leg_s)-good_s[j])**2)

    #        fit_leg_s=np.polyfit(good_x,good_s,2)
    #        res_fit_leg_s=[]
    #        for j in range(len(good_x)):
    #            res_fit_leg_s.append((np.polyval(fit_leg_s,good_x[j])-good_s[j])**2)

            fit_leg_std_s=np.sqrt(np.sum(res_fit_leg_s)/len(good_x))


        else:
            break

 
    return [np.array(good_x).tolist(), np.array(good_c).tolist(), np.array(good_s).tolist(), np.array(bad_x).tolist(), np.array(bad_c).tolist(), np.array(bad_s).tolist(), fit_leg_c.tolist(),fit_leg_s.tolist()]



def extract_trace(_data,_trace_store):
    d=np.array(_data)
    
    pix=np.arange(1,len(d[0])+1)
    
    spectrum=[]
    
    for c in _trace_store.all.x:
        col=np.array(d[:,c])
        cen=_trace_store.func.c.eval(c+1,_trace_store.opt.c)
        sigma=_trace_store.func.s.eval(c+1,_trace_store.opt.s)

        bg=np.where(((pix>cen-4.5*sigma)&(pix<cen-2.5*sigma))|((pix>cen+2.5*sigma)&(pix<cen+4.5*sigma)))

        tr=np.where((pix>cen-25)&(pix<cen+25))


        p=np.polyfit(pix[bg],col[bg],1)
        res=col[tr]-np.polyval(p,pix[tr])
        popt,pcov=curve_fit(lambda x,a,cc:gauss(x,a,cc,sigma),pix[tr],res,p0=[200,cen])

        spectrum.append(popt[0]*sigma*np.sqrt(2*np.pi))

    return spectrum


def guess_trace_position(_col):
    xx=np.arange(1,len(_col)+1)
    mid_col=_col[int(len(_col)/2)]
    mid_xx=xx[int(len(_col)/2)]
    
    popt,pcov=curve_fit(lambda x,a,cen,sigma,c:gauss(x,a,cen,sigma)+c,xx,_col,p0=[mid_col,mid_xx,5,np.mean(_col)])
    
    return popt[1]

#get all the pixels touched by a line connecting 2 points.
def get_points(_x,_y):
    
    #if the segment is longer on the x direction, sample the pixels along the x
    if np.fabs(_x[1]-_x[0])>=np.fabs(_y[1]-_y[0]):
    
        #using linspace for better control on the endpoint
        xx=np.linspace(_x[0],_x[1],int(np.fabs(_x[1]-_x[0]))+1,dtype=int)
        m=(_y[1]-_y[0])/(_x[1]-_x[0])
        q=_y[0]-m*_x[0]
        return  xx.tolist(),[round(el) for el in (m*xx+q).tolist()]
    
    #if the segment is longer on the y direction, sample the pixels along the y
    else:
        xx=np.linspace(_y[0],_y[1],int(np.fabs(_y[1]-_y[0]))+1,dtype=int)
        
        #exception for vertical line, which would have m->inf
        if _x[1]==_x[0]:
            return [_x[0]]*len(xx),xx.tolist()
            
        else:
            m=(_x[1]-_x[0])/(_y[1]-_y[0])
            q=_x[0]-m*_y[0]
            return  [round(el) for el in (m*xx+q).tolist()],xx.tolist()

def interpret_svg(_svg_string):
    points=[]
    ss=_svg_string[1:].split('L')
    for i in range(1,len(ss)):
        a0,b0=ss[i-1].split(',')
        a1,b1=ss[i].split(',')
            
        points.append([[round(float(a0)),round(float(a1))],[round(float(b0)),round(float(b1))]])

    return points

def get_points_from_path(_path):
    path_points=interpret_svg(_path)
    
    first_seg_x_length=np.fabs(path_points[0][0][1]-path_points[0][0][0])
    first_seg_y_length=np.fabs(path_points[0][1][1]-path_points[0][1][0])
    
    if first_seg_x_length>=first_seg_y_length:
        orientation='horizontal'
    else:
        orientation='vertical'

    
    xx,yy=[],[]
    for i,p in enumerate(path_points):
        pp=get_points(*p)
        #get_points parametrize the segment differently depending on the main direction of each segment. More horizontal sigments will follow the x pixels, while more vertical onse will follow the y pixels. So if a path swithes between the 2 orientations, the parametrizations would be messed up. So the xx will be reseted to just the index of each point along the path.
        
        seg_x_length=np.fabs(p[0][1]-p[0][0])
        seg_y_length=np.fabs(p[1][1]-p[1][0])
        if seg_x_length>=seg_y_length and orientation=='vertical':
            orientation='mixed'
        elif seg_y_length>seg_x_length and orientation=='horizontal':
            orientation='mixed'
        
        
        #pp includes both endpoints. To avoid duplicates at segment conjunctions, I don't take the first pixel of segments beyond the first.
        if i==0:
            xx=xx+pp[0]
            yy=yy+pp[1]
        else:
            xx=xx+pp[0][1:]
            yy=yy+pp[1][1:]

    return xx,yy,orientation

def points_to_svg(_xdata,_ydata):
    #N is the number of nodes. 50 is an indicative number. It should end up using 3 to 8 nodes max in normal circumstances
    for N in range(50):
        if N==0:
            popt=[]
        else:
            #linspace includes the extremities, so to get 1 node position i need 3 points and exclude the first and the last
            nodes=np.linspace(_xdata[0],_xdata[-1],N+2)[1:-1]

            try:
                popt,pcov=curve_fit(lambda x, *n: spline(x, _xdata, _ydata, n),_xdata,_ydata,p0=[nodes])
            except ValueError: #just in case the configuration is particularly messy
                continue
            
        svg='M{},{}L'.format(_xdata[0],_ydata[0])
        for p in popt:
            svg = svg + '{},{}L'.format(p,spline(p, _xdata, _ydata, popt))
        svg = svg + '{},{}'.format(_xdata[-1],_ydata[-1])
        
        ss=spline(_xdata, _xdata, _ydata, popt)
        
        res=0.
        for i in range(len(_xdata)):
            res=res+(_ydata[i]-ss[i])**2
        
        res=np.sqrt(res/len(_xdata))
        if N>0:
            #if adding a node improved the rapresentation by less then 5%, then we assume to have reached a nice rapresentation.
            if (prev_res-res)/prev_res<0.05:
                break
        prev_res=res
        
    return svg
            
                
def create_children(obj,type):
    out={}
    out['props']={'children':obj}
    out['type']=type
    out['namespace']='dash_html_components'
    
    return out



def get_trace_style(_i,_s):
    
    return '<img src="assets/style_{}_{}.png" alt="delete trace" width="40">'.format(str(_i),_s)
    
#    fig=plt.figure()
#    fig.set_size_inches(0.55, 0.2)
#    ax=fig.add_subplot()
#
#    ax.plot([0.,0.5], [0.5,0.5], color=get_color(_i),lw=3,ls='--',dashes=[4,1])
#
#    ax.set_frame_on(False)
#    ax.set_xticks([])
#    ax.set_yticks([])
#
#    s = io.BytesIO()
#
#    fig.savefig(s, format='png', bbox_inches="tight")
#    plt.close()
#    s = base64.b64encode(s.getvalue()).decode("utf-8").replace("\n", "")
#    return f'<img src="data:image/png;base64, {s}">'

def get_color(_i):
    colors=['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52']
    
    return colors[_i]


def shift_path(_path,_pix):
    
    out_ss='M'
    
    ss= _path[1:].split('L')
    for p in ss:
        x,y=p.split(',')
        out_ss=out_ss + '{},{}L'.format(x,float(y)+_pix)
    
    #removing the extra L we put in the string
    return out_ss[:-1]
