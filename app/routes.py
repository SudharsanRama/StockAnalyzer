from flask import redirect, jsonify, request
from app import app
from math import sqrt
from sklearn.preprocessing import MinMaxScaler
from keras.models import Sequential
from keras.layers import Dense, Dropout, LSTM
from werkzeug.utils import secure_filename
import os, json
import pandas as pd
import numpy as np

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
    data['predicted'], data['rmse'] = DATA_FRAME.get_predicted(name)
    response = app.response_class(
        response=json.dumps(data, cls=NumpyEncoder),
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
        groups = stock.last('6M').groupby(pd.Grouper(freq='2W'))
        return get_stats(groups)

    def get_predicted(self,company):
        stock = self.df.loc[self.df['symbol'] == company]
        stock['timestamp'] = pd.to_datetime(stock.timestamp,format='%Y-%m-%d')
        stock.index = stock['timestamp']
        actual = stock.last('6M')['close'].tolist()
        data = stock.sort_index(ascending=True, axis=0)

        new_data = pd.DataFrame(index=range(0,len(self.df)),columns=['Date', 'close'])
        for i in range(0,len(data)):
            new_data['Date'][i] = data['timestamp'][i]
            new_data['close'][i] = data['close'][i]

        #setting index
        new_data.index = new_data.Date
        new_data.drop('Date', axis=1, inplace=True)

        #creating train and test sets
        dataset = new_data.values
        train_size = len(stock.first('18M'))
        train = dataset[0:train_size,:]
        valid = dataset[train_size:,:]

        #converting dataset into x_train and y_train
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(dataset)

        x_train, y_train = [], []
        for i in range(60,len(train)):
            x_train.append(scaled_data[i-60:i,0])
            y_train.append(scaled_data[i,0])
        x_train, y_train = np.array(x_train), np.array(y_train)

        x_train = np.reshape(x_train, (x_train.shape[0],x_train.shape[1],1))

        # create and fit the LSTM network
        model = Sequential()
        model.add(LSTM(units=50, return_sequences=True, input_shape=(x_train.shape[1],1)))
        model.add(LSTM(units=50))
        model.add(Dense(1))

        model.compile(loss='mean_squared_error', optimizer='adam')
        model.fit(x_train, y_train, epochs=1, batch_size=1, verbose=2)

        #predicting 246 values, using past 60 from the train data
        inputs = new_data[len(new_data) - len(valid) - 60:].values
        inputs = inputs.reshape(-1,1)
        inputs  = scaler.transform(inputs)

        X_test = []
        for i in range(60,inputs.shape[0]):
            X_test.append(inputs[i-60:i,0])
        X_test = np.array(X_test)

        X_test = np.reshape(X_test, (X_test.shape[0],X_test.shape[1],1))
        closing_price = model.predict(X_test)
        closing_price = scaler.inverse_transform(closing_price)
        
        valid = new_data[train_size:]
        valid['Predictions'] = closing_price
        valid = valid.dropna()

        current_df = stock.last('6M')
        current_df['close'] = valid.last('6M')['Predictions']

        rmse = round(rmse_metric(actual, current_df['close'].tolist()), 3)

        return get_stats(current_df.groupby(pd.Grouper(freq='2W'))), rmse

def rmse_metric(actual, predicted):
	sum_error = 0.0
	for i in range(len(actual)):
		prediction_error = predicted[i] - actual[i]
		sum_error += (prediction_error ** 2)
	mean_error = sum_error / float(len(actual))
	return sqrt(mean_error)

class NumpyEncoder(json.JSONEncoder):
    """ Special json encoder for numpy types """
    def default(self, obj):
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
            np.int16, np.int32, np.int64, np.uint8,
            np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, 
            np.float64)):
            return float(obj)
        elif isinstance(obj,(np.ndarray,)): #### This is the fix
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)
   