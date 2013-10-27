Summary
=======

This plugin will cause "gedit" to immediately and automatically stash all 
unsaved documents. 


Details
=======

Once this plugin is installed and enabled (within the plugin listing, in 
"gedit"), all unsaved documents will begin to be watched. When an unsaved
document is saved by the user, its file in temporary storage will be deleted.
If all unsaved documents are saved by the user and all temporary files are
removed, the storage directory will be removed. All old temporary files will 
be periodically cleaned-up (currently, every four weeks).

Your unsaved documents will be stored under a directory named after the 
date/time that your "gedit" session was started. For example:

    ~/.gedit-unsaved/20131027-052807/Untitled Document 1


Lastly, this plugin will observe your "autosave" setting. If "autosave" is 
disabled, this plugin will not do anything. Otherwise, your unsaved documents 
will be stored at the same frequency. In other words, if your "autosave" is 
configured for two-minutes, this is the frequency at which your unsaved 
documents will be stored.


Dependencies
============

invoke (Python package)


Getting Started
===============

1) Run "invoke install" as the current user.
2) Open "gedit", and enable the "Safety Save" plugin.
3) Make sure your "autosave" setting is turned-on and configured for an 
   appropriate frequency.

