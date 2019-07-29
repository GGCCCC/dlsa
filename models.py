import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
import warnings

def simulate_logistic(sample_size, p, partition_method, partition_num):
    '''Simulate data based on logistic model

    '''
    ## Simulate Data
    n = sample_size
    p1 = int(p * 0.4)

    # partition_method = "systematic"
    # partition_num = 200

    ## TRUE beta
    beta = np.zeros(p).reshape(p, 1)
    beta[:p1] = 1

    ## Simulate features
    features = np.random.rand(n, p) - 0.5
    prob = 1 / (1 + np.exp(-features.dot(beta)))

    ## Simulate label
    label = np.zeros(n).reshape(n, 1)
    partition_id = np.zeros(n).reshape(n, 1)
    for i in range(n):
        # TODO: REMOVE loop
        label[i] = np.random.binomial(n=1,p=prob[i], size=1)

        if partition_method == "systematic":
            partition_id[i] = i % partition_num
        else:
            raise Exception("No such partition method implemented!")

        data_np = np.concatenate((partition_id, label, features), 1)
        data_pdf = pd.DataFrame(data_np, columns=["partition_id"] + ["label"] + ["x" + str(x) for x in range(p)])

    return data_pdf

def logistic_model(sample_df, Y_name, fit_intercept=False, dummy_info=[], data_info=[]):
    '''Run logistic model on the partitioned data set

    '''

    # x_train = sample_df.drop(['label', 'row_id', 'partition_id'], axis=1)
    # sample_df = samle_df.dropna()

    # Special step to create a local dummy matrix
    if len(dummy_info) > 0:
        convert_dummies = list(dummy_info['factor_selected'].keys())

        X_with_dummies = pd.get_dummies(data=sample_df,
                                        drop_first=fit_intercept,
                                        columns=convert_dummies,
                                        sparse=True)

        x_train = X_with_dummies.drop(['partition_id', Y_name], axis = 1)

        # Check if any dummy column is not in the data chunk.
        usecols_x0 = list(set(sample_df.columns.drop(['partition_id', Y_name])) - set(convert_dummies))
        usecols_x = usecols_x0.copy()
        for i in convert_dummies:
            for j in dummy_info["factor_selected_names"][i][fit_intercept:]:
                usecols_x.append(j)
        usecols_x.sort()
        usecols_full = ['par_id', "coef", "Sig_invMcoef"]
        usecols_full.extend(usecols_x)

        # raise Exception("usecols_full:\t" + str(len(usecols_full)))
        # raise Exception("usecols_x:\t" + str(usecols_x))

        if set(x_train.columns) != set(usecols_x):
            warnings.warn("Dummies:" + str(set(usecols_x) - set(x_train.columns))
                          + "missing in this data chunk " + str(x_train.shape)
                          + "Skip modeling this part of data.")

            # return a zero fake matrix.
            return pd.DataFrame(0,index=np.arange(len(usecols_x)),
                                columns=usecols_full)

    else:
        x_train = sample_df.drop(['partition_id', Y_name], axis=1)
        usecols_x0 = x_train.columns

    # Standardize the data with global mean and variance
    if len(data_info) > 0:
        for i in usecols_x0:
            x_train[i]=(x_train[i] - float(data_info[i][1])) / float(data_info[i][2])


    x_train.sort_index(axis=1, inplace=True)

    # raise Exception("x_train shape:" + str(list(x_train.columns)))

    y_train = sample_df[Y_name]

    model = LogisticRegression(solver="lbfgs", penalty="none", fit_intercept=fit_intercept)
    model.fit(x_train, y_train)
    prob = model.predict_proba(x_train)[:, 0]
    p = model.coef_.size

    coef = model.coef_.reshape(p, 1) # p-by-1
    Sig_inv = x_train.T.dot(np.multiply((prob*(1-prob))[:,None],x_train)) # p-by-p
    Sig_invMcoef = Sig_inv.dot(coef) # p-by-1

    # grad = np.dot(x_train.T, y_train - prob)

    # Assign par_id
    par_id = pd.DataFrame(np.arange(p).reshape(p, 1), columns=['par_id'])
    # par_id = pd.DataFrame(x_train.columns.to_numpy().reshape(p, 1), columns=["par_id"])

    out_np = np.concatenate((coef, Sig_invMcoef, Sig_inv),1) # p-by-(3+p)
    out_pdf = pd.DataFrame(out_np,
                           columns=pd.Index(["coef", "Sig_invMcoef"] + x_train.columns.tolist()))
    out = pd.concat([par_id, out_pdf],1)

    if out.isna().values.any():
        warnings.warn("NAs appear in the final output")

    return out
    # return pd.DataFrame(Sig_inv)
