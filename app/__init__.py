from flask import Flask

UPLOAD_FOLDER = 'C:\\Temp\\'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

from app import routes