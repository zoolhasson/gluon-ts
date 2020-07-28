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

# Standard library imports

from typing import Iterator, List, Optional, Tuple, Union, Dict

# Third-party imports
import numpy as np

# First-party imports
from gluonts.core.component import validated
from gluonts.dataset.common import Dataset
from gluonts.dataset.field_names import FieldName
from gluonts.time_feature import (
    TimeFeature,
    time_features_from_frequency_str,
    get_lags_for_frequency,
)
from gluonts.trainer import Trainer
from gluonts.transform import (
    AddAgeFeature,
    AddObservedValuesIndicator,
    AddTimeFeatures,
    AsNumpyArray,
    Chain,
    ExpectedNumInstanceSampler,
    InstanceSplitter,
    RemoveFields,
    SetField,
    Transformation,
    VstackFeatures,
)
from gluonts.support.pandas import frequency_add


class PreprocessGeneric:
    """
    Class for the purpose of preprocessing time series. The method
    make_features needs to be custom-made by inherited classes.
    """

    def __init__(
        self,
        context_window_size: int,
        forecast_horizon: int = 1,
        stratify_targets: bool = False,
        n_ignore_last: int = 0,
        **kwargs
    ):
        """
        Parameters
        ----------
        context_window_size: int
        forecast_horizon: int
        stratify_targets: bool
            If False, each context window translates to one data point in
            feature_data of length the number of features, and one
            datapoint in target_data of length the forecast horizon.
            horizon.
            If True, each context window translates to forecast_horizon
            many datapoints. The resulting datapoints in feature_data are
            of length the number of features plus one, where the last
            coordinate varies between 0 and forecast_horizon - 1, and the
            other coordinates fixed. The respective datapoints in
            target_data are all of length 1 and vary between the first to
            the last targets in the forecast horizon. (Hence the name,
            this stratifies the targets.)
        n_ignore_last: int
            Cut the last n_ignore_last steps of the time series.
        """
        assert not (stratify_targets and (forecast_horizon == 1))
        self.context_window_size = context_window_size
        self.forecast_horizon = forecast_horizon
        self.stratify_targets = stratify_targets
        self.n_ignore_last = n_ignore_last
        self.kwargs = kwargs
        self.num_samples = None
        self.feature_data = None
        self.target_data = None

    def make_features(self, time_series, starting_index):
        """
        Makes features for the context window starting at starting_index.

        Parameters
        ----------
        time_series: list
        starting_index: int
            The index where the context window begins

        Returns
        -------
        list
        """
        raise NotImplementedError()

    @validated()
    def preprocess_from_single_ts(self, time_series: Dict) -> Tuple:
        """
        Takes a single time series, ts_list, and returns preprocessed data.

        Note that the number of features is determined by the implementation
        of make_features. The number of context windows is determined by
        num_samples, see documentation under Parameters.

        If stratify_targets is False, then the length of feature_data is:
        (number of context windows) x (number of features)
        And the length of target_data is:
        (number of context windows) x (forecast_horizon)

        If stratify_targets is False, then the length of feature_data is:
        (number of context windows) * forecast_horizon x (number of features+1)
        And the length of target_data is:
        (number of context windows) * forecast_horizon x 1

        Parameters
        ----------
        time_series: dict
            has 'target' and 'start' keys

        Returns
        -------
        tuple
            list of feature datapoints, list of target datapoints
        """
        if self.n_ignore_last > 0:
            altered_time_series = {
                "target": time_series["target"][: -self.n_ignore_last],
                "start": time_series["start"],
            }
        else:
            altered_time_series = time_series
        feature_data = []
        target_data = []
        max_num_context_windows = (
            len(altered_time_series["target"])
            - self.context_window_size
            - self.forecast_horizon
            + 1
        )
        if max_num_context_windows < 1:
            return [], []
        if self.num_samples > 0:
            locations = [
                np.random.randint(max_num_context_windows)
                for _ in range(self.num_samples)
            ]
        else:
            locations = range(max_num_context_windows)
        for starting_index in locations:
            if self.stratify_targets:
                featurized_data = self.make_features(
                    altered_time_series, starting_index
                )
                for forecast_horizon_index in range(self.forecast_horizon):
                    feature_data.append(
                        list(featurized_data) + [forecast_horizon_index]
                    )
                    target_data.append(
                        [
                            time_series["target"][
                                starting_index
                                + self.context_window_size
                                + forecast_horizon_index
                            ]
                        ]
                    )
            else:
                featurized_data = self.make_features(
                    altered_time_series, starting_index
                )
                feature_data.append(featurized_data)
                target_data.append(
                    time_series["target"][
                        starting_index
                        + self.context_window_size : starting_index
                        + self.context_window_size
                        + self.forecast_horizon
                    ]
                )
        return feature_data, target_data

    @validated()
    def preprocess_from_list(
        self, ts_list, change_internal_variables: bool = True
    ) -> Tuple:
        """
        Applies self.preprocess_from_single_ts for each time series in ts_list,
        and collates the results into self.feature_data and self.target_data

        Parameters
        ----------
        ts_list: list
            List of time series, each a dict with 'target' and 'start' keys.
        change_internal_variables: bool
            If True, keep results in self.feature_data, self.target_data and
            return None.

        Returns
        -------
        tuple
            If change_internal_variables is False, then returns:
            list of feature datapoints, list of target datapoints
        """
        feature_data, target_data = [], []
        self.num_samples = self.get_num_samples(ts_list)
        for time_series in ts_list:
            ts_feature_data, ts_target_data = self.preprocess_from_single_ts(
                time_series=time_series
            )
            feature_data += list(ts_feature_data)
            target_data += list(ts_target_data)
        print(
            "Done preprocessing. Resulting number of datapoints is: {}".format(
                len(feature_data)
            )
        )
        if change_internal_variables:
            self.feature_data, self.target_data = feature_data, target_data
        else:
            return feature_data, target_data

    @validated()
    def get_num_samples(self, ts_list) -> int:
        """
        Outputs a reasonable choice for number of windows to sample from
        each time series at training time.
        """
        n_time_series = sum(
            [
                len(time_series["target"])
                - self.context_window_size
                - self.forecast_horizon
                >= 0
                for time_series in ts_list
            ]
        )
        max_size_ts = max(
            [len(time_series["target"]) for time_series in ts_list]
        )
        n_windows_per_time_series = 400000 // n_time_series
        if n_time_series * 1000 < n_windows_per_time_series:
            n_windows_per_time_series = n_time_series * 1000
        elif n_windows_per_time_series == 0:
            n_windows_per_time_series = 1
        elif n_windows_per_time_series > max_size_ts:
            n_windows_per_time_series = -1
        return n_windows_per_time_series


class PreprocessOnlyLagFeatures(PreprocessGeneric):
    def __init__(
        self,
        context_window_size,
        forecast_horizon=1,
        stratify_targets=False,
        n_ignore_last=0,
        num_samples=-1,
        **kwargs
    ):
        super().__init__(
            context_window_size=context_window_size,
            forecast_horizon=forecast_horizon,
            stratify_targets=stratify_targets,
            n_ignore_last=n_ignore_last,
            num_samples=num_samples,
            **kwargs
        )

    @classmethod
    def _pre_transform(cls, time_series_window) -> Tuple:
        """
        Makes features given time series window. Returns list of features,
        one for every step of the lag (equaling mean-adjusted lag features);
        and a dictionary of statistics features (one for mean and one for
        standard deviation).

        Parameters
        ----------
        time_series_window: list

        Returns
        -------------
        tuple
            trasnformed time series, dictionary with transformation data
        return (time_series_window - np.mean(time_series_window)), {
            'mean': np.mean(time_series_window),
            'std': np.std(time_series_window)
        }
        """
        mean_value = np.mean(time_series_window)
        return (
            (time_series_window - mean_value),
            {
                "mean": mean_value,
                "std": np.std(time_series_window),
                "n_lag_features": len(time_series_window),
            },
        )

    @validated()
    def make_features(self, time_series: Dict, starting_index: int) -> List:
        """
        Makes features for the context window starting at starting_index.

        Parameters
        ----------
        time_series: dict
            has 'target' and 'start' keys
        starting_index: int
            The index where the context window begins

        Returns
        -------
        list
        """
        end_index = starting_index + self.context_window_size
        if starting_index < 0:
            prefix = [None] * (-starting_index)
        else:
            prefix = []
        time_series_window = time_series["target"][starting_index:end_index]
        only_lag_features, transform_dict = self._pre_transform(
            time_series_window
        )
        only_lag_features = list(only_lag_features)
        return prefix + only_lag_features + list(transform_dict.values())
