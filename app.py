import os
from modules.ia_memoria.google_calendar import load_dotenv
load_dotenv()

from flask import Flask

from modules.ia_memoria.database import init_db
from modules.geral.routes import geral_bp
from modules.financas.routes import financas_bp
from modules.calendario.routes import calendario_bp
from modules.todo_gamer.routes import todo_gamer_bp
from modules.ia_memoria.routes import ia_memoria_bp

app = Flask(__name__)

# Register modular blueprints
app.register_blueprint(geral_bp)
app.register_blueprint(financas_bp)
app.register_blueprint(calendario_bp)
app.register_blueprint(todo_gamer_bp)
app.register_blueprint(ia_memoria_bp)

if __name__ == '__main__':
    # Initialize SQLite database
    init_db()
    
    # Start the server on port 5000. host='0.0.0.0' allows access from other devices in the local network!
    print("Iniciando Dashboard Familiar no NVMe local...")
    app.run(host='0.0.0.0', port=5000, debug=True)
