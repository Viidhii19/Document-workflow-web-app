import requests
data = requests.get('https://openrouter.ai/api/v1/models').json()['data']
free_models = [m['id'] for m in data if 'free' in m['id'].lower() and ('gemini' in m['id'].lower() or 'llama-3.3' in m['id'].lower())]
print("\n".join(free_models))
