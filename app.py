"""
TrafficGuard Pro — Root Application Entrypoint & Compatibility Layer.
Exposes 'app' and delegates to backend.app so root commands, Docker, Render,
and Pytest run smoothly without path issues.
"""
import os
import sys

# Add backend directory to sys.path for seamless intra-module imports
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import backend.app and re-export symbols
import backend.app as _backend_app

for _attr in dir(_backend_app):
    if not _attr.startswith('__'):
        globals()[_attr] = getattr(_backend_app, _attr)

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port  = int(os.environ.get('PORT', 5001))
    _backend_app.app.run(debug=debug, threaded=True, host='0.0.0.0', port=port)

