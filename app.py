import os
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate

# 🔹 Initialize Dash app (like Express initializes app)
app = Dash(__name__)
server = app.server  # This is what gunicorn will use

# 🔹 Configure file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 🔹 Load tree data
df = pd.read_csv(os.path.join(BASE_DIR, 'arvores-tombadas.csv'), sep=';')

# 🔹 Load tree census data
censo_dir = os.path.join(BASE_DIR, "censo-partes")
censo_files = [f for f in os.listdir(censo_dir) if f.endswith(".geojson")]
censo_paths = sorted([os.path.join(censo_dir, f) for f in censo_files])

gdf_list = []
for i, path in enumerate(censo_paths):
    gdf = gpd.read_file(path)
    if 'id' in gdf.columns:
        gdf['id'] = f"{i}_" + gdf['id'].astype(str)
    elif 'ID' in gdf.columns:
        gdf['ID'] = f"{i}_" + gdf['ID'].astype(str)
    else:
        gdf['id'] = [f"{i}_{x}" for x in range(len(gdf))]
    gdf = gdf.dropna(axis=1, how='all')
    if not gdf.empty:
        gdf_list.append(gdf)

if gdf_list:
    gdf_censo = pd.concat(gdf_list, ignore_index=True)
    gdf_censo = gdf_censo.to_crs(epsg=4326)
    gdf_censo["longitude"] = gdf_censo.geometry.x
    gdf_censo["latitude"] = gdf_censo.geometry.y
else:
    gdf_censo = gpd.GeoDataFrame(columns=['nome_popul', 'geometry'], geometry='geometry')
    gdf_censo = gdf_censo.to_crs(epsg=4326)
    gdf_censo["longitude"] = []
    gdf_censo["latitude"] = []

# 🔹 Load conservation units
gdf_ucn = gpd.read_file(os.path.join(BASE_DIR, 'unidadesconservacaonatureza-ucn.geojson'))
gdf_ucn = gdf_ucn.to_crs(epsg=4326)
gdf_ucn['geometry'] = gdf_ucn['geometry'].simplify(0.001)

# 🔹 Process species data
especies_tombadas = df['nome_popular'].dropna().unique().tolist()
especies_censo = gdf_censo['nome_popul'].dropna().unique().tolist()

unique_species = set()
species_list = []
for especie in especies_tombadas + especies_censo:
    lower_especie = especie.lower()
    if lower_especie not in unique_species:
        unique_species.add(lower_especie)
        species_list.append(especie)

lista_especies = sorted(species_list, key=lambda x: x.lower())
especies_options = [
    {'label': f"{especie} 🌳" if especie in especies_tombadas else especie, 'value': especie}
    for especie in lista_especies
]

# 🔹 Map configuration
choropleth_ucn_trace = go.Choroplethmapbox(
    geojson=gdf_ucn.__geo_interface__,
    locations=gdf_ucn.index,
    z=[1] * len(gdf_ucn),
    colorscale=[[0, 'rgba(34, 139, 34, 0.15)'], [1, 'rgba(34, 139, 34, 0.15)']],
    showscale=False,
    name="Áreas de Conservação",
    hovertext=gdf_ucn['CDZONA_NOME'],
    hoverinfo='text',
    marker_line_width=1.2,
    marker_line_color='rgba(10, 80, 10, 0.8)',
    visible=True,
    legendgroup="conservation",
    showlegend=True
)

map_layout = go.Layout(
    mapbox_style="open-street-map",
    mapbox_zoom=11,
    mapbox_center={"lat": -8.05, "lon": -34.9},
    height=700,
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    legend=dict(
        title="Legenda:",
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01,
        bgcolor='rgba(255, 255, 255, 0.7)',
        font=dict(size=12)
    ),
    hovermode='closest'
)

initial_map_figure = go.Figure(
    data=[choropleth_ucn_trace],
    layout=map_layout
)

# 🔹 Charts
species_counts = df['nome_popular'].value_counts().reset_index()
species_counts.columns = ['nome_popular', 'count']

barras = px.bar(
    species_counts,
    x='nome_popular',
    y='count',
    labels={'nome_popular': 'Espécie', 'count': 'Frequência'},
    title="📊 Espécies Mais Frequentes"
)

pizza = px.pie(
    df,
    names='familia',
    title="🧬 Distribuição por Família",
    hole=0.4
)

# 🔹 App Layout
app.layout = html.Div(children=[
    html.Header("🌳 Dashboard de Arborização Urbana - Recife", className="header"),
    html.Div([
        html.Div([
            html.H3("🗺️ Mapa Integrado: Árvores Tombadas, Censo Arbóreo e Áreas de Conservação"),
            html.Div([
                html.Button('Mostrar/Ocultar Áreas de Conservação', id='toggle-ucn-button'),
                html.Button('Marcar Todas', id='select-all-button'),
                html.Button('Desmarcar Todas', id='deselect-all-button'),
                dcc.Input(
                    id='filtro-nome-arvore',
                    type='text',
                    placeholder='Buscar por nome popular...',
                    debounce=True,
                    style={'width': '300px'}
                )
            ], style={'display': 'flex', 'alignItems': 'center', 'gap': '10px', 'marginBottom': '10px'}),
            dcc.Graph(id='mapa-integrado-graph', figure=initial_map_figure)
        ], className="card", style={'width': '75%'}),
        html.Div([
            html.H4("🌳 Filtrar por Espécies"),
            dcc.Checklist(
                id='filtro-especie',
                options=especies_options,
                value=[],
                inputStyle={"margin-right": "5px"},
                style={'height': '700px', 'overflowY': 'auto'}
            )
        ], className="card", style={'width': '25%'}),
    ], style={'display': 'flex'}),
    html.Div([
        html.Div([html.H3("📊 Espécies Mais Frequentes"), dcc.Graph(figure=barras)], className="card"),
        html.Div([html.H3("🧬 Distribuição por Família"), dcc.Graph(figure=pizza)], className="card")
    ], className="content"),
    html.Footer("© 2025 - Desenvolvido por Seu Nome • Dados: Prefeitura do Recife", className="footer")
])

# 🔹 Callbacks
@app.callback(
    Output('mapa-integrado-graph', 'figure'),
    Output('filtro-especie', 'value'),
    [
        Input('filtro-nome-arvore', 'value'),
        Input('filtro-especie', 'value'),
        Input('toggle-ucn-button', 'n_clicks'),
        Input('select-all-button', 'n_clicks'),
        Input('deselect-all-button', 'n_clicks')
    ],
    [State('mapa-integrado-graph', 'figure'),
     State('filtro-especie', 'options')]
)
def update_mapa(search_term, selected_species, ucn_clicks, select_all, deselect_all, current_figure, species_options):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'toggle-ucn-button':
        current_figure['data'][0]['visible'] = not current_figure['data'][0]['visible']
        return current_figure, selected_species

    if trigger_id == 'select-all-button':
        selected_species = [option['value'] for option in species_options]
    elif trigger_id == 'deselect-all-button':
        selected_species = []

    ucn_visible = current_figure['data'][0]['visible']
    active_traces = []

    active_traces.append(go.Choroplethmapbox(
        geojson=gdf_ucn.__geo_interface__,
        locations=gdf_ucn.index,
        z=[1] * len(gdf_ucn),
        colorscale=[[0, 'rgba(34, 139, 34, 0.15)'], [1, 'rgba(34, 139, 34, 0.15)']],
        showscale=False,
        name="Áreas de Conservação",
        hovertext=gdf_ucn['CDZONA_NOME'],
        hoverinfo='text',
        marker_line_width=1.2,
        marker_line_color='rgba(10, 80, 10, 0.8)',
        visible=ucn_visible,
        legendgroup="conservation",
        showlegend=True
    ))

    df_filtered = df
    gdf_filtered = gdf_censo

    if search_term:
        st = search_term.strip().lower()
        df_filtered = df[df['nome_popular'].str.lower().str.contains(st, na=False)]
        gdf_filtered = gdf_censo[gdf_censo['nome_popul'].str.lower().str.contains(st, na=False)]

    if selected_species:
        df_filtered = df_filtered[df_filtered['nome_popular'].isin(selected_species)]
        gdf_filtered = gdf_filtered[gdf_filtered['nome_popul'].isin(selected_species)]

    if not df_filtered.empty:
        active_traces.append(go.Scattermapbox(
            lat=df_filtered['latitude'],
            lon=df_filtered['longitude'],
            mode='markers',
            marker=go.scattermapbox.Marker(size=9, color='darkgreen'),
            name="Árvores Tombadas",
            text=df_filtered['nome_popular'],
            hoverinfo='text',
            legendgroup="tombadas"
        ))

    if not gdf_filtered.empty:
        active_traces.append(go.Scattermapbox(
            lat=gdf_filtered['latitude'],
            lon=gdf_filtered['longitude'],
            mode='markers',
            marker=go.scattermapbox.Marker(size=7, color='blue'),
            name="Censo Arbóreo",
            text=gdf_filtered['nome_popul'],
            hoverinfo='text',
            legendgroup="censo"
        ))

    new_fig = go.Figure(data=active_traces, layout=map_layout)
    return new_fig, selected_species


# 🔹 Run server (like app.listen() in Express)
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))  # Default to 8050 locally
    app.run(host='0.0.0.0', port=port, debug=False)