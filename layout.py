#import dash_core_components as dcc
from dash import dcc,html,dash_table
import dash_daq as daq
import initials



layout = html.Div([
    #dummy div to use as input to inizialize the store at launch, which for some reason it fails.
    html.Div(id='none',children=[],style={'display': 'none'}),
    dcc.Store(id='2d-data'),
    dcc.Store(id='2d-scales'),
    dcc.Store(id='trace-store'),
    dcc.Store(id='n_trace',data=-1),
    dcc.Store(id='store_from_find_trace'),
    dcc.Store(id='store_from_fit_trace'),
    #it's just easier to track what the user is doing with a dedicated varible instead of trying to figure it out from how the data change.
    dcc.Store(id='trace_action', data=''),
    dcc.Store(id='deleted_traces', data=[]),
    dcc.Store(id='shape_idx', data=-1), #unique id for new shapes
    html.Button('Tester', id='tester', n_clicks=0),
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
                            value=initials.zmin,
                            disabled=True
                        )
                    ],style={'width': '20%','display': 'inline-block'}),
                    html.Div([
                        dcc.RangeSlider(
                            id='zslider',
                            min=initials.zmin,
                            max=initials.zmax,
                            step=initials.step,
                            value=[initials.zmin,initials.zmax],
                            disabled=True
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
                            value=initials.zmax,
                            disabled=True
                        )
                    ],style={'width': '20%','display': 'inline-block'})
                ])
            ],
            style={'width': '60%','display': 'inline-block'}
            ),
            
            html.Div([
#                html.Table(
#                    children=initials.table,
#                    id='trace_table',
#                    style={'border': '1px solid black'}
#                ),
                dash_table.DataTable(
                    id='trace_table',
                    columns=[
                        {'name': 'Trace','id': 'trace_id','deletable': False,'renamable': False},
                        {'name': 'Style','id': 'style','type': 'text', 'presentation': 'markdown', 'deletable': False,'renamable': False},
                        #{'name': 'Action','id': 'delete_icon','type': 'text', 'presentation': 'markdown', 'deletable': False,'renamable': False},
                        #{'name': 'Action','id': 'up_icon','type': 'text', 'presentation': 'markdown', 'deletable': False,'renamable': False},
                        #{'name': 'Action','id': 'down_icon','type': 'text', 'presentation': 'markdown', 'deletable': False,'renamable': False},
                        #{'name': 'Action','id': 'copy_icon','type': 'text', 'presentation': 'markdown', 'deletable': False,'renamable': False},
                        {'name': 'Visible','id': 'visible_icon','type': 'text', 'presentation': 'markdown', 'deletable': False,'renamable': False},
                        {'name': 'Status','id': 'status','deletable': False,'renamable': False},
                    ],
                    data=[],
                    style_data_conditional = [{
                        "if": {"state": "active"},
                        "backgroundColor": "rgba(150, 180, 225, 0.2)",
                        "border": "inherit !important",
                    },
                    {
                        "if": {"state": "selected"},
                        "backgroundColor": "rgba(150, 180, 225, 0.2)",
                        "border": "inherit !important",
                    },
                    {
                        "if": {"row_index": 0},
                        "backgroundColor": "rgba(150, 180, 225, 0.2)"
                        
                    }],
                    editable=True,
                    
#                    dropdown_conditional=[{
#                        'if': {
#                            'column_id':'style'
#                        },
#                        'options': [
#                            {'label': i, 'value': i}
#                            for i in [
#                                'Mile End',
#                                'Plateau',
#                                'Hochelaga'
#                            ]
#                        ]
#                    }],
                    
                    markdown_options={"html": True},
                    merge_duplicate_headers=True,
                ),
                
                #in order to update the file list everytime I click, I actually record the click on the parent of the dropdown"
                html.Div([
                    html.Div(
                        id='dropdown-parent',
                        children=dcc.Dropdown(
                            id="load_csv",
                            searchable=False,
                            placeholder="Load a trace"
                        )
                        
                    ),
                    html.Button('Load', id='load-trace', n_clicks=0)
                ],
                style={'width': '50%','display': 'inline-block'}
                ),
                html.Div(
                    html.Button('New trace', id='new-trace', n_clicks=0),
                    style={'width': '40%','display': 'inline-block'}
                ),
                html.Button(
                    children=[html.Img(src='assets/delete.png', style={'width':'60px','margin-left': '0px'})],
                    id="delete_button", n_clicks=0,
                    style={'width':'50px','height':'50px'}
                ),
                html.Button(
                    children=[html.Img(src='assets/copy.png', style={'width':'50px','margin-left': '0px'})],
                    id="copy_button", n_clicks=0,
                    style={'width':'50px','height':'50px'}
                ),
                html.Button(
                    children=[html.Img(src='assets/up.png', style={'width':'50px','margin-left': '0px'})],
                    id="move_up_button", n_clicks=0,
                    style={'width':'50px','height':'50px'}
                ),
                html.Button(
                    children=[html.Img(src='assets/down.png', style={'width':'50px','margin-left': '0px'})],
                    id="move_down_button", n_clicks=0,
                    style={'width':'50px','height':'50px'}
                ),
                html.Div([
                    html.Div(
                        dcc.Input(
                            id="shift_value",
                            type='number',
                            debounce=True,  #debounce=True let user finish typing the number before updating. Otherwise the change is interactive while the user is typing
                            value=1,
                        ),
                        style={'width': '50%','display': 'inline-block'}
                    ),
                    html.Div(
                        dcc.Dropdown(
                            id="shift_units",
                            searchable=False,
                            options=[
                                {'label': 'pixel', 'value': 'pixel'},
                                {'label': 'arcsec', 'value': 'arcsec'}
                            ],
                            value='pixel'
                        ),
                        style={'width': '50%','display': 'inline-block'}
                    )
                ])
            ],
            style={'width': '40%','display': 'inline-block','verticalAlign': 'top'}
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

