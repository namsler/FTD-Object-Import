# FTD-Parse

 importObjects.py
 This script will import host, network, and service objects from an ASA script
 For consistent results, use config files that do not have names.
 NOTE: a module to remove objects has been included. Be very careful with this module.
 It will delete ALL objects under that heading, including objects that are already in use by firewalls.
 To launch the script, be sure the the firewall config and the script are in the same folder.
 In powershell run the command "python importObjects.py"
 The script will prompt for the config name, IP of the FMC and the username and password.
 The script will then parse the config file and then import the specified objects into the FMC.
 It is recommended to run the script on a test FMC prior to running on the operational firewall

There is a module to remove objects from the FMC. BE VERY CAREFUL WITH THIS! This was designed to remove all objects within a category. (ie, host, network, url). This includes any objects that are in use on other firewalls. 

It is recommended to run the script using a test FMC VM prior to running it on the production VM.
