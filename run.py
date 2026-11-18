import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 60, flush=True)
    print("   FINDBACK — Smart Object Recovery Network", flush=True)
    print(f"   Server running at: http://127.0.0.1:{port}", flush=True)
    print("=" * 60, flush=True)
    app.run(host='127.0.0.1', port=port, debug=False)
