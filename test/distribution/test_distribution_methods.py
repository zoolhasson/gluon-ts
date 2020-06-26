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
import mxnet as mx
import numpy as np
import pytest

# First-party imports
from gluonts.mx.distribution import (
    Uniform,
    StudentT,
    NegativeBinomial,
    Laplace,
    Gaussian,
    Gamma,
    Beta,
    MultivariateGaussian,
    PiecewiseLinear,
    Poisson,
    Binned,
    TransformedDistribution,
    Categorical,
)

from gluonts.core.serde import load_json, dump_json

test_cases = [
    (
        Gaussian,
        {
            "mu": mx.nd.array([1000.0, -1000.0]),
            "sigma": mx.nd.array([0.1, 1.0]),
        },
    ),
    (
        Gamma,
        {"alpha": mx.nd.array([2.5, 7.0]), "beta": mx.nd.array([1.5, 2.1])},
    ),
    (
        Beta,
        {"alpha": mx.nd.array([2.5, 7.0]), "beta": mx.nd.array([1.5, 2.1])},
    ),
    (
        Laplace,
        {"mu": mx.nd.array([1000.0, -1000.0]), "b": mx.nd.array([0.1, 1.0])},
    ),
    (
        StudentT,
        {
            "mu": mx.nd.array([1000.0, -1000.0]),
            "sigma": mx.nd.array([1.0, 2.0]),
            "nu": mx.nd.array([4.2, 3.0]),
        },
    ),
    (
        NegativeBinomial,
        {"mu": mx.nd.array([1000.0, 1.0]), "alpha": mx.nd.array([1.0, 2.0])},
    ),
    (
        Uniform,
        {
            "low": mx.nd.array([1000.0, -1000.1]),
            "high": mx.nd.array([2000.0, -1000.0]),
        },
    ),
    (
        Binned,
        {
            "bin_log_probs": mx.nd.array(
                [[1e-300, 0.3, 0.1, 0.05, 0.2, 0.1, 0.25]]
            )
            .log()
            .repeat(axis=0, repeats=2),
            "bin_centers": mx.nd.array(
                [[-5, -3, -1.2, -0.5, 0, 0.1, 0.2]]
            ).repeat(axis=0, repeats=2),
        },
    ),
    (
        Binned,
        {
            "bin_log_probs": mx.nd.array(
                [[1e-300, 0.3, 0.1, 0.05, 0.2, 0.1, 0.25]]
            )
            .log()
            .repeat(axis=0, repeats=2),
            "bin_centers": mx.nd.array(
                [[-5, -3, -1.2, -0.5, 0, 0.1, 0.2]]
            ).repeat(axis=0, repeats=2),
            "label_smoothing": 0.1,
        },
    ),
    (
        Categorical,
        {
            "log_probs": mx.nd.array(
                [[1e-300, 0.3, 0.1, 0.05, 0.2, 0.1, 0.25]]
            )
            .log()
            .repeat(axis=0, repeats=2),
        },
    ),
    (Poisson, {"rate": mx.nd.array([1000.0, 1.0])}),
]

test_output = {
    "Gaussian": {
        "mean": mx.nd.array([1000.0, -1000.0]),
        "stddev": mx.nd.array([0.1, 1.0]),
        "variance": mx.nd.array([0.01, 1.0]),
    },
    "Beta": {
        "mean": mx.nd.array([0.625, 0.7692307]),
        "stddev": mx.nd.array([0.2165063, 0.1325734]),
        "variance": mx.nd.array([0.046875, 0.0175757]),
    },
    "Gamma": {
        "mean": mx.nd.array([1.6666666, 3.3333333]),
        "stddev": mx.nd.array([1.05409255, 1.25988158]),
        "variance": mx.nd.array([1.1111111, 1.58730159]),
    },
    "Laplace": {
        "mean": mx.nd.array([1000.0, -1000.0]),
        "stddev": mx.nd.array([0.14142136, 1.4142135]),
        "variance": mx.nd.array([0.02, 1.9999999]),
    },
    "StudentT": {
        "mean": mx.nd.array([1000.0, -1000.0]),
        "stddev": mx.nd.array([1.3816986, 3.4641016]),
        "variance": mx.nd.array([1.909091, 12.0]),
    },
    "NegativeBinomial": {
        "mean": mx.nd.array([1000.0, 1.0]),
        "stddev": mx.nd.array([1000.4999, 1.7320508]),
        "variance": mx.nd.array([1.001e06, 3.000e00]),
    },
    "Uniform": {
        "mean": mx.nd.array([1500.0, -1000.05]),
        "stddev": mx.nd.array([2.8867514e02, 2.8860467e-02]),
        "variance": mx.nd.array([8.3333336e04, 8.3292654e-04]),
    },
    "Binned": {
        "mean": mx.nd.array([-0.985, -0.985]),
        "stddev": mx.nd.array([1.377416, 1.377416]),
        "variance": mx.nd.array([1.8972749, 1.8972749]),
    },
    "Categorical": {
        "mean": mx.nd.array([3.45, 3.45]),
        "stddev": mx.nd.array([1.9868319, 1.9868319]),
        "variance": mx.nd.array([3.947501, 3.947501]),
    },
    "Poisson": {
        "mean": mx.nd.array([1000.0, 1.0]),
        "stddev": mx.nd.array([31.622776, 1.0]),
        "variance": mx.nd.array([1000.0, 1.0]),
    },
}

# TODO: implement stddev methods for MultivariateGaussian and LowrankMultivariateGaussian
DISTRIBUTIONS = [
    Gaussian,
    Laplace,
    StudentT,
    Gamma,
    NegativeBinomial,
    Uniform,
    Binned,
    Poisson,
]


serialize_fn_list = [lambda x: x, lambda x: load_json(dump_json(x))]


@pytest.mark.parametrize("distr_class, params", test_cases)
@pytest.mark.parametrize("serialize_fn", serialize_fn_list)
def test_means(distr_class, params, serialize_fn) -> None:
    distr = distr_class(**params)
    distr = serialize_fn(distr)
    means = distr.mean
    distr_name = distr.__class__.__name__
    assert means.shape == test_output[distr_name]["mean"].shape
    # asnumpy()  needed to b/c means is all pointers to values
    assert np.allclose(
        means.asnumpy(), test_output[distr_name]["mean"].asnumpy(), atol=1e-11
    )


@pytest.mark.parametrize("distr_class, params", test_cases)
@pytest.mark.parametrize("serialize_fn", serialize_fn_list)
def test_stdevs(distr_class, params, serialize_fn) -> None:
    distr = distr_class(**params)
    distr = serialize_fn(distr)
    stddevs = distr.stddev
    distr_name = distr.__class__.__name__
    assert stddevs.shape == test_output[distr_name]["stddev"].shape
    assert np.allclose(
        stddevs.asnumpy(),
        test_output[distr_name]["stddev"].asnumpy(),
        atol=1e-11,
    )


@pytest.mark.parametrize("distr_class, params", test_cases)
@pytest.mark.parametrize("serialize_fn", serialize_fn_list)
def test_variances(distr_class, params, serialize_fn) -> None:
    distr = distr_class(**params)
    distr = serialize_fn(distr)
    variances = distr.variance
    distr_name = distr.__class__.__name__
    assert variances.shape == test_output[distr_name]["variance"].shape
    assert np.allclose(
        variances.asnumpy(),
        test_output[distr_name]["variance"].asnumpy(),
        atol=1e-11,
    )
