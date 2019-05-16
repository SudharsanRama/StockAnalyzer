from flask import redirect, jsonify, request
from app import app
from werkzeug.utils import secure_filename
import os, json
import pandas as pd

ALLOWED_EXTENSIONS = set(['csv'])
DATA_FRAME = None

@app.route('/')
@app.route('/index')
def index():
    return redirect("static/index.html")

@app.route('/upload', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return jsonify(None)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return jsonify(None)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filePath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filePath)
            global DATA_FRAME
            DATA_FRAME = DataFrame(filePath)
            return jsonify(DATA_FRAME.get_list())
    return jsonify(None)

@app.route('/details/<name>', methods=['GET'])
def get_details(name):
    global DATA_FRAME
    # return app.response_class(DATA_FRAME.get_description(name))
    # return DATA_FRAME.get_description(name)
    response = app.response_class(
        response=DATA_FRAME.get_description(name),
        status=200,
        mimetype='application/json'
    )
    return response

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class DataFrame:
    def __init__(self,filePath):
        self.filePath = filePath
        self.df = pd.read_csv(filePath)

    def get_list(self):
        return self.df['Name'].unique().tolist()

    def get_description(self,company):
        stock = self.df.loc[self.df['Name'] == company]
        return stock.to_json(orient='split')


   