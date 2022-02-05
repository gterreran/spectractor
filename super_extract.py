#!/usr/bin/env python

#next line are for debugging. It helps figuring out at what line the script is.
import inspect #import currentframe

import astropy.io.fits as pf
from astropy.visualization import ZScaleInterval,MinMaxInterval
import numpy as np
import copy,glob,json
import extract_module as em

import dash,json,sys,os


import layout

#from dash.long_callback import DiskcacheLongCallbackManager
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from dash_extensions.enrich import Dash,Trigger,ServersideOutput, FileSystemStore
#from dash_extensions.enrich import DashProxy, TriggerTransform, ServersideOutputTransform

cache_dir="./cache"

output_defaults=dict(backend=FileSystemStore(cache_dir=cache_dir), session_check=True)

print('Emptying cache...',end=' ')
os.system('rm {}/*'.format(cache_dir))
print('Done.')

#import diskcache
#cache = diskcache.Cache("./cache")
#long_callback_manager = DiskcacheLongCallbackManager(cache)


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


#print(type(px.data.iris()))
#sys.exit()

#app = dash.Dash(__name__, long_callback_manager=long_callback_manager)
#app = dash.Dash(__name__)
#app = Dash(__name__)
app = Dash(output_defaults=output_defaults)
#app = DashProxy(transforms=[
#    TriggerTransform(),  # enable use of Trigger objects
#    ServersideOutputTransform()  # enable use of ServersideOutput objects
#])

app.layout = layout.layout

#############################################################################################

#upload image and storing the data.
@app.callback(
    ServersideOutput("2d_data",'data'),
    #---------------------
    Input("load-2d",'filename'),
    #---------------------
    prevent_initial_call=True
)
def upload_image(filename):
    debug()
    
    d,z={},{}
    d['data']=pf.getdata(filename)
    d['Y_DIM']=len(d['data'])
    d['X_DIM']=len(d['data'][0])
    
    return d


#here I handle the contrast nozles.
@app.callback(
    Output("2d_scales",'data'),
    Output("zslider",'value'),
    Output("zslider",'min'),
    Output("zslider",'max'),
    Output("zmin",'value'),
    Output("zmax",'value'),
    #---------------------
    Input("2d_data",'data'),
    Input("zslider",'value'),
    Input("zmin",'value'),
    Input("zmax",'value'),
    #---------------------
    State("2d_scales",'data'),
    #---------------------
    prevent_initial_call=True
)
def update_scale_2d_and_slider(_2d_data, _zslider, _zmin, _zmax, _zlims_json):
    debug()
    
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == "2d_data":
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
    Output("2d",'figure'),   #the output is the element with id=2d and will affect the figure component of the element. (Graph has a figure component, of course)
    #---------------------
    Input("2d_scales",'data'),
    Input("2d_data",'data'),
    Input("drawing-style", 'value'),
    Input("2d_figure_shapes",'data'),
    #---------------------
    State("2d",'figure'),       #inputs fire the callback. States don't.
    #State('load_csv', 'value'),
    #---------------------
    prevent_initial_call=True
)
def main_figure_update(_zlims_json, _2d_data, _drawing_style, _shapes, _fig):
    debug()
    
    ctx = dash.callback_context
    #multiple triggers can occure here, so it's better to check if the trigger is present in a list instead to check that it's the first
    trigger_list = [el['prop_id'].split('.')[0] for el in ctx.triggered]
    
    if "drawing-style" in trigger_list:
        _fig['layout']['dragmode']=_drawing_style
    
    #storing the shapes in a seperate variable is reduntant, as all the shapes are already stored in the figure. However, it allows to keep just one Output for '2d', as some callbacks that wants to draw, will actually add the shape to the list, which triggers this callback.
    if "2d_figure_shapes" in trigger_list:
        shapes=json.loads(_shapes)

        #some callback returned a trace to plot on the 2d.
        if len(_fig['layout']['shapes']) != len(shapes):
            _fig['layout']['shapes'].append(shapes[-1])
        
        #if last thing added wasn't a path, it means that the user drew it, and it was a straight line. Here the it gets converted into a path.
        #The else here is required because if the user use the autofind without any shape drawn, _fig['layout']['shapes'] is empty and it will return an error.
        #At least in this way it will not check if new trace is a line, as by construction it is not
        elif _fig['layout']['shapes'][-1]['type'] != 'path':
            _fig['layout']['shapes'][-1]=shapes[-1]
        
        #pass
    
    if "2d_data" in trigger_list:
        _fig['data'][0]['z']=_2d_data['data']
        _fig['layout']['shapes']=[]
        
    if "2d_scales" in trigger_list:
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
    State("2d_data",'data'),
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
        return '0','0','0',zoom_fig


#@app.callback(
#    Output("cut",'figure'),
#    Input("2d", 'clickData')
#)
#def display_cut(clickData):
#    if clickData is not None:
#        x0=clickData['points'][0]['x']
#        y0=clickData['points'][0]['y']
#        y_cut=np.array(d[y0-50:y0+50,x0])
#
#        cut['data'][0]['x']=np.arange(x0-50,x0+50)
#        cut['data'][0]['y']=y_cut
#        return cut
#    else:
#        return px.line(np.zeros(100))


#click and drag projection
@app.callback(
    Output("cut",'figure'),
    Output("2d_figure_shapes",'data'),
    #---------------------
    Input("2d",'relayoutData'),
    #---------------------
    State("2d_data",'data'),
    State("2d_figure_shapes",'data'),
    State("cut",'figure'),
    #---------------------
    prevent_initial_call=True
)
def drawing_and_storing_as_path(_2d_relayoutData,_2d_data,_shapes_json,_cut_fig):
    #there is an autoshape relayoutData event that triggers, so we need extra precautions to avoid this callback to fire only when we want to.
    if not any(['shapes' in key for key in _2d_relayoutData]):
        raise PreventUpdate
        
    debug()
    
    shapes=json.loads(_shapes_json)
    
    if 'shapes' in _2d_relayoutData:
        #triggered by the deletion of a segment
        if len(_2d_relayoutData['shapes'])<len(shapes):
            current_shapes=[]
            for shape in _2d_relayoutData['shapes']:
                current_shapes.append(shape['path'])
            for i,segment in enumerate(shapes):
                if segment['path'] not in current_shapes:
                    shapes.pop(i)
                    break
            
            return _cut_fig,json.dumps(shapes)
        
                    
        #triggered by drawing a new segment
        else:
            #both straigh line and paths are handled as SVG paths.
            path=get_path(_2d_relayoutData['shapes'][-1])
        
        shapes.append(as_path(path))

    #if 'shapes' is not in _2d_relayoutData and the code reached this point, then it means that the user moved something
    else:
        
        key0=next(iter(_2d_relayoutData))
        shape_index=int(key0[key0.find('[')+1:key0.find(']')])
        
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
    
        shapes[shape_index]=shapes.append(as_path(path))
        
        
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
    
    return _cut_fig,json.dumps(shapes)

    
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
    Trigger("auto-find",'on'),
    #---------------------
    Input("2d_figure_shapes",'data'),
    #---------------------
    State("find-trace",'disabled'),
    #---------------------
    prevent_initial_call=True
)
def auto_find_trace_selected(_proj,_state):
    if _state==False and _proj=='[]':
        return True
    elif _state==True and _proj!='[]':
        return False
    else:
        return False
    

@app.callback(
    Output("extract-trace",'disabled'),
    #---------------------
    Input("trace_fit_store",'data'),
    #---------------------
    prevent_initial_call=True
)
def activate_extract_button(_trace_data):
    if _trace_data!='[]':
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
    Input("trace_fit_store",'data'),
    #---------------------
    State("trace_points",'data'),
    State("refit_trace_button",'disabled'),
    #---------------------
    prevent_initial_call=True
)
def activate_refit_button(trace_fit_store, _trace_points, _status):
    
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == "trace_fit_store":
        return True
    #this prevents to try to refit when there are no data
    elif _trace_points is None:
        raise PreventUpdate
    else:
        return False


#trace and sigma figures handler
@app.callback(
    Output("trace_tracker",'figure'),
    Output("sigma_tracker",'figure'),
    #---------------------
    Input("trace_points",'data'),
    Input("trace_fit_store",'data'),
    #---------------------
    State("trace_tracker",'figure'),
    State("sigma_tracker",'figure'),
    #---------------------
    prevent_initial_call=True
)
def trace_and_sigma_figures(_trace_points,_trace_fit,_fig_trace,_fig_sigma):
    debug()
    
    ctx = dash.callback_context
    trigger_list = [el['prop_id'].split('.')[0] for el in ctx.triggered]

    if "trace_points" in trigger_list:
        _fig_trace['data'][0]['x']=_trace_points[0]
        _fig_trace['data'][0]['y']=_trace_points[1]

        _fig_sigma['data'][0]['x']=_trace_points[0]
        _fig_sigma['data'][0]['y']=_trace_points[2]

    if "trace_fit_store" in trigger_list:
        _fig_trace['data'][0]['visible']=False
        _fig_trace['data'][0]['visible']=False
    
        xx=_trace_points[0]

        c_fit=_trace_fit['func_c'].eval(xx,_trace_fit['popt_c'])
        s_fit=_trace_fit['func_s'].eval(xx,_trace_fit['popt_s'])
        
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
        
    
        _fig_trace['data'][1]['x']=_trace_fit['good_x']
        _fig_trace['data'][1]['y']=_trace_fit['good_c']
        _fig_trace['data'][2]['x']=_trace_fit['bad_x']
        _fig_trace['data'][2]['y']=_trace_fit['bad_c']
        _fig_trace['data'][3]['x']=xx
        _fig_trace['data'][3]['y']=c_fit
        
        _fig_sigma['data'][1]['x']=_trace_fit['good_x']
        _fig_sigma['data'][1]['y']=_trace_fit['good_s']
        _fig_sigma['data'][2]['x']=_trace_fit['bad_x']
        _fig_sigma['data'][2]['y']=_trace_fit['bad_s']
        _fig_sigma['data'][3]['x']=xx
        _fig_sigma['data'][3]['y']=s_fit
        
    return _fig_trace,_fig_sigma


@app.callback(
    ServersideOutput("trace_points",'data'),
    #---------------------
    Trigger("find-trace",'n_clicks'),
    #---------------------
    State("2d_data",'data'),
    State("auto-find",'on'),
    State("2d_figure_shapes",'data'),
    #---------------------
    prevent_initial_call=True
)
def find_trace(_2d_data,_auto,_shapes):
    debug()
    
    if _auto:
        X_DIM=_2d_data['X_DIM']
    
        #it will start from the midpoint and first search on the right and then go back from the middle and search on the left

        right_data=list(range(int(X_DIM/2)+1,X_DIM))
        left_data=list(range(int(X_DIM/2),-1,-1))
        
        cen_0=em.guess_trace_position(np.array(_2d_data["data"])[:,int(X_DIM/2)])
        
        
        selection=[[right_data,[cen_0]*len(right_data)],[left_data,[cen_0]*len(left_data)]]
        
    else:
        selection=[]
        for el in json.loads(_shapes):
            xx,yy,orientation=em.get_points_from_path(el['path'])
            selection.append([xx,yy])
    
    xx,yy,ss=em.find_trace(selection,_2d_data["data"],auto=_auto)
    
    return [xx,yy,ss]
    
    
@app.callback(
    ServersideOutput("trace_fit_store",'data'),
    Output("2d_figure_shapes",'data'),
    #---------------------
    Trigger("refit_trace_button",'n_clicks'),
    #---------------------
    Input("trace_points",'data'),
    #---------------------
    State("trace_func",'value'),
    State("trace_func_order",'value'),
    State("sigma_func",'value'),
    State("sigma_func_order",'value'),
    State("2d_figure_shapes",'data'),
    #---------------------
    prevent_initial_call=True
)
def fit_trace(_trace_points, _func_cen_lab, _order_cen, _func_sig_lab, _order_sig, _shapes):
    debug()
    
    tt=em.fit_trace(_trace_points,_func_cen_lab,_order_cen,_func_sig_lab,_order_sig)
    
    trace_store={
        'all_x':_trace_points[0],
        'good_x':tt[0],
        'good_c':tt[1],
        'good_s':tt[2],
        'bad_x':tt[3],
        'bad_c':tt[4],
        'bad_s':tt[5],
        'func_c':em.func(_func_cen_lab,_order_cen),
        'func_s':em.func(_func_sig_lab,_order_sig),
        'popt_c':tt[6],
        'popt_s':tt[7],
    }
    
    c_fit=trace_store['func_c'].eval(_trace_points[0],tt[6])
    path=em.points_to_svg(_trace_points[0],c_fit)
    
    #as it is, if I refit, it will draw a new trace on the 2d
    shapes_out=json.loads(_shapes)
    current_shape=as_path(path)
    if current_shape not in shapes_out:
        shapes_out.append(current_shape)
        shapes_out=json.dumps(shapes_out)

    return trace_store,shapes_out


@app.callback(
    Output("spectrum",'figure'),
    #---------------------
    Trigger("extract-trace",'n_clicks'),
    #---------------------
    State("2d_data",'data'),
    State("trace_fit_store",'data'),
    State("spectrum",'figure'),
    #---------------------
    prevent_initial_call=True
)
def extract_trace(_2d_data,_trace_store,_spectrum):
    debug()

    _spectrum['data'][0]['x']=_trace_store['all_x']
    _spectrum['data'][0]['y']=em.extract_trace(_2d_data["data"],_trace_store)
    
    return _spectrum


@app.callback(
    Output("refit_trace_button",'disabled'),
    #---------------------
    Trigger("shape-printer", 'n_clicks'),
    #---------------------
    State("2d",'figure'),
    #---------------------
    prevent_initial_call=True
)
def clicker_2d(_fig):
    debug()
    
    for el in _fig['layout']['template']:
        print(el,_fig['layout']['template'][el])

    return True
    
    
@app.callback(
    Output("refit_trace_button",'disabled'),
    #---------------------
    Input("2d", 'clickAnnotationData'),
    #---------------------
    prevent_initial_call=True
)
def clicker_2d(_clickData_2d):
    debug()

    print(_clickData_2d)

    return True

@app.callback(
    Output("refit_trace_button",'disabled'),
    #---------------------
    Input("trace_tracker", 'clickData'),
    #---------------------
    prevent_initial_call=True
)
def clicker_trace(_clickData_trace):
    debug()

    print(_clickData_trace)

    return True
    
if __name__ == '__main__':
    app.run_server(debug=True)



#fig.update_layout(coloraxis_showscale=False)
#fig.update_xaxes(showticklabels=False)
#fig.update_yaxes(showticklabels=False)
#fig.show()
#
#app.run_server(debug=True)
