"""This package provides the configuration classes used by the Sun lab maintained version of the suite2p library
(sl-suite2p package, https://github.com/Sun-Lab-NBB/suite2p) to process brain activity data within and across sessions
(days)."""

from .multi_day import MultiDayS2PConfiguration
from .single_day import SingleDayS2PConfiguration

__all__ = ["MultiDayS2PConfiguration", "SingleDayS2PConfiguration"]
