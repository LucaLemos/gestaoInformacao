import os
import gdown
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate

# URL and output filename for the GeoJSON on Google Drive
GEOJSON_URL = 'https://drive.google.com/uc?id=11jh8IdxdiMG1AffVKtmkeNSbA0FkEHFn'
GEOJSON_FILE = 'censo_arboreo.geojson'

# Download censo_arboreo.geojson if not already downloaded
if not os.path.exists(GEOJSON_FILE):
    print(f"Downloading {GEOJSON_FILE} from Google Drive...")
    gdown.download(GEOJSON_URL, GEOJSON_FILE, quiet=False)
else:
    print(f"{GEOJSON_FILE} already exists. Using local copy.")

# 🔹 Ler dados das árvores tombadas
df = pd.read_csv('arvores-tombadas.csv', sep=';')

# 🔹 Ler o GeoJSON do censo arbóreo
gdf_censo = gpd.read_file(GEOJSON_FILE)
gdf_censo = gdf_censo.to_crs(epsg=4326)
gdf_censo['longitude'] = gdf_censo.geometry.x
gdf_censo['latitude'] = gdf_censo.geometry.y

# 🔹 Ler o GeoJSON das Unidades de Conservação da Natureza
gdf_ucn = gpd.read_file('unidadesconservacaonatureza-ucn.geojson')
gdf_ucn = gdf_ucn.to_crs(epsg=4326)
gdf_ucn['geometry'] = gdf_ucn['geometry'].simplify(0.001)

# 🔸 Obter lista única de espécies (sem duplicatas e marcando as tombadas)
especies_tombadas = df['nome_popular'].dropna().unique().tolist()
especies_censo = gdf_censo['nome_popul'].dropna().unique().tolist()

# Criar lista única sem duplicatas (case insensitive)
unique_species = set()
species_list = []
for especie in especies_tombadas + especies_censo:
    lower_especie = especie.lower()
    if lower_especie not in unique_species:
        unique_species.add(lower_especie)
        species_list.append(especie)

# Marcar espécies tombadas
lista_especies = sorted(species_list, key=lambda x: x.lower())
especies_options = []
for especie in lista_especies:
    is_tombada = especie in especies_tombadas
    label = f"{especie} 🌳" if is_tombada else especie
    especies_options.append({'label': label, 'value': especie})

# 🔸 Traço das Áreas de Conservação
choropleth_ucn_trace = go.Choroplethmapbox(
    geojson=gdf_ucn.__geo_interface__,
    locations=gdf_ucn.index,
    z=[1]*len(gdf_ucn),
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

# 🔸 Layout do mapa com configurações de legenda
map_layout = go.Layout(
    mapbox_style="open-street-map",
    mapbox_zoom=11,
    mapbox_center={"lat": -8.05, "lon": -34.9},
    height=700,
    margin={"r":0, "t":0, "l":0, "b":0},
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

# 🔸 Figura inicial do mapa (apenas com áreas de conservação)
initial_map_figure = go.Figure(
    data=[choropleth_ucn_trace],
    layout=map_layout
)
initial_map_figure.update_layout(
    legend=dict(
        itemsizing='constant',
        traceorder='normal'
    )
)

# 🔸 Gráfico de barras
species_counts = df['nome_popular'].value_counts().reset_index()
species_counts.columns = ['nome_popular', 'count']
barras = px.bar(
    species_counts,
    x='nome_popular',
    y='count',
    labels={'nome_popular': 'Espécie', 'count': 'Frequência'},
    title="📊 Espécies Mais Frequentes"
)

# 🔸 Gráfico de pizza
pizza = px.pie(
    df,
    names='familia',
    title="🧬 Distribuição por Família",
    hole=0.4
)

# 🔸 Iniciar o app
app = Dash(__name__)
server = app.server

app.layout = html.Div(children=[
    html.Header("🌳 Dashboard de Arborização Urbana - Recife", className="header"),

    html.Div([
        html.Div([
            html.H3("🗺️ Mapa Integrado: Árvores Tombadas, Censo Arbóreo e Áreas de Conservação"),

            html.Div([
                html.Button(
                    'Mostrar/Ocultar Áreas de Conservação',
                    id='toggle-ucn-button',
                    style={'marginRight': '20px'}
                ),

                html.Div([
                    html.Button(
                        'Marcar Todas',
                        id='select-all-button',
                        style={'marginRight': '10px'}
                    ),
                    html.Button(
                        'Desmarcar Todas',
                        id='deselect-all-button',
                        style={'marginRight': '20px'}
                    ),
                ]),

                dcc.Input(
                    id='filtro-nome-arvore',
                    type='text',
                    placeholder='Buscar por nome popular...',
                    debounce=True,
                    style={'width': '300px'}
                )
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px', 'marginLeft': '10px'}),

            dcc.Graph(id='mapa-integrado-graph', figure=initial_map_figure)
        ], className="card", style={'width': '75%', 'padding': '10px'}),

        html.Div([
            html.H4("🌳 Filtrar por Espécies"),
            dcc.Checklist(
                id='filtro-especie',
                options=especies_options,
                value=[],
                inputStyle={"margin-right": "5px"},
                style={'height': '700px', 'overflowY': 'auto'}
            )
        ], className="card", style={'width': '25%', 'padding': '10px'}),

    ], style={'display': 'flex'}),

    html.Div([
        html.Div([
            html.H3("📊 Espécies Mais Frequentes"),
            dcc.Graph(figure=barras)
        ], className="card"),

        html.Div([
            html.H3("🧬 Distribuição por Família"),
            dcc.Graph(figure=pizza)
        ], className="card")
    ], className="content"),

    html.Footer("© 2025 - Desenvolvido por Seu Nome • Dados: Prefeitura do Recife", className="footer")
])

# 🔸 Callback para atualizar o mapa
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
def update_mapa_camadas(search_term, selected_species, ucn_clicks, select_all, deselect_all, current_figure, species_options):
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

    # Sempre mostrar áreas de conservação (se visível)
    active_traces.append(go.Choroplethmapbox(
        geojson=gdf_ucn.__geo_interface__,
        locations=gdf_ucn.index,
        z=[1]*len(gdf_ucn),
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

    # Filtro das árvores tombadas com base na pesquisa textual
    df_filtered = df
    if search_term and search_term.strip() != '':
        df_filtered = df[df['nome_popular'].str.contains(search_term.strip(), case=False, na=False)]

    # Filtrar pelo checklist de espécies selecionadas
    if selected_species:
        df_filtered = df_filtered[df_filtered['nome_popular'].isin(selected_species)]

    # Adicionar pontos das árvores tombadas ao mapa
    if not df_filtered.empty:
        active_traces.append(go.Scattermapbox(
            lat=df_filtered['latitude'],
            lon=df_filtered['longitude'],
            mode='markers',
            marker=dict(size=9, color='forestgreen'),
            name="Árvores Tombadas",
            text=df_filtered['nome_popular'],
            hoverinfo='text',
            legendgroup="tombadas",
            showlegend=True
        ))

    # Filtrar censo arbóreo por espécies selecionadas (ou todas se nada selecionado)
    gdf_filtered = gdf_censo
    if selected_species:
        mask = gdf_filtered['nome_popul'].isin(selected_species)
        gdf_filtered = gdf_filtered[mask]

    # Adicionar pontos do censo arbóreo
    if not gdf_filtered.empty:
        active_traces.append(go.Scattermapbox(
            lat=gdf_filtered['latitude'],
            lon=gdf_filtered['longitude'],
            mode='markers',
            marker=dict(size=6, color='orange'),
            name="Censo Arbóreo",
            text=gdf_filtered['nome_popul'],
            hoverinfo='text',
            legendgroup="censo",
            showlegend=True
        ))

    # Atualizar layout do mapa
    current_figure['data'] = active_traces

    return current_figure, selected_species


if __name__ == '__main__':
    app.run(debug=True)
