#import dash_core_components as dcc
from dash import dcc
#import dash_html_components as html
from dash import html
import dash_daq as daq
import initials



layout = html.Div([
    dcc.Store(id='2d_data'),#data=initials.data_0),
    dcc.Store(id='2d_scales'),
    dcc.Store(id='trace_points',data='[]'),
    dcc.Store(id='trace_fit_store',data='[]'),
    dcc.Store(id='2d_figure_shapes',data='[]'),
    html.Div([
        #First display row
        html.Div([
            html.Div(
                dcc.Graph(id="cut",figure=initials.cut),
                style={'width': '50%','display': 'inline-block'}
            ),
            html.Div(
                dcc.Graph(id="zoomin",figure=initials.zoom_fig),
                style={'width': '50%','display': 'inline-block'}
            )
        ]),
        
        #Button row
        html.Div([
            html.Div(
                dcc.Upload(id="load-2d",children=html.Button('Upload 2d image', n_clicks=0)),
                style={'display': 'inline-block'}
            ),
            html.Div(
                dcc.RadioItems(
                    id='drawing-style',
                    options=[
                        {'label': 'Straght line', 'value': 'drawline'},
                        {'label': 'Free hand drawing', 'value': 'drawopenpath'}
                    ],
                    value='drawline'
                ),
                style={'display': 'inline-block'}
            ),
            html.Div(
                html.Button('Find trace', id='find-trace', n_clicks=0, disabled=True),
                style={'display': 'inline-block'}
            ),
            html.Div(
                daq.BooleanSwitch(id='auto-find', on=False, label="Auto find", labelPosition="top"),
                style={'display': 'inline-block'}
            ),
            html.Div(
                html.Button('Extract trace', id='extract-trace', n_clicks=0, disabled=True),
                style={'display': 'inline-block'}
            )
        ]),
        
        #2d figure and Table
        html.Div([
            html.Div([
                html.Table([
                        html.Td([
                            dcc.Markdown('0',id='x')
                        ],style={'border': '1px solid black','width': '33%'}),
                        html.Td([
                            dcc.Markdown('0',id='y')
                        ],style={'border': '1px solid black','width': '33%'}),
                        html.Td([
                            dcc.Markdown('0',id='z')
                        ],style={'border': '1px solid black','width': '33%'})
                    ],
                    style={'border': '1px solid black'}),
                
                dcc.Graph(id="2d",figure=initials.fig, config=initials.config),
                
                html.Div([
                    html.Div([
                        "Zmin: ",
                        dcc.Input(
                            id='zmin',
                            placeholder=initials.zmin, #This is not selectable. It will disappars as soon as the user starts typing
                            type='number',
                            debounce=True,  #debounce=True let user finish typing the number before updating. Otherwise the change is interactive while the user is typing
                            step=initials.step,
                            value=initials.zmin
                        )
                    ],style={'width': '20%','display': 'inline-block'}),
                    html.Div([
                        dcc.RangeSlider(
                            id='zslider',
                            min=initials.zmin,
                            max=initials.zmax,
                            step=initials.step,
                            value=[initials.zmin,initials.zmax],
                        )
                    ],style={'width': '60%','display': 'inline-block'}),
                    html.Div([
                        "Zmax: ",
                        dcc.Input(
                            id='zmax',
                            placeholder=initials.zmax,
                            type='number',
                            debounce=True,
                            step=initials.step,
                            value=initials.zmax
                        )
                    ],style={'width': '20%','display': 'inline-block'})
                ])
            ],
            style={'width': '80%','display': 'inline-block'}
            ),
            
            html.Div([
                html.Table(
                    id='trace_table'
                ),
                
                #in order to update the file list everytime I click, I actually record the click on the parent of the dropdown"
                html.Div(
                    id='dropdown-parent',
                    children=[
                        dcc.Dropdown(
                            id="load_csv",
                            searchable=False,
                            placeholder="Load a trace"
                        )
                    ],
                    style={'width': '60%','display': 'inline-block'}
                ),
                html.Div(
                    html.Button('Load', id='load-trace', n_clicks=0),
                    style={'width': '60%','display': 'inline-block'}
                )
            ],
            style={'width': '20%','display': 'inline-block'}
            )
        ]),
    

        html.Div([
            html.Div([
                dcc.Graph(id="trace_tracker",figure=initials.tracetracker),
                html.Div([
                    html.Div(dcc.Dropdown(
                        id="trace_func",
                        searchable=False,
                        options=[
                            {'label': 'Chebyshev', 'value': 'Che'},
                            {'label': 'Legendre', 'value': 'Leg'},
                            {'label': 'Spline1', 'value': 'Sp1'},
                            {'label': 'Spline3', 'value': 'Sp3'}
                        ],
                        value='Leg'
                    ),style={'width': '40%','display': 'inline-block'}),
                    html.Div(dcc.Input(id='trace_func_order', type='number',step=1,value=3),style={'width': '30%','display': 'inline-block'}),
                    html.Div(html.Button('Re-Fit', id='refit_trace_button', disabled=True),style={'width': '30%','display': 'inline-block'}),
                ])
            ],
            style={'width': '35%','display': 'inline-block'}
            ),
            html.Div([
                dcc.Graph(id="sigma_tracker",figure=initials.sigmatracker),
                html.Div([
                    html.Div(dcc.Dropdown(
                        id="sigma_func",
                        searchable=False,
                        options=[
                            {'label': 'Chebyshev', 'value': 'Che'},
                            {'label': 'Legendre', 'value': 'Leg'},
                            {'label': 'Spline1', 'value': 'Sp1'},
                            {'label': 'Spline3', 'value': 'Sp3'}
                        ],
                        value='Leg'
                    ),style={'width': '40%','display': 'inline-block'}),
                    html.Div(dcc.Input(id='sigma_func_order', type='number',step=1,value=3),style={'width': '30%','display': 'inline-block'}),
                ])
            ],
            style={'width': '35%','display': 'inline-block'}
            ),
            html.Div(
                dcc.Graph(id="cut_display"),
                style={'width': '30%','display': 'inline-block'}
            )
        ]),
        html.Div(
            dcc.Graph(id="spectrum",figure=initials.spectrum)
        )
    ])
])

