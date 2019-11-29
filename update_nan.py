
import numpy as np
import pandas as pd
import datetime as dt
import sys


def update_data_csv(filename, datafile, target_file):
    check = 'prev_settlement'
    pd_price = pd.read_csv(filename, index_col=[0])
    id_list = pd_price.index.tolist()
    id_list = list(set(id_list))

    pd_data = pd.read_csv(datafile)
    pd_data['date'] = pd_data['date'].apply(lambda x: dt.datetime.strptime(x, '%Y/%m/%d'))
    pd_data['date'] = pd_data['date'].apply(lambda x: dt.datetime.strftime(x, '%Y%m%d'))
    pd_data = pd_data.set_index('date')

    for i in id_list:
        t = target_file + '/' + str(i) + '_Day.csv'
        temp = pd.read_csv(t, index_col=[0])
        for d in pd_price['date'][i]:
            u_i = str(i) + '.SH'
            temp.at[d, check] = pd_data[u_i][str(d)]
        temp.to_csv(t)
        print(temp)
    return True


def read_hd5(filename):
    import h5py
    f1 = h5py.File(filename, 'r+')
    print(f1['10001333'][()])


if __name__ == '__main__':

    if len(sys.argv) != 4:
        raise EnvironmentError('4 arguments required')

    output = sys.argv[1]
    dataf = sys.argv[2]
    target = sys.argv[3]
    update_data_csv('output.csv', dataf, target)

    # read_hd5(r'C:\Users\rice\Desktop\etf_daybar\h5_data.h5')
