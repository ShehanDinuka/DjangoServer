from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import loader

from .models import User, Stock

import sys
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta
from sklearn.preprocessing import MinMaxScaler
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from keras.layers import Dropout
from keras.regularizers import L1L2
from keras import backend as K
from sklearn.externals import joblib  # save the model


# Using HttpResponse function
def user_details(request):
    # - show revers order
    latest_users = User.objects.order_by('-name')[:5]

    template = loader.get_template('stock/index.html')
    context = {
        'latest_users': latest_users,
    }
    return HttpResponse(template.render(context, request))


# def user_details(request):
#     # - show revers order
#     latest_users = User.objects.order_by('-name')[:5]
#     context = {
#         'latest_users': latest_users,
#     }
#     return render(request, 'stock/index.html', context)

def user_get_by_id(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    response = "User id : %s"
    return HttpResponse(response % user.name)

    # def user_get_by_id(request, user_id):
    #     try:
    #         user = User.objects.get(pk=user_id)
    #         response = "User id : %s"
    #     except User.DoesNotExist:
    #         raise Http404("User Does not exist")
    #     return HttpResponse(response % user.name)


def root_mean_squared_error(y_true, y_pred):
    return K.sqrt(K.mean(K.square(y_pred - y_true)))


# used to create model
def create_model(request):
    data_set = pd.read_csv(r'D:\testProjectDjango\products\formatted_128714.csv')
    copy = pd.read_csv(r'D:\testProjectDjango\products\formatted_128714.csv')
    dataset = data_set[['DATE', 'OP', 'CLS']]
    days = []

    for i in range(1773):
        s = str(dataset.loc[i, 'DATE'])
        # you could also import date instead of datetime and use that.
        date = datetime(year=int(s[0:4]), month=int(s[4:6]), day=int(s[6:8]))
        days.append(date.weekday())
        dataset.loc[i, 'DATE'] = date.date()

    dataset['DAY'] = days
    dataset = dataset[['DATE', 'DAY', 'CLS']]

    values = dataset.iloc[:, 1:4].values;
    values = values.astype('float32')

    # normalize features
    scaler = MinMaxScaler(feature_range=(0, 1))
    fit_transform_values = scaler.fit_transform(values)
    reframed = series_to_supervised(values, 4, 1)
    values = reframed.values
    train = values[:1400, :]
    val = values[1400:1525, :]
    test = values[1525:, :]

    # split into input and outputs
    train_X, train_y = train[:, :-1], train[:, -1]
    val_X, val_y = val[:, :-1], val[:, -1]
    test_X, test_y = test[:, :-1], test[:, -1]
    # reshape input to be 3D [samples, timesteps, features]
    train_X = train_X.reshape((train_X.shape[0], 1, train_X.shape[1]))
    val_X = val_X.reshape((val_X.shape[0], 1, val_X.shape[1]))
    test_X = test_X.reshape((test_X.shape[0], 1, test_X.shape[1]))
    model = Sequential()
    model.add(LSTM(units=128, return_sequences=True, input_shape=(train_X.shape[1], train_X.shape[2]),
                   bias_regularizer=L1L2(l1=0.001, l2=0.001)))
    model.add(Dropout(0.5))

    model.add(LSTM(units=64))
    model.add(Dropout(0.5))

    model.add(Dense(units=16, init='uniform', activation='relu'))

    model.add(Dense(units=1))
    model.compile(optimizer='adam', loss=root_mean_squared_error)
    history = model.fit(train_X, train_y, epochs=100, batch_size=50, validation_data=(val_X, val_y), verbose=2,
                        shuffle=False)
    joblib.dump(model, 'stock-pre.joblib')
    return HttpResponse('model creation completed')


# used to get model predictions
def run_model(request):
    model = joblib.load('stock-pre.joblib')

    ### has to check
    predictions = model.predict([[21, 1]])
    return HttpResponse('model value created')


def get_pre_model():
    model = joblib.load('stock-pre.joblib')
    return HttpResponse('model value created')


def send_stock(request, value):
    if (value != 10):
        return HttpResponse('sell')
    else:
        return HttpResponse('sell')


def series_to_supervised(data, n_in=1, n_out=1, dropnan=True):
    n_vars = 1 if type(data) is list else data.shape[1]
    df = pd.DataFrame(data)
    cols, names = list(), list()
    # input sequence (t-n, ... t-1)
    for i in range(n_in, 0, -1):
        cols.append(df.shift(i))
        names += [('var%d(t-%d)' % (j + 1, i)) for j in range(n_vars)]
    # forecast sequence (t, t+1, ... t+n)
    for i in range(0, n_out):
        cols.append(df.shift(-i))
        if i == 0:
            names += [('var%d(t)' % (j + 1)) for j in range(n_vars)]
        else:
            names += [('var%d(t+%d)' % (j + 1, i)) for j in range(n_vars)]
    # put it all together
    agg = pd.concat(cols, axis=1)
    agg.columns = names
    # drop rows with NaN values
    if dropnan:
        agg.dropna(inplace=True)
    return agg
