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

import PyQt5.uic

from krita import Window

from PyQt5.Qt import *
from PyQt5.QtCore import (
        pyqtSignal,
        QResource
    )
from PyQt5.QtWidgets import (
        QDialog,
        QFileDialog,
        QMessageBox,
        QTreeView
    )

from PyQt5.QtGui import (
        QStandardItemModel
    )

from .pmplugin import (
        Plugin,
        Plugins
    )

from .pmexceptions import (
        EInvalidType,
        EInvalidValue
    )


class PMPluginList(QTreeView):
    """Plugin list"""

    COLNUM_NAME = 0
    COLNUM_DESC = 1
    COLNUM_LAST = 1

    USERROLE_PLUGIN = Qt.UserRole + 1


    def __init__(self, parent=None):
        super(PMPluginList, self).__init__(parent)
        self.__model = None
        self.__initHeaders()

    def __initHeaders(self):
        """Initialise treeview header & model"""
        self.__model = QStandardItemModel(0, PMPluginList.COLNUM_LAST + 1, self)
        self.__model.setHeaderData(self.COLNUM_NAME, Qt.Horizontal, i18n("Plugin name"))
        self.__model.setHeaderData(self.COLNUM_DESC, Qt.Horizontal, i18n("Description name"))

        self.setModel(self.__model)

        # set colums size rules
        header = self.header()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(self.COLNUM_NAME, QHeaderView.Fixed)
        header.setSectionResizeMode(self.COLNUM_DESC, QHeaderView.Fixed)

        header.setSortIndicatorShown(True)
        header.setSectionsClickable(True)

    def addPlugin(self, plugin):
        """Add a plugin to list"""
        #if not isinstance(plugin, Plugin):
        #    raise EInvalidType('Given `plugin` must be a <Plugin>')

        newRow = [
                QStandardItem(''),
                QStandardItem('')
            ]

        newRow[self.COLNUM_NAME].setFlags(newRow[self.COLNUM_NAME].flags() | Qt.ItemIsUserCheckable)
        if plugin.isActive():
            newRow[self.COLNUM_NAME].setCheckState(Qt.Checked)
        else:
            newRow[self.COLNUM_NAME].setCheckState(Qt.Unchecked)
        newRow[self.COLNUM_NAME].setText(plugin.name())
        newRow[self.COLNUM_NAME].setData(plugin, PMPluginList.USERROLE_PLUGIN)
        newRow[self.COLNUM_NAME].setEnabled(plugin.isValid())
        newRow[self.COLNUM_DESC].setText(plugin.description())
        newRow[self.COLNUM_DESC].setEnabled(plugin.isValid())

        self.__model.appendRow(newRow)

    def resizeColumns(self):
        """Resize columns to content"""
        self.resizeColumnToContents(self.COLNUM_NAME)
        self.resizeColumnToContents(self.COLNUM_DESC)

    def clear(self):
        """Clear content"""
        self.__model.removeRows(0, self.__model.rowCount())

    def selectedPlugin(self):
        """Return selected plugin

        return None if no plugin is selected
        """
        smodel=self.selectionModel().selectedRows(PMPluginList.COLNUM_NAME)

        if len(smodel) == 1:
            return smodel[0].data(PMPluginList.USERROLE_PLUGIN)

        return None

    def selectedItem(self):
        """Return selected item (column 'NAME')

        return None if no plugin is selected
        """
        smodel=self.selectionModel().selectedRows(PMPluginList.COLNUM_NAME)

        if len(smodel) == 1:
            return self.model().itemFromIndex(smodel[0])

        return None

    def selectPlugin(self, plugin=None):
        """Select plugin in list

        If no plugin is provided, select first item
        """
        if isinstance(plugin, Plugin):
            id = plugin.id()
        elif isinstance(plugin, str):
            id = plugin
        else:
            id = None

        root = self.model().invisibleRootItem()

        for rowIndex in range(root.rowCount()):
            if root.child(rowIndex, 0).data(PMPluginList.USERROLE_PLUGIN).id() == id or id is None:
                first = root.child(rowIndex, 0).index()
                last = root.child(rowIndex, PMPluginList.COLNUM_LAST).index()
                self.selectionModel().select(QItemSelection(first, last), QItemSelectionModel.ClearAndSelect)
                break


class PMWindow(QDialog):
    """Buli Commander main window"""

    dialogShown = pyqtSignal()

    # region: initialisation methods -------------------------------------------

    def __init__(self, name, version, parent=None):
        super(PMWindow, self).__init__(parent)
        if not isinstance(name, str):
            raise EInvalidType('Given `name` must be a <str>')
        if not isinstance(version, str):
            raise EInvalidType('Given `version` must be a <str>')

        self.__eventCallBack = {}

        uiFileName = os.path.join(os.path.dirname(__file__), 'resources', 'pmwindow.ui')
        PyQt5.uic.loadUi(uiFileName, self)

        self.setWindowTitle(f'{name} v{version}')

        self.buttonBox.accepted.connect(self.accept)
        self.tvPluginList.selectionModel().selectionChanged.connect(self.__selectionChanged)
        self.tvPluginList.model().itemChanged.connect(self.__itemChanged)

        self.tbInstall.clicked.connect(self.__installPlugin)
        self.tbUninstall.clicked.connect(self.__uninstallPlugin)
        self.tbActivate.clicked.connect(self.__activatePlugin)

        self.__plugins = Plugins()

        self.__updateButtons()
        self.__buildList()
        self.tvPluginList.selectPlugin()

    # endregion: initialisation methods ----------------------------------------

    # region: events- ----------------------------------------------------------

    def showEvent(self, event):
        """Event trigerred when dialog is shown

           At this time, all widgets are initialised and size/visiblity is known


           Example
           =======
                # define callback function
                def my_callback_function():
                    print("BCMainWindow shown!")

                # initialise a dialog from an xml .ui file
                dlgMain = BCMainWindow.loadUi(uiFileName)

                # execute my_callback_function() when dialog became visible
                dlgMain.dialogShown.connect(my_callback_function)
        """
        self.splitterManual.setSizes([1000, 1000])

        super(PMWindow, self).showEvent(event)
        self.dialogShown.emit()

    def closeEvent(self, event):
        """Event executed when window is about to be closed"""
        #event.ignore()
        event.accept()

    def eventFilter(self, object, event):
        """Manage event filters for window"""
        if object in self.__eventCallBack.keys():
            return self.__eventCallBack[object](event)

        return super(PMWindow, self).eventFilter(object, event)

    def setEventCallback(self, object, method):
        """Add an event callback method for given object

           Example
           =======
                # define callback function
                def my_callback_function(event):
                    if event.type() == QEvent.xxxx:
                        print("Event!")
                        return True
                    return False


                # initialise a dialog from an xml .ui file
                dlgMain = BCMainWindow.loadUi(uiFileName)

                # define callback for widget from ui
                dlgMain.setEventCallback(dlgMain.my_widget, my_callback_function)
        """
        if object is None:
            return False

        self.__eventCallBack[object] = method
        object.installEventFilter(self)

    def __selectionChanged(self, selection):
        plugin=self.tvPluginList.selectedPlugin()

        if not plugin is None:
            if plugin.manualFile() != '':
                try:
                    with open(plugin.manualFile(), "r") as file:
                        data=file.readlines()
                        self.lblManual.setText(''.join(data))
                except:
                    self.lblManual.setText("Sorry, I'm unable to read the manual...")
            else:
                self.lblManual.setText("Sorry, no manual was provided for this plugin...")
        else:
            self.lblManual.setText("")

        self.__updateButtons()

    def __installPlugin(self, action):
        """Install a plugin"""
        fileName = QFileDialog.getOpenFileName(self,
                                               i18n("Import Krita Plugin"),
                                               "",
                                               "Zip archives (*.zip)")
        if fileName[0] != '':
            self.installPlugin(fileName[0])

    def __uninstallPlugin(self, action):
        """uninstall a plugin"""
        self.uninstallPlugin(self.tvPluginList.selectedPlugin())

    def __activatePlugin(self, action):
        """Activate/deactivate a plugin"""
        if action:
            self.activatePlugin()
        else:
            self.deactivatePlugin()

    def __itemChanged(self, value):
        """A plugin has been checked/unchecked"""
        if value.checkState() == Qt.Checked:
            self.activatePlugin()
        else:
            self.deactivatePlugin()

    # endregion: events --------------------------------------------------------

    # region: methods ----------------------------------------------------------

    def __updateButtons(self):
        """Update buttons according to selection"""
        plugin=self.tvPluginList.selectedPlugin()

        if plugin is None:
            self.tbUninstall.setEnabled(False)
            self.tbActivate.setEnabled(False)
            self.tbActivate.setChecked(False)
        else:
            self.tbUninstall.setEnabled(True)
            self.tbActivate.setEnabled(plugin.isValid())
            self.tbActivate.setChecked(plugin.isActive())

    def __buildList(self):
        """Build plugin list"""
        self.__plugins.refresh()
        self.tvPluginList.clear()

        for plugin in self.__plugins.plugins():
            self.tvPluginList.addPlugin(plugin)

        self.tvPluginList.resizeColumns()

    def activatePlugin(self):
        """Activate the current selected plugin"""
        plugin=self.tvPluginList.selectedPlugin()
        if plugin is None:
            return

        plugin.activate()

        item=self.tvPluginList.selectedItem()
        item.setCheckState(Qt.Checked)
        self.__updateButtons()


    def deactivatePlugin(self):
        """Deactivate the current selected plugin"""
        plugin=self.tvPluginList.selectedPlugin()
        if plugin is None:
            return
        plugin.deactivate()

        item=self.tvPluginList.selectedItem()
        item.setCheckState(Qt.Unchecked)
        self.__updateButtons()

    def installPlugin(self, fileName):
        """Install given plugin"""
        plugin = Plugin.install(fileName)
        if plugin is None:
            return
        self.refreshList()
        self.tvPluginList.selectPlugin(plugin)

        QMessageBox.information(
                QWidget(),
                i18n('Install Plugin'),
                i18n(f'The plugin "{plugin.name()}" has been installed!')
            )


    def uninstallPlugin(self, plugin):
        """Install given plugin"""
        if plugin is None:
            plugin = self.tvPluginList.selectedPlugin()

        if plugin is None:
            return

        name = plugin.name()

        if plugin.uninstall():
            self.refreshList()
            self.tvPluginList.selectPlugin(plugin)

            QMessageBox.information(
                    QWidget(),
                    i18n('Uninstall Plugin'),
                    i18n(f'The plugin "{name}" has been uninstalled!')
                )
                

    def refreshList(self):
        """Refresh current plugin list"""
        self.__buildList()

    # endregion: methods -------------------------------------------------------



