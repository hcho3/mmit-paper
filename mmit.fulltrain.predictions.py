"""

"""
import cPickle
import json
import numpy as np
import pandas as pd

from mmit import MaxMarginIntervalTree
from mmit.metrics import mean_squared_error
from mmit.model_selection import GridSearchCV
from os import listdir, mkdir, system
from os.path import abspath, basename, exists, join
from sklearn.model_selection import KFold


class Dataset(object):
    def __init__(self, path):
        self.path = path
        feature_data = pd.read_csv(join(path, "features.csv"))
        self.X = feature_data.values.astype(np.float)
        self.X.flags.writeable = False
        self.feature_names = feature_data.columns.values
        self.feature_names.flags.writeable = False
        del feature_data
        self.y = pd.read_csv(join(path, "targets.csv")).values.astype(np.float)
        self.y.flags.writeable = False
        self.folds = pd.read_csv(join(path, "folds.csv")).values.reshape(-1, )
        self.folds.flags.writeable = False
        self.name = basename(path)

    @property
    def n_examples(self):
        return self.X.shape[0]

    @property
    def n_features(self):
        return self.X.shape[1]

    def __hash__(self):
        return hash((self.X.data, self.y.data, self.feature_names.data, self.folds.data))


def find_datasets(path):
    for d in listdir(path):
        if exists(join(path, d, "features.csv")) and \
                exists(join(path, d, "targets.csv")) and \
                exists(join(path, d, "folds.csv")):
            yield Dataset(abspath(join(path, d)))


def mse_scorer(estimator, X, y):
    """
    Negative mean squared error, since GridSearchCV maximizes a metric
    """
    return -mean_squared_error(y_pred=estimator.predict(X), y_true=y)


def save_predictions(estimator, method, dataset, predictions_path):
    open(join(predictions_path, method, dataset.name, "predictions.fulltrain.csv"), "w")\
        .write("pred.log.penalty\n" + "\n".join(str(p) for p in estimator.predict(dataset.X)))
    print estimator
    # cPickle.dump(estimator.get_params(), open(join(predictions_path, method, dataset.name, "parameters.fulltrain.json"), "w"))


if __name__ == "__main__":
    predictions_path = "./predictions"
    n_cpu = 4
    n_margin_values = 20
    param_template = {"max_depth": [30],
                      "min_samples_split": [2],
                      "random_state": [42]}

    datasets = list(find_datasets("./data"))
    # We are just interested in the simulated datasets for this experiment
    datasets = [d for d in datasets if "simulated." in d.name]

    for i, d in enumerate(datasets):
        print "{0:d}/{1:d}: {2!s}".format(i + 1, len(datasets), d.name)

        # Determine the margin grid
        sorted_limits = d.y.flatten().astype(np.float)
        sorted_limits = sorted_limits[~np.isinf(sorted_limits)]
        sorted_limits.sort()
        range_max = sorted_limits.max() - sorted_limits.min()
        range_min = np.diff(sorted_limits)
        range_min = range_min[range_min > 0].min()
        param_template["margin"] = [0.] + np.logspace(np.log10(range_min), np.log10(range_max), n_margin_values).tolist()

        print ".... linear hinge"
        method = "mmit.linear.hinge.pruning"
        params = dict(param_template)
        params["loss"] = ["linear_hinge"]
        if not exists(join(predictions_path, method, d.name)) or \
                not exists(join(predictions_path, method, d.name, "predictions.fulltrain.csv")):
            try:
                mkdir(join(predictions_path, method, d.name))
            except:
                pass
            cv_protocol = KFold(n_splits=10, shuffle=True, random_state=42)
            cv = GridSearchCV(estimator=MaxMarginIntervalTree(), param_grid=params,
                              cv=cv_protocol, n_jobs=n_cpu, scoring=mse_scorer,
                              pruning=True).fit(d.X, d.y)

            for hps, metrics in cv.cv_results_:
                print hps, metrics["cv"]

            print "BEST:"
            print cv.best_estimator_
            print cv.best_params_
            print cv.best_score_

            save_predictions(cv.best_estimator_, method, d, predictions_path)

        print ".... squared hinge"
        method = "mmit.squared.hinge.pruning"
        params = dict(param_template)
        params["loss"] = ["squared_hinge"]
        if not exists(join(predictions_path, method, d.name)) or \
                not exists(join(predictions_path, method, d.name, "predictions.fulltrain.csv")):
            try:
                mkdir(join(predictions_path, method, d.name))
            except:
                pass
            cv_protocol = KFold(n_splits=10, shuffle=True, random_state=42)
            cv = GridSearchCV(estimator=MaxMarginIntervalTree(), param_grid=params,
                              cv=cv_protocol, n_jobs=n_cpu, scoring=mse_scorer,
                              pruning=True).fit(d.X, d.y)
            save_predictions(cv.best_estimator_, method, d, predictions_path)
            print "BEST:"
            print cv.best_estimator_
            print cv.best_params_
            print cv.best_score_
