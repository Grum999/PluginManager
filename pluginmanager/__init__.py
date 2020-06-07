from .pluginmanager import PluginManager

# And add the extension to Krita's list of extensions:
app = Krita.instance()
extension = PluginManager(parent=app)
app.addExtension(extension)
