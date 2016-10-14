#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
guidebook.py
~~~~~~~~~~~~

PURPOSE
This module is the "scientific expert knowledge" that is consulted.



:author: R.K.Garcia <rayg@ssec.wisc.edu>
:copyright: 2014 by University of Wisconsin Regents, see AUTHORS for more details
:license: GPLv3, see LICENSE for more details
"""
__author__ = 'rayg'
__docformat__ = 'reStructuredText'

import logging
import numpy as np

from sift.common import INFO, KIND, INSTRUMENT, PLATFORM
from sift.view.Colormap import DEFAULT_IR, DEFAULT_VIS, DEFAULT_UNKNOWN

LOG = logging.getLogger(__name__)

GUIDEBOOKS = {}


class Guidebook(object):
    """
    guidebook which knows about AHI, ABI, AMI bands, timing, file naming conventions
    """
    @staticmethod
    def is_relevant(pathname):
        return False

    @staticmethod
    def for_info(info=None, path=None):
        """
        given an info dictionary, figure out which
        :param info:
        :return:
        """
        if info and not path:
            path = info.get(INFO.PATHNAME, None)

    def channel_siblings(self, uuid, infos):
        """
        determine the channel siblings of a given dataset
        :param uuid: uuid of the dataset we're interested in
        :param infos: datasetinfo_dict sequence, available datasets
        :return: (list,offset:int): list of [uuid,uuid,uuid] for siblings in order; offset of where the input is found in list
        """
        return None, None

    def time_siblings(self, uuid, infos):
        """
        determine the time siblings of a given dataset
        :param uuid: uuid of the dataset we're interested in
        :param infos: datasetinfo_dict sequence, available datasets
        :return: (list,offset:int): list of [uuid,uuid,uuid] for siblings in order; offset of where the input is found in list
        """
        return None, None


DEFAULT_COLORMAPS = {
    'toa_bidirectional_reflectance': DEFAULT_VIS,
    'toa_brightness_temperature': DEFAULT_IR,
    'height_at_cloud_top': 'Cloud Top Height',
    # 'thermodynamic_phase_of_cloud_water_particles_at_cloud_top': 'Cloud Phase',
}


# Instrument -> Band Number -> Nominal Wavelength
NOMINAL_WAVELENGTHS = {
    PLATFORM.HIMAWARI_8: {
        INSTRUMENT.AHI: {
            1: 0.47,
            2: 0.51,
            3: 0.64,
            4: 0.86,
            5: 1.6,
            6: 2.3,
            7: 3.9,
            8: 6.2,
            9: 6.9,
            10: 7.3,
            11: 8.6,
            12: 9.6,
            13: 10.4,
            14: 11.2,
            15: 12.4,
            16: 13.3,
        },
    },
    # PLATFORM.HIMAWARI_9: {
    #     INSTRUMENT.AHI: {
    #     },
    # },
    # PLATFORM.GOES_16: {
    #     INSTRUMENT.ABI: {
    #     },
    # },
}

# CF compliant Standard Names (should be provided by input files or the workspace)
# Instrument -> Band Number -> Standard Name
STANDARD_NAMES = {
    PLATFORM.HIMAWARI_8: {
        INSTRUMENT.AHI: {
            1: "toa_bidirectional_reflectance",
            2: "toa_bidirectional_reflectance",
            3: "toa_bidirectional_reflectance",
            4: "toa_bidirectional_reflectance",
            5: "toa_bidirectional_reflectance",
            6: "toa_bidirectional_reflectance",
            7: "toa_brightness_temperature",
            8: "toa_brightness_temperature",
            9: "toa_brightness_temperature",
            10: "toa_brightness_temperature",
            11: "toa_brightness_temperature",
            12: "toa_brightness_temperature",
            13: "toa_brightness_temperature",
            14: "toa_brightness_temperature",
            15: "toa_brightness_temperature",
            16: "toa_brightness_temperature",
        }
    }
}



class AHI_HSF_Guidebook(Guidebook):
    "e.g. HS_H08_20150714_0030_B10_FLDK_R20.merc.tif"
    REFL_BANDS = [1, 2, 3, 4, 5, 6]
    BT_BANDS = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

    def collect_info(self, info):
        """Collect information that may not come from the dataset.

        This method should only be called once to "fill in" metadata
        that isn't originally known about an opened file.
        """
        z = {}

        if info[INFO.KIND] in (KIND.IMAGE, KIND.COMPOSITE):
            if z.get(INFO.CENTRAL_WAVELENGTH) is None:
                try:
                    wl = NOMINAL_WAVELENGTHS[info[INFO.PLATFORM]][info[INFO.INSTRUMENT]][info[INFO.BAND]]
                except KeyError:
                    wl = None
                z[INFO.CENTRAL_WAVELENGTH] = wl

        if INFO.BAND in info:
            band_short_name = "B{:02d}".format(info[INFO.BAND])
        else:
            band_short_name = info.get(INFO.DATASET_NAME, '???')
        if INFO.SHORT_NAME not in info:
            z[INFO.SHORT_NAME] = band_short_name
        if INFO.LONG_NAME not in info:
            z[INFO.LONG_NAME] = info.get(INFO.SHORT_NAME, z[INFO.SHORT_NAME])

        if INFO.STANDARD_NAME not in info:
            try:
                z[INFO.STANDARD_NAME] = STANDARD_NAMES[info[INFO.PLATFORM]][info[INFO.INSTRUMENT]][info[INFO.BAND]]
            except KeyError:
                z[INFO.STANDARD_NAME] = z.get(INFO.SHORT_NAME)

        return z

    def _is_refl(self, dsi):
        # work around for old `if band in BAND_TYPE`
        return dsi.get(INFO.BAND) in self.REFL_BANDS or \
               dsi.get(INFO.STANDARD_NAME) == "toa_bidirectional_reflectance"

    def _is_bt(self, dsi):
        return dsi.get(INFO.BAND) in self.BT_BANDS or \
               dsi.get(INFO.STANDARD_NAME) == "toa_brightness_temperature"

    def climits(self, dsi):
        # Valid min and max for colormap use for data values in file (unconverted)
        if self._is_refl(dsi):
            # Reflectance/visible data limits
            return -0.012, 1.192
        elif self._is_bt(dsi):
            # BT data limits
            return -109.0 + 273.15, 55 + 273.15
        elif "valid_min" in dsi and "valid_max" in dsi:
            return dsi["valid_min"], dsi["valid_max"]
        elif "flag_values" in dsi:
            return min(dsi["flag_values"]), max(dsi["flag_values"])
        else:
            # some kind of default
            return 0., 255.

    def units_conversion(self, dsi):
        "return UTF8 unit string, lambda v,inverse=False: convert-raw-data-to-unis"
        units = dsi.get("units", "")
        if units == "1":
            units = ""

        if self._is_refl(dsi):
            # Reflectance/visible data limits
            return ('{:.03f}', '', lambda x, inverse=False: x)
        elif self._is_bt(dsi):
            # BT data limits, Kelvin to degC
            return ("{:.02f}", "°C", lambda x, inverse=False: x - 273.15 if not inverse else x + 273.15)
        elif "flag_values" in dsi:
            # XXX: Better place to put all this logic?
            if "flag_meanings" in dsi:
                flag_masks = dsi["flag_masks"] if "flag_masks" in dsi else [-1] * len(dsi["flag_values"])
                def _flag_meaning(x, inverse=False):
                    single = False
                    if isinstance(x, np.ndarray):
                        if x.size == 2:
                            # assume color limits
                            return [str(val) for val in x]
                    else:
                        x = [x]
                        single = True

                    all_strings = []
                    for data_val in x:
                        meanings = []
                        data_val = int(data_val)
                        for fmean, fval, fmask in zip(dsi["flag_meanings"], dsi["flag_values"], flag_masks):
                            if (data_val & fmask) == fval:
                                meanings.append(fmean)
                        s = "{:d} ({:s})".format(data_val, ", ".join(meanings))
                        all_strings.append(s)
                    if single:
                        return all_strings[0]
                    return all_strings

                return ("{:s}", units, _flag_meaning)
            else:
                return ("{:0.0f}", units, lambda x, inverse=False: x)
        else:
            return ("{:.03f}", units, lambda x, inverse=False: x)

    def default_colormap(self, dsi):
        return DEFAULT_COLORMAPS.get(dsi.get(INFO.STANDARD_NAME), DEFAULT_UNKNOWN)

    # def display_time(self, dsi):
    #     return dsi.get(INFO.DISPLAY_TIME, '--:--')
    #
    # def display_name(self, dsi):
    #     return dsi.get(INFO.DISPLAY_NAME, '-unknown-')

    def _default_display_time_rgb(self, ds_info):
        dep_info = [ds_info.r, ds_info.g, ds_info.b]
        valid_times = [nfo.get(INFO.DISPLAY_TIME, '<unknown time>') for nfo in dep_info if nfo is not None]
        if len(valid_times) == 0:
            display_time = '<unknown time>'
        else:
            display_time = valid_times[0] if len(valid_times) and all(t == valid_times[0] for t in valid_times[1:]) else '<multiple times>'

        return display_time

    def _default_display_time(self, ds_info):
        if ds_info.kind == KIND.RGB:
            return self._default_display_time_rgb(ds_info)

        # FUTURE: This can be customized by the user
        when = ds_info.get(INFO.SCHED_TIME, ds_info.get(INFO.OBS_TIME))
        if when is None:
            dtime = '--:--'
        else:
            dtime = when.strftime('%Y-%m-%d %H:%M')
        return dtime

    def _default_display_name_rgb(self, ds_info, display_name=None):
        dep_info = [ds_info.r, ds_info.g, ds_info.b]
        if display_name is None:
            display_time = self._default_display_time(ds_info)

        try:
            names = []
            for color, dep_layer in zip("RGB", dep_info):
                if dep_layer is None:
                    name = u"{}:---".format(color)
                else:
                    name = u"{}:{}".format(color, dep_layer.dataset_name)
                names.append(name)
            name = u' '.join(names) + u' ' + display_time
        except KeyError:
            LOG.error('unable to create new name from {0!r:s}'.format(dep_info))
            name = "-RGB-"

        return name

    def _default_display_name(self, ds_info, display_time=None):
        if ds_info[INFO.KIND] == KIND.RGB:
            return self._default_display_name_rgb(ds_info)

        # FUTURE: This can be customized by the user
        sat = ds_info[INFO.PLATFORM]
        inst = ds_info[INFO.INSTRUMENT]
        name = ds_info.get(INFO.SHORT_NAME, '-unknown-')

        label = ds_info.get(INFO.STANDARD_NAME, '')
        if label == 'toa_bidirectional_reflectance':
            label = 'Refl'
        elif label == 'toa_brightness_temperature':
            label = 'BT'

        if display_time is None:
            display_time = ds_info.get(INFO.DISPLAY_TIME, self._default_display_time(ds_info))
        name = "{inst} {name} {standard_name} {dtime}".format(
            inst=inst.value, name=name, standard_name=label, dtime=display_time)
        return name



# if __name__ == '__main__':
#     sys.exit(main())
