from dash import Dash, dcc, html
import os

# Initialize Dash app
app = Dash(__name__)
server = app.server  # This is used by Gunicorn/Render

# App layout
app.layout = html.Div(children=[
    html.H1('Hello World!')
])

# Run the server
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))  # Default to 8050 locally
    app.run(host='0.0.0.0', port=port, debug=False)
