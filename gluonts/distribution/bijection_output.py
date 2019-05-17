# Standard library imports
from typing import Tuple

# First-party imports
from gluonts.core.component import validated
from gluonts.distribution.bijection import Bijection
from gluonts.distribution.distribution_output import Output
from gluonts.model.common import Tensor


class BijectionOutput(Output):
    """
    Class to connect a network to a bijection
    """

    bij_cls: type

    @validated()
    def __init__(self) -> None:
        pass

    def domain_map(self, F, *args: Tensor):
        raise NotImplementedError()

    def bijection(self, bij_args: Tensor) -> Bijection:
        return self.bij_cls(*bij_args)

    @property
    def event_shape(self) -> Tuple:
        raise NotImplementedError()
