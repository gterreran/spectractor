#!/usr/bin/env python

#next line are for debugging. It helps figuring out at what line the script is.
import inspect #import currentframe

import logging

import astropy.io.fits as pf
from astropy.visualization import ZScaleInterval,MinMaxInterval
import numpy as np
import extract_module as em
import dash,json,sys,os,base64,io,glob


import layout,initials

from dash.exceptions import PreventUpdate
from dash import no_update, callback_context

from dash_extensions.enrich import Dash,Trigger,ServersideOutput, FileSystemStore, Input, Output, State


def debug():
    '''
    This is just for debuggin purposes. It prints the function in which it is called,
    and the line at which it is called.
    '''
    
    print('{} fired. Line {}.'.format(inspect.stack()[1][3],inspect.stack()[1][2]))



def check_folder_for_traces():
    '''
    As per function name. Search files ending with trace.csv
    '''
    
    options=[]
    for f in glob.glob('*trace.csv'):
        options.append({'label': f, 'value': f})
    return options



def get_path(_pp):
    '''
    From a dictionary representing a dash figure, it returns the SVG path.
    If the original shape was a line, it converts it into a path
    '''

    #free hand path
    if _pp['type']=='path':
        return _pp['path']
        
    #straigh line
    else:
        x0=_pp['x0']
        y0=_pp['y0']
        x1=_pp['x1']
        y1=_pp['y1']
        return 'M{},{}L{},{}'.format(x0,y0,x1,y1)



def as_path(_path, _opacity=1, _color='red', _width=4, _dash='dash'):
    '''
    It takes an SVG path and returns the the full dash shape.
    '''
    p={'editable': True,
       'xref': 'x',
       'yref': 'y',
       'layer': 'above',
       'opacity': _opacity,
       'line': {'color': _color, 'width': _width, 'dash': _dash},
       'type': 'path',
       'path': _path,
       'clickmode':'event+select',
       'hovermode':'closest'
    }
    
    return p


#############################################################################################
'''
NOTES ABOUT DASH AND PLOTLY

The difference between Input and State, is that State doesn't trigger the callback.

It is not possible to have multiple ServersideOutput pointing to the same object.
However, with dash_extensions you can have normal Outputs pointing to the same object.
You don't even need to pack it and unpack it as a json. I'm not sure if the package
does the conversion under the hood, possibly not as it seems relatively fast.
A workaround to the ServersideOutput would be to create several proxy variable in the form of
'Stores' to store the same quantity coming from different callbacks.

Trigger is very useful. Fires a callback without actually using the variable that fired it.
'''

cache_dir="./cache"

output_defaults=dict(backend=FileSystemStore(cache_dir=cache_dir), session_check=True)

#dash seems to login several times. I found this workaround on the internet
log = logging.getLogger(__name__)
app = Dash(__name__, output_defaults=output_defaults, assets_folder='assets')

# remove last handler. The one added by dash
log.handlers.pop()

app.layout = layout.layout



#upload image and storing the data.
@app.callback(
    ServersideOutput("2d-data",'data'),
    #---------------------
    Output("zmin",'disabled'),
    Output("zmax",'disabled'),
    Output("zslider",'disabled'),
    Output("new-trace",'n_clicks'),
    #---------------------
    Input("load-2d",'contents'),
    Input("load-2d",'filename'),
)
def upload_image(_contents, _filename):
    '''
    'load-2d' is an 'Upload' object. The easiest way to treat it, would be to take
    the 'filename' component and pass it to pyfits. However, the 'filename' component
    does not retain the path, so it would work only for file in the same directory
    as this script. So I actually parse the 'contents' component, which is an encoded
    64bit variable. So I decode it and, just then pass it to pyfits.
    '''

    debug()
    d={}
    #Here I inizialize all the ServersideOutputs
    if _contents is None:
        d['data']=np.zeros(shape=(1000,3000))
        d['Y_DIM']=len(d['data'])
        d['X_DIM']=len(d['data'][0])
        d['no_trigger']=1
        
        return d,True,True,True,no_update
    
    #If a proper image is loaded, I also activate the zscale nozles.
    else:
        content_type, content_string = _contents.split(',')
        fits = base64.b64decode(content_string)
        d['data']=pf.getdata(io.BytesIO(fits))
        d['header']=pf.getheader(io.BytesIO(fits))
        d['filename']=_filename
        d['Y_DIM']=len(d['data'])
        d['X_DIM']=len(d['data'][0])
        d['no_trigger']=0
    
    
        return d,False,False,False,1


#upload arc
@app.callback(
    ServersideOutput("2d-data-arc",'data'),
    #---------------------
    Input("load-2d-arc",'contents'),
    Input("load-2d-arc",'filename'),
    #---------------------
    prevent_initial_call=True
)
def upload_image(_contents, _filename):
    debug()
    d={}
    
    content_type, content_string = _contents.split(',')
    fits = base64.b64decode(content_string)
    d['data']=pf.getdata(io.BytesIO(fits))
    d['header']=pf.getheader(io.BytesIO(fits))
    d['filename']=_filename
    
    
    return d
    

#here I handle the contrast nozles.
@app.callback(
    Output("2d-scales",'data'),
    Output("zslider",'value'),
    Output("zslider",'min'),
    Output("zslider",'max'),
    Output("zmin",'value'),
    Output("zmax",'value'),
    #---------------------
    Input("2d-data",'data'),
    Input("zslider",'value'),
    Input("zmin",'value'),
    Input("zmax",'value'),
    #---------------------
    State("2d-scales",'data'),
    #---------------------
    prevent_initial_call=True
)
def update_scale_2d_and_slider(_2d_data, _zslider, _zmin, _zmax, _zlims_json):

    if _2d_data['no_trigger']==1:
        raise PreventUpdate
        
    debug()
    
    ctx = callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == "2d-data":
        z={}
        z['zsmin'],z['zsmax'] = [int(el) for el in ZScaleInterval().get_limits(_2d_data['data'])]
        z['mmmin'],z['mmmax'] = [int(el) for el in MinMaxInterval().get_limits(_2d_data['data'])]
    else:
        z=json.loads(_zlims_json)
    
        if trigger_id == "zmin" or trigger_id == "zmax":
            z['zsmin'],z['zsmax']=int(_zmin),int(_zmax)
        else:
            z['zsmin'],z['zsmax']=[int(el) for el in _zslider]
    
    return json.dumps(z),[z['zsmin'],z['zsmax']],z['mmmin'],z['mmmax'],z['zsmin'],z['zsmax']


#figure handling
@app.callback(
    Output("2d",'figure'),
    #---------------------
    Input("2d-scales",'data'),
    Input("2d-data",'data'),
    Input("drawing-style", 'value'),
    Input("trace_table",'data'),
    #---------------------
    State("n_trace",'data'),
    State("2d",'figure'),
    State("trace_action",'data'),
    State("deleted_traces",'data'),
    #---------------------
    prevent_initial_call=True
)
def main_figure_update(_zlims_json, _2d_data, _drawing_style, _trace_table, _n_trace, _fig, _trace_action, _deleted_traces):

    if _2d_data['no_trigger']==1:
        raise PreventUpdate

    debug()
    
    ctx = callback_context
    #multiple triggers can occure here, so it's better to check if the trigger is present in a list instead to check that it's the first
    trigger_list = [el['prop_id'].split('.')[0] for el in ctx.triggered]

    _fig['layout']['newshape'] = {'line':{'color':em.get_color(_n_trace),'dash':'dash'}}

    
    if "drawing-style" in trigger_list:
        _fig['layout']['dragmode']=_drawing_style
    

    if "trace_table" in trigger_list:
        if _trace_action == 'new_trace':
            pass
            
        elif _trace_action == 'draw':
            _fig['layout']['shapes'][-1]['shape_id'] = _trace_table[_n_trace]['trace_paths'][-1]['shape_id']
            
        elif _trace_action == 'edit':
            for tr in _trace_table[_n_trace]['trace_paths']:
                for sh in range(len(_fig['layout']['shapes'])):
                    if _fig['layout']['shapes'][sh]['shape_id'] == tr['shape_id']:
                        _fig['layout']['shapes'][sh]=tr
                        
        elif _trace_action == 'copy':
            for tr in _trace_table[-1]['trace_paths']:
                _fig['layout']['shapes'].append(tr)

        elif _trace_action == 'delete':
            for tr in _deleted_traces[-1]['trace_paths']:
                for sh in range(len(_fig['layout']['shapes'])):
                    if _fig['layout']['shapes'][sh]['shape_id'] == tr['shape_id']:
                        del _fig['layout']['shapes'][sh]
                        break
        
        elif _trace_action == 'expand':
            for tr in _trace_table[_n_trace]['trace_paths']:
                for sh in range(len(_fig['layout']['shapes'])):
                    if _fig['layout']['shapes'][sh]['shape_id'] == tr['shape_id']:
                        del _fig['layout']['shapes'][sh]
                        break
            
            _fig['layout']['shapes'].append(_trace_table[_n_trace]['trace_paths'][-1])
            

    
    if "2d-data" in trigger_list:
        _fig['data'][0]['z']=_2d_data['data']
        _fig['layout']['shapes']=[]
        
    if "2d-scales" in trigger_list:
        z=json.loads(_zlims_json)
        _fig['layout']['coloraxis']['cmin']=z['zsmin']
        _fig['layout']['coloraxis']['cmax']=z['zsmax']
    
    return _fig

#zoomin and position
@app.callback(
    Output("x", 'children'),
    Output("y", 'children'),
    Output("z", 'children'),
    Output("zoomin", 'figure'),
    #---------------------
    Input("2d", 'hoverData'),
    #---------------------
    State("2d-data",'data'),
    State("zoomin",'figure'),
    #---------------------
    prevent_initial_call=True
)
def display_hover_data(_hoverData, _2d_data, _zoom_fig):
    #debug()
    
    if _hoverData is not None:
        #gather positon of mouse.
        h_x=_hoverData['points'][0]['x']
        h_y=_hoverData['points'][0]['y']
        h_z=_hoverData['points'][0]['z']
        
        #checking if mouse goes close to the edge
        low_y=max([h_y-25,0])
        low_x=max([h_x-25,0])
        up_y=min([h_y+25,_2d_data['Y_DIM']])
        up_x=min([h_x+25,_2d_data['X_DIM']])

        zoomed_d=_2d_data['data'][low_y:up_y,low_x:up_x]
        
        #if zoom range is outside edge, padd array with zeros at the correct end of the array
        if low_y==0:
            zoomed_d=np.pad(zoomed_d,((50-len(zoomed_d),0),(0,0)),'constant',constant_values=0)
        if low_x==0:
            zoomed_d=np.pad(zoomed_d,((0,0),(50-len(zoomed_d[0]),0)),'constant',constant_values=0)
        if up_y==_2d_data['Y_DIM']:
            zoomed_d=np.pad(zoomed_d,((0,50-len(zoomed_d)),(0,0)),'constant',constant_values=0)
        if up_x==_2d_data['X_DIM']:
            zoomed_d=np.pad(zoomed_d,((0,0),(0,50-len(zoomed_d[0]))),'constant',constant_values=0)
        
        _zoom_fig['data'][0]['z']=zoomed_d
        return str(h_x),str(h_y),str(h_z),_zoom_fig
        
    else:
        _zoom_fig['data'][0]['z']=np.zeros(shape=(50,50))
        return '0','0','0',_zoom_fig

#click and drag projection
@app.callback(
    Output("cut",'figure'),
    Output("trace_table", 'data'),
    Output("shape_idx",'data'),
    Output("trace_action",'data'),
    #---------------------
    Input("2d",'relayoutData'),
    #---------------------
    State("2d",'figure'),
    State("2d-data",'data'),
    State("trace_table",'data'),
    State("cut",'figure'),
    State("n_trace",'data'),
    State("shape_idx",'data'),
    #---------------------
    prevent_initial_call=True
)
def drawing_and_storing_as_path(_2d_relayoutData, _2d_fig, _2d_data, _table_data, _cut_fig, _n_trace, _shape_idx):
    #there is an autoshape relayoutData event that triggers, so we need extra precautions to avoid this callback to fire only when we want to.
    if _2d_relayoutData is None:
        raise PreventUpdate
    if not any(['shapes' in key for key in _2d_relayoutData]):
        raise PreventUpdate
        
    debug()
    
    #triggered by drawing a new segment
    if 'shapes' in _2d_relayoutData:
    
        _shape_idx=_shape_idx+1
    
        #both straigh line and paths are handled as SVG paths.
        path=get_path(_2d_relayoutData['shapes'][-1])
        
        _table_data[_n_trace]['trace_paths'].append(as_path(path,_color=em.get_color(_n_trace)))
        _table_data[_n_trace]['trace_paths'][-1]['shape_id']=_shape_idx
    

        _table_data[_n_trace]['status']='drawn'

    #if 'shapes' is not in _2d_relayoutData and the code reached this point, then it means that the user moved something
    else:
        
        key0=next(iter(_2d_relayoutData))
        shape_index=int(key0[key0.find('[')+1:key0.find(']')])
        
        print(shape_index)
        
        #free hand path
        if key0.split('.')[1]=='path':
            path=_2d_relayoutData[key0]
         
        #straight line
        else:
            x0=_2d_relayoutData['shapes[{}].x0'.format(shape_index)]
            y0=_2d_relayoutData['shapes[{}].y0'.format(shape_index)]
            x1=_2d_relayoutData['shapes[{}].x1'.format(shape_index)]
            y1=_2d_relayoutData['shapes[{}].y1'.format(shape_index)]
            path='M{},{}L{},{}'.format(x0,y0,x1,y1)
    
        #the index of _table_data refers to the trace, not the actual shape in the figure. So the scripts needs to find which is the one to actually edit.
        for t in range(len(_table_data)):
            for i in range(len(_table_data[t]['trace_paths'])):
                if _table_data[t]['trace_paths'][i]['shape_id'] == shape_index:
                    _table_data[t]['trace_paths'][i]['path'] = as_path(path,_color=em.get_color(t))['path']
        
        
    xx,yy,orientation=em.get_points_from_path(path)
    #numpy black magic ravel_multi_index([list_x_coord,list_y_coord],shape original array)
    indexes=np.ravel_multi_index([yy,xx], (_2d_data['Y_DIM'],_2d_data['X_DIM']))
    zz=_2d_data['data'].take(indexes)

    _cut_fig['data'][0]['y']=zz
    
    if orientation=='horizontal':
        _cut_fig['data'][0]['x']=xx
    elif orientation=='vertical':
        _cut_fig['data'][0]['x']=yy
    else:
        _cut_fig['data'][0]['x']=list(range(len(zz)))
    
    return _cut_fig,_table_data,_shape_idx, 'draw'

    
@app.callback(
    Output("load_csv", 'options'),
    #---------------------
    Input("dropdown-parent", 'n_clicks'),
    #---------------------
    prevent_initial_call=True
)
def update_options(_n_clicks):
    debug()
    if _n_clicks is None:
        raise dash.exceptions.PreventUpdate
    return check_folder_for_traces()


@app.callback(
    Output("find-trace",'disabled'),
    #---------------------
    Input("auto-find",'on'),
    Input("trace_table",'data'),
    #---------------------
    State("n_trace",'data'),
    #---------------------
    prevent_initial_call=True
)
def auto_find_trace_selected(_auto,_trace_table, _n_trace):
    if _auto or len(_trace_table[_n_trace]['trace_paths'])!=0:
        return False
    else:
        return True
    
    debug()



@app.callback(
    Output("extract-trace",'disabled'),
    Output("expand-trace",'disabled'),
    #---------------------
    Input("trace-store",'data'),
    Input("n_trace",'data'),
    #---------------------
    prevent_initial_call=True
)
def activate_extract_button(_trace_fit, _n_trace):
    try:
        _trace_fit[_n_trace]
    except:
        return True,True
    debug()
    
    if len(_trace_fit[_n_trace].good.x)!=0:
        return False,False
    else:
        return True,True



@app.callback(
    Output("refit_trace_button",'disabled'),
    #---------------------
    Trigger("trace_func",'value'),
    Trigger("sigma_func",'value'),
    Trigger("trace_func_order",'value'),
    Trigger("sigma_func_order",'value'),
    #---------------------
    Input("trace-store",'data'),
    #---------------------
    State("refit_trace_button",'disabled'),
    State("n_trace",'data'),
    #---------------------
    prevent_initial_call=True
)
def activate_refit_button(_trace_fit_store, _status, _n_trace):
    
    #this prevents to try to refit when there are no data
    if len(_trace_fit_store[_n_trace].all.x) == 0:
        raise PreventUpdate
    else:
        return False

@app.callback(
    ServersideOutput("store_from_find_trace",'data'),
    Output("trace_table", 'data'),
    Output("shape_idx",'data'),
    Output("trace_action",'data'),
    #---------------------
    Trigger("find-trace",'n_clicks'),
    Trigger("expand-trace",'n_clicks'),
    #---------------------
    State("2d-data",'data'),
    State("auto-find",'on'),
    State("trace_table",'data'),
    State("n_trace",'data'),
    State("shape_idx",'data'),
    #---------------------
    prevent_initial_call=True
)
def find_trace(_2d_data, _auto, _trace_table, _n_trace, _shape_idx):
    debug()
    
    ctx = callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == "find-trace":
        if _auto:
            X_DIM=_2d_data['X_DIM']
        
            #it will start from the midpoint and first search on the right and then go back from the middle and search on the left

            right_data=list(range(int(X_DIM/2)+1,X_DIM))
            left_data=list(range(int(X_DIM/2),-1,-1))
            
            cen_0=em.guess_trace_position(np.array(_2d_data['data'])[:,int(X_DIM/2)])
            
            
            selection=[[right_data,[cen_0]*len(right_data)],[left_data,[cen_0]*len(left_data)]]
            
            xx,yy,ss,pop,bg=em.find_trace(selection, _2d_data['data'], auto=_auto)
            
            _shape_idx=_shape_idx+1
            
            path=em.points_to_svg(xx,yy)
            
            _trace_table[_n_trace]['trace_paths'].append(as_path(path,_color=em.get_color(_n_trace)))
            _trace_table[_n_trace]['trace_paths'][-1]['shape_id']=_shape_idx
        
            _trace_table[_n_trace]['status']='found'
            
            
            return [xx,yy,ss,pop,bg], _trace_table, _shape_idx, 'copy'
            
        else:
            selection=[]
            for el in _trace_table[_n_trace]['trace_paths']:
                xx,yy,orientation=em.get_points_from_path(el['path'])
                selection.append([xx,yy])
        
            xx,yy,ss,pop,bg=em.find_trace(selection, _2d_data['data'], auto=_auto)
            
            return [xx,yy,ss,pop,bg], no_update, no_update, no_update
    
    else:
        X_DIM=_2d_data['X_DIM']

        selection=[]
        for el in _trace_table[_n_trace]['trace_paths']:
            xx,yy,orientation=em.get_points_from_path(el['path'])
            selection.append([xx,yy])
        
        left_data = list(range(selection[0][0][0],-1,-1))
        selection_left = [[left_data,[selection[0][1][0]]*len(left_data)]]
        
        xx_l,yy_l,ss_l,pop_l,bg_l = em.find_trace(selection_left, _2d_data['data'], auto=1)
        xx,yy,ss,pop,bg=em.find_trace([selection[0]], _2d_data['data'], auto=0)
        
        xx,yy,ss,pop,bg = [x+y for x,y in zip([xx_l,yy_l,ss_l,pop_l,bg_l], [xx,yy,ss,pop,bg])]
        
        for s in range(1,len(selection)):
            mid_data = list(range(selection[s-1][0][-1],selection[s][0][0]))
            selection_mid = [[mid_data,[selection[s-1][1][0]]*len(mid_data)]]
            xx_m,yy_m,ss_m,pop_m,bg_m = em.find_trace(selection_mid, _2d_data['data'], auto=1)
            
            xx_s,yy_s,ss_s,pop_s,bg_s=em.find_trace([selection[s]], _2d_data['data'], auto=0)
            
            xx,yy,ss,pop,bg = [x+y+z for x,y,z in zip([xx,yy,ss,pop,bg], [xx_m,yy_m,ss_m,pop_m,bg_m], [xx_s,yy_s,ss_s,pop_s,bg_s])]
            

        right_data = list(range(selection[-1][0][-1],X_DIM))
        selection_right = [[right_data,[selection[-1][1][-1]]*len(right_data)]]
        
        xx_r,yy_r,ss_r,pop_r,bg_r=em.find_trace(selection_right, _2d_data['data'], auto=1)

        xx,yy,ss,pop,bg = [x+y for x,y in zip([xx,yy,ss,pop,bg], [xx_r,yy_r,ss_r,pop_r,bg_r])]

        _shape_idx=_shape_idx+1
            
        path=em.points_to_svg(xx,yy)
        
        _trace_table[_n_trace]['trace_paths'].append(as_path(path,_color=em.get_color(_n_trace)))
        _trace_table[_n_trace]['trace_paths'][-1]['shape_id']=_shape_idx
    
        _trace_table[_n_trace]['status']='found'
        
        return [xx,yy,ss,pop,bg], _trace_table, _shape_idx, 'expand'
    
    
    
@app.callback(
    ServersideOutput("store_from_fit_trace",'data'),
    #---------------------
    Trigger("refit_trace_button",'n_clicks'),
    #---------------------
    Input("store_from_find_trace",'data'),
    #---------------------
    State("trace_func",'value'),
    State("trace_func_order",'value'),
    State("sigma_func",'value'),
    State("sigma_func_order",'value'),
    #---------------------
    prevent_initial_call=True
)
def fit_trace(_positions, _func_cen_lab, _order_cen, _func_sig_lab, _order_sig):
    debug()
    
    tt=em.fit_trace(_positions, _func_cen_lab,_order_cen,_func_sig_lab,_order_sig)
    func_c = em.func(_func_cen_lab,_order_cen)
    func_s = em.func(_func_sig_lab,_order_sig)
    
    return tt+[func_c,func_s]

    
@app.callback(
    ServersideOutput("trace-store",'data'),
    #---------------------
    Input("store_from_fit_trace",'data'),
    #---------------------
    State("store_from_find_trace",'data'),
    State("trace-store",'data'),
    State("n_trace",'data'),
    #---------------------
    prevent_initial_call=True
)
def update_trace_store_and_table(_fit, _find, _trace_data, _n_trace):
    debug()
    
    if _trace_data is None:
        _trace_data=[]
        
    for i in range(_n_trace+1):
        try:
            _trace_data[i]
        except:
            _trace_data.append(em.dTrace())
    
    xx,cc,ss,pop,bg=_find
    _trace_data[_n_trace].all.x = xx
    _trace_data[_n_trace].all.c = cc
    _trace_data[_n_trace].all.s = ss


    _trace_data[_n_trace].good.x = _fit[0]
    _trace_data[_n_trace].good.c = _fit[1]
    _trace_data[_n_trace].good.s = _fit[2]
    _trace_data[_n_trace].bad.x = _fit[3]
    _trace_data[_n_trace].bad.c = _fit[4]
    _trace_data[_n_trace].bad.s = _fit[5]
    _trace_data[_n_trace].opt.c = _fit[6]
    _trace_data[_n_trace].opt.s = _fit[7]
    _trace_data[_n_trace].func.c = _fit[8]
    _trace_data[_n_trace].func.s = _fit[9]


    return _trace_data


#trace and sigma figures handler
@app.callback(
    Output("trace_tracker",'figure'),
    Output("sigma_tracker",'figure'),
    #---------------------
    Input("trace-store",'data'),
    Input("n_trace",'data'),
    #---------------------
    State("trace_tracker",'figure'),
    State("sigma_tracker",'figure'),
    #---------------------
    prevent_initial_call=True
)
def trace_and_sigma_figures(_trace_fit, _n_trace, _fig_trace, _fig_sigma):
    try:
        _trace_fit[_n_trace]
    except:
        return initials.tracetracker, initials.sigmatracker
        
    debug()

    if len(_trace_fit[_n_trace].all.x)==0:
        raise PreventUpdate

    if _fig_trace['data'][0]['x'] != _trace_fit[_n_trace].all.x:
    
        _fig_trace['data'][0]['x']=_trace_fit[_n_trace].all.x
        _fig_trace['data'][0]['y']=_trace_fit[_n_trace].all.c

        _fig_sigma['data'][0]['x']=_trace_fit[_n_trace].all.x
        _fig_sigma['data'][0]['y']=_trace_fit[_n_trace].all.s

    if _trace_fit[_n_trace].opt.c is not None:
        _fig_trace['data'][0]['visible']=False
        _fig_trace['data'][0]['visible']=False
    
        xx=_trace_fit[_n_trace].all.x

        c_fit=_trace_fit[_n_trace].func.c.eval(xx,_trace_fit[_n_trace].opt.c)
        s_fit=_trace_fit[_n_trace].func.s.eval(xx,_trace_fit[_n_trace].opt.s)
        
        if len(_fig_trace['data'])==1:
            _fig_trace['data'].append({
                'hovertemplate': 'x=%{x}<br>y=%{y}<extra></extra>',
                'legendgroup': '',
                'marker': {'color': '#636efa', 'symbol': 'circle'},
                'mode': 'markers',
                'name': '',
                'orientation': 'v',
                'showlegend': False,
                'type': 'scatter'
            })
            _fig_trace['data'].append({
                'hovertemplate': 'x=%{x}<br>y=%{y}<extra></extra>',
                'legendgroup': '',
                'marker': {'color': 'red', 'symbol': 'circle'},
                'mode': 'markers',
                'name': '',
                'orientation': 'v',
                'showlegend': False,
                'type': 'scatter'
            })
            _fig_sigma['data'].append({
                'hovertemplate': 'x=%{x}<br>y=%{y}<extra></extra>',
                'legendgroup': '',
                'marker': {'color': '#636efa', 'symbol': 'circle'},
                'mode': 'markers',
                'name': '',
                'orientation': 'v',
                'showlegend': False,
                'type': 'scatter'
            })
            _fig_sigma['data'].append({
                'hovertemplate': 'x=%{x}<br>y=%{y}<extra></extra>',
                'legendgroup': '',
                'marker': {'color': 'red', 'symbol': 'circle'},
                'mode': 'markers',
                'name': '',
                'orientation': 'v',
                'showlegend': False,
                'type': 'scatter'
            })
            _fig_trace['data'].append({})
            _fig_sigma['data'].append({})
        
    
        _fig_trace['data'][1]['x']=_trace_fit[_n_trace].good.x
        _fig_trace['data'][1]['y']=_trace_fit[_n_trace].good.c
        _fig_trace['data'][2]['x']=_trace_fit[_n_trace].bad.x
        _fig_trace['data'][2]['y']=_trace_fit[_n_trace].bad.c
        _fig_trace['data'][3]['x']=xx
        _fig_trace['data'][3]['y']=c_fit
        
        _fig_sigma['data'][1]['x']=_trace_fit[_n_trace].good.x
        _fig_sigma['data'][1]['y']=_trace_fit[_n_trace].good.s
        _fig_sigma['data'][2]['x']=_trace_fit[_n_trace].bad.x
        _fig_sigma['data'][2]['y']=_trace_fit[_n_trace].bad.s
        _fig_sigma['data'][3]['x']=xx
        _fig_sigma['data'][3]['y']=s_fit
    
    return _fig_trace,_fig_sigma


#trace profile figure handler
@app.callback(
    Output("trace-profile",'figure'),
    #---------------------
    Input("store_from_find_trace",'data'),
    Input("trace_tracker", 'clickData'),
    #---------------------
    State("n_trace",'data'),
    State("2d-data",'data'),
    State("trace-profile",'figure'),
    #---------------------
    prevent_initial_call=True
)
def trace_profile_figures(_trace_data, _click_data, _n_trace, _2d_data, _fig_profile):#, _fig_trace, _fig_sigma):
        
    debug()
    
    ctx = callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger_id=="trace_tracker":
        X_MID=_click_data['points'][0]['x']
        Y_MID=_click_data['points'][0]['y']
        
    
    else:
        X_MID_idx=int((len(_trace_data[0]) - 1)/2)
        X_MID=_trace_data[0][X_MID_idx]
        Y_MID=_trace_data[1][X_MID_idx]
    
    xx=list(range(int(Y_MID-30),int(Y_MID+30)))
    
    _fig_profile['data'][0]['y'] = _2d_data['data'][:,X_MID][int(Y_MID-30):int(Y_MID+30)]
    _fig_profile['data'][0]['x'] = xx
    _fig_profile['data'][0]['name']='data'
    
    height=max(_fig_profile['data'][0]['y'])-min(_fig_profile['data'][0]['y'])
    top=max(_fig_profile['data'][0]['y'])+0.055*height
    bottom=min(_fig_profile['data'][0]['y'])-0.055*height
    
    _fig_profile['data'].append({})
    _fig_profile['data'].append({})
    
    for i,el in enumerate(_trace_data[0]):
        if el==X_MID:
            popt=_trace_data[3][i]
            bg=_trace_data[4][i]
    
    
    _fig_profile['data'][1]['x']=xx
    _fig_profile['data'][1]['y']=em.gauss(xx,*popt)+np.polyval(bg,xx)
    _fig_profile['data'][1]['line']={'color': '#red', 'dash': 'solid'}
    _fig_profile['data'][1]['name']='gaussian fit'
    
    _fig_profile['data'][2]['x']=xx
    _fig_profile['data'][2]['y']=np.polyval(bg,xx)
    _fig_profile['data'][2]['line']={'color': 'orange', 'dash': 'dash'}
    _fig_profile['data'][2]['name']='linear background'
    

    if 'shapes' not in _fig_profile['layout']:
        _fig_profile['layout']['shapes']=[]
        
    _fig_profile['layout']['shapes'].append({
        'type': 'rect',
        'x0':Y_MID-25,
        'x1':Y_MID-15,
        'y0':bottom,
        'y1':top,
        'line':{'color':'yellow','width':2},
        'fillcolor':'yellow',
        'layer':'below',
        'showlegend': False,
        'editable': True
    })

        
    _fig_profile['layout']['shapes'].append({
        'type': 'rect',
        'x0':Y_MID+15,
        'x1':Y_MID+25,
        'y0':bottom,
        'y1':top,
        'line':{'color':'yellow','width':2},
        'fillcolor':'yellow',
        'layer':'below',
        'showlegend': False,
        'editable': True
    })


    return _fig_profile
    
    
@app.callback(
    Output("spectrum-store",'data'),
    #Output("spectrum-arc-store",'data'),
    #---------------------
    Trigger("extract-trace",'n_clicks'),
    #---------------------
    State("2d-data",'data'),
    State("2d-data-arc",'data'),
    State("trace-store",'data'),
    State("spectrum-store",'data'),
    State("spectrum-arc-store",'data'),
    State("n_trace",'data'),
    #---------------------
    prevent_initial_call=True
)
def extract_trace(_2d_data, _2d_data_arc, _trace_store, _spectrum_store, _spectrum_arc_store, _n_trace):
    debug()

    if _spectrum_store is None:
        _spectrum_store=[]
    if _spectrum_arc_store is None:
        _spectrum_arc_store=[]
    
    print(_n_trace)
    
    for i in range(_n_trace+1):
        try:
            _spectrum_store[i]
        except:
            _spectrum_store.append({})
            _spectrum_arc_store.append({})

    s_x = _trace_store[_n_trace].all.x
    s_y = em.extract_trace(_2d_data['data'],_trace_store[_n_trace])
    
    _spectrum_store[_n_trace]['x'] = s_x
    _spectrum_store[_n_trace]['y'] = s_y
    _spectrum_store[_n_trace]['filename'] = _2d_data['filename']
    #_spectrum_store[_n_trace]['header'] = _2d_data['header']
    
    #this is not yet implemented
    #arc_y = em.extract_trace(_2d_data_arc['data'], _trace_store[_n_trace], arc=True)
    
#    _spectrum_arc_store[_n_trace]['x'] = s_x
#    _spectrum_arc_store[_n_trace]['y'] = s_y
#    _spectrum_arc_store[_n_trace]['filename'] = _2d_data_arc['filename']
#    _spectrum_arc_store[_n_trace]['header'] = _2d_data_arc['header']
    
    return _spectrum_store#, _spectrum_arc_store
    


@app.callback(
    Output("spectrum",'figure'),
    #---------------------
    Input("spectrum-store",'data'),
    Input("n_trace",'data'),
    #---------------------
    State("spectrum",'figure'),
    #---------------------
    prevent_initial_call=True
)
def plot_trace(_spectrum_store, _n_trace, _spectrum):
    try:
        _spectrum_store[_n_trace]
    except:
        return initials.spectrum
        
    debug()

    _spectrum['data'][0]['x'] = _spectrum_store[_n_trace]['x']
    _spectrum['data'][0]['y'] = _spectrum_store[_n_trace]['y']
    
    return _spectrum


@app.callback(
    Output("n_trace",'data'),
    Output("trace_table", 'style_data_conditional'),
    Output("trace_table", 'data'),
    Output("trace_action",'data'),
    #---------------------
    Trigger("new-trace",'n_clicks'),
    #---------------------
    State("trace_table", 'style_data_conditional'),
    State("n_trace",'data'),
    State("trace_table",'data'),
    #---------------------
    prevent_initial_call=True
    )
def add_new_trace(_style,_n_trace,_trace_table):
    
    debug()
    new_trace=len(_trace_table)
    
    col=em.get_trace_col(_trace_table)
    
    _trace_table.append({
        'trace_id':new_trace+1,
        'style': '<img src="assets/style_{}_d.png" alt="trace style" width="40">'.format(col),
        'visible_icon':'<img src="assets/visible.png" alt="visible" width="40">',
        'status':'empty',
        'visible':1,
        'trace_paths':[]
    })
    
    _style[2] = {'if': {'row_index': new_trace}, 'backgroundColor': 'rgba(150, 180, 225, 0.2)'}
    
    return new_trace,_style,_trace_table,'new_trace'
    

@app.callback(
    Output("n_trace",'data'),
    Output("trace_table", 'style_data_conditional'),
    Output("trace_table", 'active_cell'),
    Output("trace_table", 'selected_cells'),
    Output("trace_table", 'data'),
    Output("trace_action",'data'),
    #---------------------
    Input("trace_table", 'active_cell'),
    #---------------------
    State("trace_table", 'data'),
    State("trace_table", 'style_data_conditional'),
    State("n_trace",'data'),
    #---------------------
    prevent_initial_call=True
)
def style_selected_rows(_cell, _trace_table, _style, _n_trace):
    if _cell is None:
        raise PreventUpdate
    
    debug()
    
    #if the user changes raw, just update the active raw, and don't actually grab any button associated with the clicked cell
    if _n_trace!=_cell['row']:
        _style[2] = {'if': {'row_index': _cell['row']}, 'backgroundColor': 'rgba(150, 180, 225, 0.2)'}
        return _cell['row'], _style, None, [], _trace_table, 'none'


    #set visible/not_visible
    if _cell['column'] == 2:
        if _trace_table[_n_trace]['visible']:
            _trace_table[_n_trace]['visible'] = 0
            _trace_table[_n_trace]['visible_icon'] = '<img src="assets/not_visible.png" alt="not_visible" width="40">'

            for tr in range(len(_trace_table[_n_trace]['trace_paths'])):
                _trace_table[_n_trace]['trace_paths'][tr]['visible']=False
                
        else:
            _trace_table[_n_trace]['visible'] = 1
            _trace_table[_n_trace]['visible_icon'] = '<img src="assets/visible.png" alt="visible" width="40">'
            for tr in range(len(_trace_table[_n_trace]['trace_paths'])):
                _trace_table[_n_trace]['trace_paths'][tr]['visible']=True
    
    
    return no_update, no_update, None, [], _trace_table, 'edit'



@app.callback(
    Output("trace_table", 'data'),
    Output("trace_action",'data'),
    #---------------------
    Trigger("move_up_button", 'n_clicks'),
    Trigger("move_down_button", 'n_clicks'),
    #---------------------
    State("trace_table", 'data'),
    State("n_trace",'data'),
    State("shift_value",'value'),
    State("shift_units",'value'),
    #---------------------
    prevent_initial_call=True
)
def move_trace_up_down(_trace_table, _n_trace, _shift, _shift_unit):
    debug()
    
    #to implement the shift in arcseconds
    
    ctx = callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id=="move_up_button":
        dir= 1
    else:
        dir=-1
    
    for tr in range(len(_trace_table[_n_trace]['trace_paths'])):
        _trace_table[_n_trace]['trace_paths'][tr]['path'] = em.shift_path(_trace_table[_n_trace]['trace_paths'][tr]['path'], _shift*dir)
    
    return _trace_table,'edit'



@app.callback(
    Output("trace_table", 'data'),
    Output("trace_action",'data'),
    Output("shape_idx",'data'),
    #---------------------
    Trigger("copy_button", 'n_clicks'),
    #---------------------
    State("trace_table", 'data'),
    State("n_trace",'data'),
    State("shape_idx",'data'),
    #---------------------
    prevent_initial_call=True
)
def copy_trace(_trace_table, _n_trace, _shape_idx):
    debug()
    
    new_trace=len(_trace_table)
    
    col=em.get_trace_col(_trace_table)
    
    _trace_table.append({
        'trace_id':new_trace+1,
        'style': '<img src="assets/style_{}_d.png" alt="trace style" width="40">'.format(col),
        'visible_icon':'<img src="assets/visible.png" alt="visible" width="40">',
        'status':_trace_table[_n_trace]['status'],
        'visible':1,
        'trace_paths':[]
        #not copy trace_paths here. Doing below
    })
    
    for tr in _trace_table[_n_trace]['trace_paths']:
        _shape_idx=_shape_idx+1
    
        _trace_table[-1]['trace_paths'].append(as_path(tr['path'],_color=em.get_color(new_trace)))
        _trace_table[-1]['trace_paths'][-1]['shape_id']=_shape_idx

    
    #_style[2] = {"if": {"row_index": _n_trace}, "backgroundColor": "rgba(150, 180, 225, 0.2)"}
    
    return _trace_table,'copy',_shape_idx



@app.callback(
    Output("n_trace",'data'),
    Output("trace_table", 'data'),
    Output("trace_table", 'style_data_conditional'),
    Output("trace_action",'data'),
    Output("deleted_traces",'data'),
    #---------------------
    Trigger("delete_button", 'n_clicks'),
    #---------------------
    State("trace_table", 'data'),
    State("n_trace",'data'),
    State("trace_table", 'style_data_conditional'),
    State("deleted_traces",'data'),
    #---------------------
    prevent_initial_call=True
)
def delete_trace(_trace_table, _n_trace, _style, _deleted_traces):
    debug()
    
    #changing the indexes of the remaining traces
    for tr in range(_n_trace,len(_trace_table)):
        _trace_table[tr]['trace_id']=_trace_table[tr]['trace_id']-1
    
    _deleted_traces.append(_trace_table.pop(_n_trace))
    
    _style[2] = {'if': {'row_index': _n_trace}, 'backgroundColor': 'rgba(150, 180, 225, 0.2)'}

    return _n_trace-1, _trace_table, _style, 'delete', _deleted_traces


@app.callback(
    Output("trace_table", 'data'),
    #---------------------
    Trigger("write-out", 'n_clicks'),
    #---------------------
    State("spectrum-store",'data'),
    State("spectrum-arc-store",'data'),
    State("trace_table", 'data'),
    State("n_trace",'data'),
    #---------------------
    prevent_initial_call=True
)
def write_out_spectrum(_spectrum, _spectrum_arc, _trace_table, _n_trace):
    debug()
    
    em.write_out(_spectrum[_n_trace], _spectrum_arc[_n_trace])
    
    _trace_table[_trace_table]['status']='written out'
    
    return _trace_table
    


#this is just for debuggin. I put an extra button to print out what I need to check
@app.callback(
    Output("none",'children'),
    #---------------------
    Trigger("tester",'n_clicks'),
    #---------------------
    #State("2d",'figure'),
    #State("trace_table",'data'),
    #State("n_trace",'data'),
    State("cut",'figure'),
    #---------------------
    prevent_initial_call=True
    )
def tester(_inp):#,_n_trace):
    for line in _inp['data'][0]:
        print(line,_inp['data'][0][line])
#    for el in _inp['layout']['shapes']:
#        print(el)
#    print(len(_table))
#    for el in range(len(_inp[_n_trace])):
#        print(el,len(_inp[el]['trace_paths']))
#        for item in _inp[el]['trace_paths']:
#            print(item['id_in_fig'],item['path'])
#        print(_inp[_n_trace][el])
    return 0




if __name__ == '__main__':

    print('Emptying cache...',end=' ')
    os.system('rm {}/*'.format(cache_dir))
    print('Done.')
    
    app.run_server(debug=True)

