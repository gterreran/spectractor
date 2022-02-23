#!/usr/bin/env python

#next line are for debugging. It helps figuring out at what line the script is.
import inspect #import currentframe

import logging

import astropy.io.fits as pf
from astropy.visualization import ZScaleInterval,MinMaxInterval
import numpy as np
import copy,glob,json
import extract_module as em
import dash,json,sys,os,base64,io
from dash import html


import layout

#from dash.long_callback import DiskcacheLongCallbackManager
#from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from dash_extensions.enrich import Dash,Trigger,ServersideOutput, FileSystemStore, Input, Output, State


def debug():
    #print(currentframe().f_back.f_lineno)
    print('{} fired. Line {}.'.format(inspect.stack()[1][3],inspect.stack()[1][2]))

def check_folder_for_traces():
    options=[]
    for f in glob.glob('*trace.csv'):
        options.append({'label': f, 'value': f})
    return options

def get_path(_pp):
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

#It is not possible to have multiple ServersideOutput pointing to the same object. Only normal Outputs.
#To circumvent this, I'll have to create proxy Stores to receive the ServersideOutput from different callbacks, and use them as Inputs to update the real final ServersideOutput (trace-store)


cache_dir="./cache"

output_defaults=dict(backend=FileSystemStore(cache_dir=cache_dir), session_check=True)

#dash seems to login several times. I found this workaround on the internet
log = logging.getLogger(__name__)
app = Dash(__name__, output_defaults=output_defaults, assets_folder='assets')
#app = DashProxy(__name__, output_defaults=output_defaults, transforms=[
#    MultiplexerTransform(),  # makes it possible to target an output multiple times in callbacks
#    ServersideOutputTransform(),  # enable use of ServersideOutput objects
#    NoOutputTransform(),  # enable callbacks without output
#    BlockingCallbackTransform(),  # makes it possible to skip callback invocations while a callback is running
#])

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
    #---------------------
    State("trace_table",'data')
)
def upload_image(_contents,_trace_table):
    debug()
    d={}
    #Here I inizialize all the ServersideOutputs
    if _contents is None:
        d['data']=np.zeros(shape=(1000,3000))
        d['Y_DIM']=len(d['data'])
        d['X_DIM']=len(d['data'][0])
        d['no_trigger']=1
        
        return d,True,True,True,dash.no_update
    
    #If a proper image is loaded, I also activate the zscale nozles.
    else:
        content_type, content_string = _contents.split(',')
        fits = base64.b64decode(content_string)
        d['data']=pf.getdata(io.BytesIO(fits))
        d['Y_DIM']=len(d['data'])
        d['X_DIM']=len(d['data'][0])
        d['no_trigger']=0
    
    
        return d,False,False,False,1
    

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
    
    ctx = dash.callback_context
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
    
    ctx = dash.callback_context
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
    #---------------------
    State("trace_table",'data'),
    State("n_trace",'data'),
    State("find-trace",'disabled'),
    #---------------------
    prevent_initial_call=True
)
def auto_find_trace_selected(_auto,_trace_table, _n_trace, _state):
    debug()
    if _auto or len(_trace_table[_n_trace]['trace_paths'])!=0:
        return False
    else:
        return True
    

@app.callback(
    Output("extract-trace",'disabled'),
    #---------------------
    Input("trace-store",'data'),
    #---------------------
    State("n_trace",'data'),
    #---------------------
    prevent_initial_call=True
)
def activate_extract_button(_trace_data, _n_data):
    if len(_trace_data[_n_data].good.x)!=0:
        return False
    else:
        return True



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
    #---------------------
    Trigger("find-trace",'n_clicks'),
    #---------------------
    State("2d-data",'data'),
    State("auto-find",'on'),
    State("trace_table",'data'),
    State("n_trace",'data'),
    #---------------------
    prevent_initial_call=True
)
def find_trace(_2d_data, _auto, _trace_table, _n_trace):
    debug()
    
    
    if _auto:
        X_DIM=_2d_data['X_DIM']
    
        #it will start from the midpoint and first search on the right and then go back from the middle and search on the left

        right_data=list(range(int(X_DIM/2)+1,X_DIM))
        left_data=list(range(int(X_DIM/2),-1,-1))
        
        cen_0=em.guess_trace_position(np.array(_2d_data['data'])[:,int(X_DIM/2)])
        
        
        selection=[[right_data,[cen_0]*len(right_data)],[left_data,[cen_0]*len(left_data)]]
        
    else:
        selection=[]
        for el in _trace_table[_n_trace]['trace_paths']:
            xx,yy,orientation=em.get_points_from_path(el['path'])
            selection.append([xx,yy])
    
    xx,yy,ss=em.find_trace(selection,_2d_data['data'], auto=_auto)
    
    return [xx,yy,ss]
    
    
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
    
    xx,cc,ss=_find
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
    #---------------------
    State("trace_tracker",'figure'),
    State("sigma_tracker",'figure'),
    State("n_trace",'data'),
    #---------------------
    prevent_initial_call=True
)
def trace_and_sigma_figures(_trace_fit, _fig_trace, _fig_sigma, _n_trace):
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


@app.callback(
    Output("spectrum",'figure'),
    #---------------------
    Trigger("extract-trace",'n_clicks'),
    #---------------------
    State("2d-data",'data'),
    State("trace-store",'data'),
    State("spectrum",'figure'),
    State("n_trace",'data'),
    #---------------------
    prevent_initial_call=True
)
def extract_trace(_2d_data, _trace_store, _spectrum, _n_trace):
    debug()

    _spectrum['data'][0]['x']=_trace_store[_n_trace].all.x
    _spectrum['data'][0]['y']=em.extract_trace(_2d_data["data"],_trace_store[_n_trace])
    
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
    _n_trace=_n_trace+1
    
    _trace_table.append({
        'trace_id':_n_trace+1,
        'style':em.get_trace_style(_n_trace,'d'),
        'visible_icon':'<img src="assets/visible.png" alt="visible" width="40">',
        'status':'empty',
        'visible':1,
        'trace_paths':[]
    })
    
    _style[2] = {"if": {"row_index": _n_trace}, "backgroundColor": "rgba(150, 180, 225, 0.2)"}
    
    return _n_trace,_style,_trace_table,'new_trace'
    

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
        _style[2] = {"if": {"row_index": _cell['row']}, "backgroundColor": "rgba(150, 180, 225, 0.2)"}
        return _cell['row'], _style, None, [], _trace_table, dash.no_update


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
    
    
    return dash.no_update, dash.no_update, None, [], _trace_table, 'edit'



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
    
    ctx = dash.callback_context
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
    
    _trace_table.append({
        'trace_id':new_trace+1,
        'style':em.get_trace_style(new_trace,'d'),
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
    
    _deleted_traces.append(_trace_table.pop(_n_trace))
    
    _style[2] = {"if": {"row_index": _n_trace}, "backgroundColor": "rgba(150, 180, 225, 0.2)"}

    return _n_trace-1, _trace_table, _style, 'delete', _deleted_traces


@app.callback(
    Output("none",'children'),
    #---------------------
    Trigger("tester",'n_clicks'),
    #---------------------
    State("2d",'figure'),
    State("n_trace",'data'),
    #---------------------
    prevent_initial_call=True
    )
def add_new_trace(_inp,_n_trace):
    for el in _inp['layout']['shapes']:
        print(el)
#    print(len(_table))
#    for el in range(len(_table)):
#        print(el,len(_table[el]['trace_paths']))
#        for item in _table[el]['trace_paths']:
#            print(item['id_in_fig'],item['path'])
    return 0








if __name__ == '__main__':

    print('Emptying cache...',end=' ')
    os.system('rm {}/*'.format(cache_dir))
    print('Done.')
    
    app.run_server(debug=True)

