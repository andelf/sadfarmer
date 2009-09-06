#!/usr/bin/env python
# -*- coding:gb18030 -*-

from distutils.core import setup
import py2exe

from SadFarmer import __VERSION__, __DEV_STATUS__

setup(
    version = __VERSION__,
    description = u"伤心农民 %s(%s). By WangMaoMao" % (__VERSION__, __DEV_STATUS__),
    name = r"SadFarmer",
    options = {"py2exe": {"compressed": 1,
                          "optimize": 2,
                          "ascii": 0,
                          "bundle_files": 1}},
    zipfile = None,
    # targets to build
    console = [{"script": r"SadFarmer.py", "icon_resources": [(1, r"icon.ico")]} ],
    )
