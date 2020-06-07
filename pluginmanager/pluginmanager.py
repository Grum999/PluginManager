#-----------------------------------------------------------------------------
# Plugin Manager
# Copyright (C) 2020 - Grum999
# -----------------------------------------------------------------------------
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.
# If not, see https://www.gnu.org/licenses/
# -----------------------------------------------------------------------------
# A Krita plugin designed to manage plugins
# -----------------------------------------------------------------------------

import os
import re
import sys
import time

import PyQt5.uic

from krita import (
        Extension
    )

from PyQt5.Qt import *
from PyQt5 import QtCore
from PyQt5.QtCore import (
        QStandardPaths,
        QObject
    )
from PyQt5.QtWidgets import (
        QApplication,
        QCheckBox,
        QColorDialog,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QProgressBar,
        QProgressDialog,
        QVBoxLayout,
        QWidget
    )

if __name__ != '__main__':
     # script is executed from Krita, loaded as a module
    __PLUGIN_EXEC_FROM__ = 'KRITA'

    from .pmwindow import PMWindow

else:
    # Execution from 'Scripter' plugin?
    __PLUGIN_EXEC_FROM__ = 'SCRIPTER_PLUGIN'

    from importlib import reload

    print("======================================")
    print(f'Execution from {__PLUGIN_EXEC_FROM__}')

    for module in list(sys.modules.keys()):
        if not re.search(r'^pluginmanager\.', module) is None:
            print('Reload module: ', module, sys.modules[module])
            reload(sys.modules[module])

    from pluginmanager.pmwindow import PMWindow

    print("======================================")


EXTENSION_ID = 'pykrita_plugincommander'
PLUGIN_VERSION = '0.1.0a'
PLUGIN_MENU_ENTRY = 'Plugin Manager'


class PluginManager(Extension):

    def __init__(self, parent):
        # Default options

        # Always initialise the superclass.
        # This is necessary to create the underlying C++ object
        super().__init__(parent)
        self.parent = parent

    def setup(self):
        """Is executed at Krita's startup"""
        pass

    def createActions(self, window):
        self.__window = window
        action = window.createAction(EXTENSION_ID, PLUGIN_MENU_ENTRY, "tools/scripts")
        action.triggered.connect(self.start)

    def start(self):
        """Execute Plugin Manager"""
        # ----------------------------------------------------------------------
        # Create dialog box
        uiWindow = PMWindow(PLUGIN_MENU_ENTRY, PLUGIN_VERSION)
        uiWindow.exec()


if __PLUGIN_EXEC_FROM__ == 'SCRIPTER_PLUGIN':
    PluginManager(Krita.instance()).start()

