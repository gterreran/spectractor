import plotly.express as px
import numpy as np
import json


zmin=0
zmax=0
step=1

fig = px.imshow(np.zeros(shape=(1000,3000)), origin='lower', zmin=zmin, zmax=zmax)

fig.layout.dragmode='drawline'
config = {
    "modeBarButtonsToAdd": [
        "eraseshape"
    ]
}

fig.layout.newshape={'line_color':'red','line_dash':'dash'}
fig.layout.clickmode='event+select'
#fig.layout.hovermode='closest'
#fig.layout.captureevents=True
fig.update_xaxes(fixedrange=True)
fig.update_yaxes(fixedrange=True)

zoom_fig = px.imshow(np.zeros(shape=(50,50)), origin='lower', zmin=zmin, zmax=zmax)
#zoom_fig["data"][0]["showscale"]=False
#zoom_fig["data"][0]["coloraxis"]=None
#zoom_fig["data"][0]["colorscale"]='gray'
zoom_fig.layout.coloraxis.showscale = False
zoom_fig.update_xaxes(fixedrange=True)
zoom_fig.update_yaxes(fixedrange=True)

cut = px.line(np.zeros(100))
spectrum = px.line(np.zeros(100))
tracetracker = px.scatter(x=[0],y=[0])
tracetracker.layout.clickmode='event+select'
tracetracker.layout.hovermode='closest'
sigmatracker = px.scatter(x=[0],y=[0])
