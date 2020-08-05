# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

# Third-party imports
import numpy as np
from itertools import chain
import pytest

# First-party imports
from gluonts.model.rotbaum import TreePredictor, TreeEstimator
from gluonts.evaluation import Evaluator
from gluonts.evaluation.backtest import backtest_metrics

# TODO: function.
# TODO: implement using accuracy_test like other gluonts models

# @pytest.fixture()
# def hyperparameters(dsinfo):
#     return dict(
#         context_length=2,
#         quantiles=[0.1, 0.5, 0.9],
#         num_workers=0,
#     )

# @pytest.mark.parametrize("quantiles", [[0.1, 0.5, 0.9], [0.5]])
# def test_accuracy(
#     accuracy_test, hyperparameters, quantiles
# ):
#     hyperparameters.update(
#         quantiles=quantiles, max_workers=32
#     )

#     accuracy_test(TreeEstimator, hyperparameters, accuracy=0.20)

def test_accuracy(accuracy_test, dsinfo):

    estimator = TreeEstimator(
        context_length=2,
        prediction_length=dsinfo["prediction_length"],
        freq=dsinfo["freq"],
    )
    predictor = estimator.train(dsinfo.train_ds)

    agg_metrics, item_metrics = backtest_metrics(
        test_dataset=dsinfo.test_ds,
        predictor=predictor,
        evaluator=Evaluator(quantiles=[0.1, 0.5, 0.9]),
    )

    if dsinfo["name"] == "constant":
        for q in [0.1, 0.5, 0.9]:
            assert agg_metrics[f"wQuantileLoss[{q}]"] == 0
    if dsinfo["name"] == "synthetic":
        assert 1.1 < agg_metrics[f"wQuantileLoss[0.5]"] < 1.2
        accuracy = 10.0
        assert agg_metrics["ND"] <= accuracy
