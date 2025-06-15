from flask import Flask, jsonify, request
import requests
import csv
import os
from datetime import datetime
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)

LOG_FILE = os.environ.get('LOG_FILE', 'pokemon_queries.csv')
POKEAPI_BASE_URL = os.environ.get('POKEAPI_BASE_URL', 'https://pokeapi.co/api/v2/pokemon/')

if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['timestamp', 'query_type', 'query_value'])

def log_query(query_type, value):
    with open(LOG_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.utcnow().isoformat(), query_type, value])

@app.route('/pokemon', methods=['GET'])
@metrics.counter(
    'pokemon_api_requests_total',
    'Total number of Pokémon API requests',
    labels={'by': lambda: request.args.get('id') and 'id' or (request.args.get('name') and 'name' or 'none')}
)
def get_pokemon():
    pokemon_id = request.args.get('id')
    pokemon_name = request.args.get('name')

    if not pokemon_id and not pokemon_name:
        return jsonify({'error': 'Please provide either an id or a name'}), 400

    # Prefer id over name if both are present
    if pokemon_id:
        query_type = 'id'
        query_value = pokemon_id
    else:
        if pokemon_name.isdigit():
            return jsonify({'error': 'Numeric values should be passed using the "id" parameter, not "name"'}), 400
        query_type = 'name'
        query_value = pokemon_name

    log_query(query_type, query_value)

    response = requests.get(f"{POKEAPI_BASE_URL}{query_value.lower()}")
    if response.status_code != 200:
        return jsonify({'error': 'Pokemon not found'}), 404

    data = response.json()

    base_stats = {}
    for stat in data['stats']:
        stat_name = stat['stat']['name']
        base_stats[stat_name] = stat['base_stat']

    result = {
        'name': data['name'],
        'url': f"{POKEAPI_BASE_URL}{data['id']}/",
        'base_stats': {
            'hp': base_stats.get('hp'),
            'attack': base_stats.get('attack'),
            'defense': base_stats.get('defense'),
            'special-attack': base_stats.get('special-attack'),
            'special-defense': base_stats.get('special-defense'),
            'speed': base_stats.get('speed')
        }
    }

    return jsonify(result)


if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    app.run(host=host, port=port)
