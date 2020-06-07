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

from .pmexceptions import (
        EInvalidType,
        EInvalidValue
    )

import krita

import os
import re
import shutil
import sys
import zipfile
import configparser

import PyQt5.uic
from PyQt5.Qt import *
from PyQt5.QtCore import (
        QStandardPaths
    )
from PyQt5.QtWidgets import (
        QMessageBox
    )

class Plugin(object):
    """A plugin definition"""
    ACTION_VALIDATE_ASK = 0
    ACTION_VALIDATE_YES = 1
    ACTION_VALIDATE_NO = 2

    def __init__(self, desktopFileName=None):
        self.__id = ''
        self.__name = ''
        self.__description = ''
        self.__path = ''
        self.__manual = ''
        self.__desktopFile = ''
        self.__isActive = False
        self.__isValid = False

        self.loadFromDesktopFile(desktopFileName)

    def __repr__(self):
        """Return str value"""
        return f"<Plugin({self.__id}, {self.__name},  {self.__isValid}, {self.__isActive}, {self.__path})>"

    def __defaultValues(self):
        self.__id = ''
        self.__name = ''
        self.__description = ''
        self.__path = ''
        self.__manual = ''
        self.__desktopFile = ''
        self.__isActive = False
        self.__isValid = False

    def __loadFromcfgParser(self, cfgParser):
        """Load plugin from a configparser"""
        settings=cfgParser['Desktop Entry']

        self.__id = settings.get('X-KDE-Library', '')
        self.__name = settings.get('Name', '')
        self.__description = settings.get('Comment', '')
        self.__path = os.path.join(Plugins.path(), self.__id)
        self.__manual = settings.get('X-Krita-Manual', '')
        if self.__manual != '':
            self.__manual = os.path.join(self.__path, self.__manual)

        if isinstance(self.__name, list):
            self.__name = ' '.join(self.__name)
        if isinstance(self.__description, list):
            self.__description = '\n'.join(self.__description)

        self.__isValid = True

        if Krita.instance().readSetting('python', f'enable_{self.__id}', 'false') == 'true':
            self.__isActive = True
        else:
            self.__isActive = False

    def __getMenuLocation(self, location, fromWidget=None):
        """Return action for given menu location

        location is a string in form 'menu1/menu2/menuN'

        Return None if not found
        """
        idList = location.split('/')

        if fromWidget is None:
            if not Krita.instance().activeWindow() is None:
                fromWidget = Krita.instance().activeWindow().qwindow().menuWidget()

        if not fromWidget is None:
            for action in fromWidget.actions():
                if action.objectName() == idList[0]:
                    if len(idList) == 1:
                        # the last item, return the menu
                        return action.menu()
                    else:
                        return self.__getMenuLocation('/'.join(idList[1:]), action.menu() )

        return None

    def id(self):
        """Return plugin id"""
        return self.__id

    def name(self):
        """Return plugin name"""
        return self.__name

    def description(self):
        """Return plugin description"""
        return self.__description

    def path(self):
        """Return plugin path"""
        return self.__path

    def manualFile(self):
        """Return manual file name"""
        return self.__manual

    def desktopFile(self):
        """Return desktop file name"""
        return self.__desktopFile

    def isActive(self):
        """Return if plugin is active or not"""
        return self.__isActive

    def isValid(self):
        """Return if plugin is valid or not"""
        return self.__isValid

    def loadFromDesktopFile(self, desktopFileName=None):
        """Load plugin from given desktop file name"""

        self.__defaultValues()

        if desktopFileName is None:
            return

        if not isinstance(desktopFileName, str):
            raise EInvalidType("Given `desktopFileName` must be a <str>")

        if os.path.isfile(desktopFileName):
            if re.search(r'\.desktop$', desktopFileName):
                self.__desktopFile = desktopFileName

                configParser = configparser.ConfigParser()
                configParser.read(desktopFileName)
                self.__loadFromcfgParser(configParser)
            else:
                self.__isValid = False
                self.__isActive = False
                raise EInvalidValue('Given `desktopFileName` must have ".desktop" extension')
        else:
            self.__isValid = False
            self.__isActive = False
            raise EInvalidValue('Given `desktopFileName` file doesn''t exists')

    def loadFromDesktopContent(self, desktopContent=''):
        """Load plugin from desktop content definition"""

        self.__defaultValues()

        if desktopContent is None:
            return

        if not isinstance(desktopContent, str):
            raise EInvalidType("Given `desktopContent` must be a <str>")

        if desktopContent == '':
            return

        configParser = configparser.ConfigParser()
        configParser.read_string(desktopContent)
        self.__loadFromcfgParser(configParser)

        # theorical desktop file
        self.__desktopFile = os.path.join(Plugins.path(), f'{self.__id}.desktop')

    def deactivate(self):
        """Deactivate plugin

        The plugin is set as disabled in kritarc
        """
        if not self.__isActive:
            # already inactive, do nothing
            return

        self.__isActive = False
        Krita.instance().writeSetting('python', f'enable_{self.__id}', 'false')

        moduleNames = [name for name in sys.modules.keys()]
        for moduleName in moduleNames:
            module = sys.modules[moduleName]
            if '__file__' in module.__dict__ and isinstance(module.__file__, str) and os.path.dirname(module.__file__) == self.__path:
                sys.modules.pop(moduleName)
                # need to check how to do this, but need to remove module completely
                # del xxxxx


    def activate(self):
        """Activate plugin

        The plugin is set as enabled in kritarc
        """
        if self.__isActive:
            # already active, do nothing
            return

        # set plugin activated in Krita settings
        self.__isActive = True
        Krita.instance().writeSetting('python', f'enable_{self.__id}', 'true')

        import inspect
        import importlib
        from importlib.machinery import SourceFileLoader

        # plugin must be activated through __init__.py
        script = os.path.join(self.__path, '__init__.py')

        spec = importlib.util.spec_from_file_location(self.__id, script)
        loader = SourceFileLoader("__main__", script)
        users_module = loader.load_module()

        # make a list of current defined actions
        newActionsList = []
        actionsListId = []
        for action in Krita.instance().actions():
            actionsListId.append(action.objectName())

        # plugin is loaded
        # need to activate it
        # => setup
        # => actions

        # from here, we don't really know what the __init__.py have made
        # so lookup the extensions list to search the onbject that has been instancied
        # from the __init__.py plugin
        for extension in Krita.instance().extensions():
            path = os.path.dirname(inspect.getfile(extension.__class__))

            if path == self.__path:
                if not extension.setup is None and callable(extension.setup):
                    # setup is defined, execute it
                    extension.setup()

                if not extension.createActions is None and callable(extension.createActions):
                    # create actions is defined, execute it
                    extension.createActions(Krita.instance().activeWindow())

                    # compare the list of current defined actions with the previous one
                    # new actions has been added by plugin
                    for action in Krita.instance().actions():
                        if not action.objectName() in actionsListId:
                            newActionsList.append(action)

        # now, plugin is practically ready to be used in Krita
        # menu is unfornately not updated, even if action has been created
        # it seems that action is not a QAction created and inserted directly in
        # menu, but a KisAction created and managed through the actionManager

        # the tweak here is to append the created action directly to menu
        # it's not clean because there might be a reason why the actionManager
        # has been implemented, but it's currently the only way found to add
        # dynamically an action to menu
        for action in newActionsList:
            menuLocation = action.property('menulocation')
            if not menuLocation is None:
                menu = self.__getMenuLocation(action.property('menulocation'))
                if not menu is None:
                    menu.addAction(action)

    def uninstall(self, confirmUninstall=None):
        """Uninstall plugin

        1) deactivate plugin
        2) remove plugin entirely
        """
        if confirmUninstall is None:
            confirmUninstall = Plugin.ACTION_VALIDATE_ASK

        if confirmUninstall == Plugin.ACTION_VALIDATE_ASK:
            userChoice = QMessageBox.question(
                    QWidget(),
                    i18n('Uninstall Plugin'),
                    i18n(f'The plugin "{self.__name}" will be completely removed.\n\nConfirm uninstallation?'),
                    QMessageBox.Yes | QMessageBox.No
                )

            if userChoice == QMessageBox.Yes:
                confirmUninstall = Plugin.ACTION_VALIDATE_YES
            else:
                confirmUninstall = Plugin.ACTION_VALIDATE_NO

        if confirmUninstall == Plugin.ACTION_VALIDATE_NO:
            qDebug(f'user didn''t confirm uninstallation\nCancel uninstallation')
            return False

        # deactivate plugin if still active
        self.deactivate()
        Krita.instance().writeSetting('python', f'enable_{self.__id}', None)

        # remove files

        if os.path.exists(self.__desktopFile):
            os.remove(self.__desktopFile)

        actionFile = os.path.join(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation), 'actions', f'{self.__id}.action')
        if os.path.exists(actionFile):
            os.remove(actionFile)

        if os.path.exists(self.__path):
            shutil.rmtree(self.__path, ignore_errors=True)

        # curent plugin is not valid anymore...
        self.__defaultValues()

        return True

    @staticmethod
    def install(zipFileName, overwrite=None):
        """Install plugin from zip file

        Return a Plugin if Ok, otherwise None
        """
        if overwrite is None:
            overwrite = Plugin.ACTION_VALIDATE_ASK


        if not isinstance(zipFileName, str):
            raise EInvalidType("Given `zipFile` must be a <str>")

        if not os.path.isfile(zipFileName):
            # not a file=> exit
            qDebug(f"File name doesn't exist: {zipFileName}")
            return None

        try:
            with zipfile.ZipFile(zipFileName, 'r') as archive:
                # open zip file and search for desktop entry
                desktopFile = [fileName for fileName in archive.namelist() if re.search(r'\.desktop$', fileName)]

                if len(desktopFile) == 0:
                    qDebug(f"No desktop entry found in archive: {zipFileName}")
                    return None
                elif len(desktopFile) > 1:
                    qDebug(f"Too much desktop entry ({len(desktopFile)}) found in archive: {zipFileName}")
                    return None

                plugin = Plugin()

                # initialise plugin with information from desktop entry stored into zip file
                desktopFileName = desktopFile[0]
                desktopFile = archive.open(desktopFileName)
                plugin.loadFromDesktopContent(desktopFile.read().decode())

                if not plugin.isValid():
                    # plugin it not valid, stop
                    qDebug(f'Plugin from archive is not valid')
                    return None

                initFileName = os.path.join(plugin.id(), '__init__.py' )
                initFile = [fileName for fileName in archive.namelist() if re.search(re.escape(initFileName)+'$', fileName)]
                if len(initFile) == 0:
                    # no __init__ file, invalid plugin...
                    qDebug(f"File '{initFileName}' not found in archive: {zipFileName}")
                    return None
                else:
                    initFileName = initFile[0]

                # Archive seems to be valid
                if os.path.exists(plugin.path()):
                    if overwrite == Plugin.ACTION_VALIDATE_ASK:
                        userChoice = QMessageBox.question(
                                QWidget(),
                                i18n('Install Plugin'),
                                i18n(f'The plugin "{plugin.name()}" already exists.\n\nOverwrite it?'),
                                QMessageBox.Yes | QMessageBox.No
                            )

                        if userChoice == QMessageBox.Yes:
                            overwrite = Plugin.ACTION_VALIDATE_YES
                        else:
                            overwrite = Plugin.ACTION_VALIDATE_NO

                    if overwrite == Plugin.ACTION_VALIDATE_NO:
                        qDebug(f'Plugin already exist in destination: {plugin.path()}\nCancel installation')
                        return None
                else:
                    os.mkdir(plugin.path())


                # extract files
                rootPathLength = len(os.path.dirname(desktopFileName))
                if rootPathLength > 0:
                    rootPathLength+=1

                initPathLength = len(os.path.dirname(initFileName))
                if initPathLength > 0:
                    initPathLength+=1

                for fileSrc in archive.infolist():
                    if os.path.basename(fileSrc.filename) == f'{plugin.id()}.desktop':
                        fileSrc.filename = fileSrc.filename[rootPathLength:]

                        archive.extract(fileSrc, Plugins.path())
                    elif os.path.basename(fileSrc.filename) == f'{plugin.id()}.action':
                        fileSrc.filename = fileSrc.filename[rootPathLength:]

                        archive.extract(fileSrc, os.path.join(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation), 'actions') )
                    elif len(fileSrc.filename) > initPathLength:
                        fileSrc.filename = fileSrc.filename[initPathLength:]
                        archive.extract(fileSrc, plugin.path())


                # here, everything is OK: activate plugin
                plugin.activate()

                return plugin

        except Exception as e:
            qDebug(f"Unable to read archive archive: {zipFileName}")
            qDebug(str(e))
            return None

        return None



class Plugins(object):
    """Manage plugin list"""

    def __init__(self):
        self.__plugins = {}
        self.__buildList()

    def __buildList(self):
        """Build plugin list"""
        self.__plugins = {}

        with os.scandir(Plugins.path()) as files:
            for file in files:
                fullPathName = os.path.join(Plugins.path(), file.name)
                if re.search(r'\.desktop$', file.name):
                    self.append(fullPathName)

    @staticmethod
    def path():
        """Return plugin installation path"""
        returned = os.path.join(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation), 'pykrita')
        if not os.path.exists(returned):
            os.mkdir(dest)

        return returned

    def length(self):
        """Return number of plugins"""
        return len(self.__plugins)

    def append(self, plugin):
        """Append a plugin to list

        Return True if added, otherwise False"
        """

        if isinstance(plugin, str):
            try:
                plugin = Plugin(plugin)
            except:
                return False
        elif not isinstance(plugin, Plugin):
            return False

        if plugin.id() != '':
            self.__plugins[plugin.id()] = plugin
            return True

        return False

    def remove(self, id):
        """Remove a plugin from list"""
        if not isinstance(id, str):
            raise EInvalidType('Given `id` must be a <str>')

        if id in self.__plugins:
            self.__plugins.pop(id)

    def plugin(self, id):
        """Return plugin from given id

        If no plugin exists, return None
        """
        if not isinstance(id, str):
            raise EInvalidType('Given `id` must be a <str>')

        if id in self.__plugins:
            return self.__plugins[id]

        return None

    def plugins(self):
        """Return a list of plugins"""
        returned = []
        for pluginId in self.__plugins:
            returned.append(self.__plugins[pluginId])

        return returned

    def refresh(self):
        """Refresh plugin list"""
        self.__buildList()





