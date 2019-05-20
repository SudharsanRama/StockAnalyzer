from flask import redirect, jsonify, request
from app import app
from app.linear_regression import simple_linear_regression
from werkzeug.utils import secure_filename
import os, json
import pandas as pd

ALLOWED_EXTENSIONS = set(['csv','xlsx'])
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
    data = {}
    data['actual'] = DATA_FRAME.get_description(name)
    data['predicted'] = DATA_FRAME.get_predicted(name)
    response = app.response_class(
        response=json.dumps(data),
        status=200,
        mimetype='application/json'
    )
    return response

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_stats(groups):
    starts, opens, highs, lows, close = [],[],[],[],[]
    for(month_start, sub_stock) in groups:
        starts.append(month_start.strftime('%d %b %Y %H:%M Z'))
        opens.append(sub_stock["open"].iloc[0])
        highs.append(sub_stock["high"].max())
        lows.append(sub_stock["low"].min())
        close.append(sub_stock["close"].iloc[-1])

    stats = [{"start": start, "open": open, "high": high, "low": low, "close": close} for start, open, high, low, close in zip(starts, opens, highs, lows, close)]
    return stats

class DataFrame:
    def __init__(self,filePath):
        self.filePath = filePath
        self.df = pd.read_excel(filePath, parse_dates=['timestamp'])

    def get_list(self):
        return self.df['symbol'].unique().tolist()

    def get_description(self,company):
        stock = self.df.loc[self.df['symbol'] == company].set_index('timestamp')
        g = stock.last('6M').groupby(pd.Grouper(freq='M'))
        return get_stats(g)

    def get_predicted(self,company):
        stock = self.df.loc[self.df['symbol'] == company].set_index('timestamp')
        dataset, test_set = [], []
        g = stock.first('18M')
        for index, row in g.iterrows():
            dataset.append([(row['high']+row['low'])/2, row['close']])
        g = stock.last('6M')
        for index, row in g.iterrows():
            test_set.append([(row['high']+row['low'])/2, 0])
        g['close'] = simple_linear_regression(dataset, test_set)
        return get_stats(g.groupby(pd.Grouper(freq='M')))


   